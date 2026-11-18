import copy
import os
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple

import dotenv
from config_manager.yaml_parser import is_secret_masked, parse_yaml, to_plain_dict
from utils.logging import get_logger

CANONICAL_SECRET_PATHS: Dict[Tuple[str, ...], str] = {
    ("notifications", "telegram", "bot_token"): "TELEGRAM_BOT_TOKEN",
    ("notifications", "telegram", "chat_id"): "TELEGRAM_CHAT_ID",
    ("notifications", "email", "smtp_host"): "EMAIL_SMTP_HOST",
    ("notifications", "email", "smtp_port"): "EMAIL_SMTP_PORT",
    ("notifications", "email", "username"): "EMAIL_USERNAME",
    ("notifications", "email", "password"): "EMAIL_PASSWORD",
    ("notifications", "email", "from_address"): "EMAIL_FROM_ADDRESS",
}

ENV_VAR_REGEX = re.compile(r"^[A-Z0-9_]{3,64}$")
ENV_TEMPLATE_REGEX = re.compile(r"^\$\{([A-Za-z0-9_]+)(?::-(.*?))?\}$")


class EnvSecurityError(Exception):
    """Raised when environment variable name or secret value fails security validation."""
    pass


def is_env_template(val: Any) -> bool:
    """Return True if val matches ${VAR_NAME} or ${VAR_NAME:-default}."""
    if isinstance(val, str) and ENV_TEMPLATE_REGEX.match(val.strip()):
        return True
    return False


def get_env_template_var_name(val: Any) -> Optional[str]:
    """Extract VAR_NAME from ${VAR_NAME} or ${VAR_NAME:-default}."""
    if isinstance(val, str):
        m = ENV_TEMPLATE_REGEX.match(val.strip())
        if m:
            return m.group(1)
    return None


def get_val_at_path(data: Any, path: Tuple[str, ...]) -> Any:
    """Safely get value at nested path tuple from a dict."""
    curr = data
    for p in path:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return None
    return curr


def set_val_at_path(data: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    """Safely set value at nested path tuple in a dict, creating intermediate dicts if needed."""
    curr = data
    for i, p in enumerate(path[:-1]):
        if p not in curr or not isinstance(curr[p], dict):
            curr[p] = {}
        curr = curr[p]
    curr[path[-1]] = value


def validate_secret_security(var_name: str, secret_val: Any) -> None:
    """
    Validate that environment variable name conforms to whitelist
    and secret value contains no CRLF characters (injection prevention).
    """
    if not ENV_VAR_REGEX.match(var_name):
        raise EnvSecurityError(
            f"Security validation failed: Invalid environment variable name '{var_name}'. "
            "Must be uppercase alphanumeric with underscores, between 3 and 64 characters."
        )

    val_str = str(secret_val)
    if "\r" in val_str or "\n" in val_str:
        raise EnvSecurityError(
            f"Security validation failed: Secret value for '{var_name}' contains illegal newline characters "
            "(CRLF injection prevention)."
        )


class EnvSecretManager:
    """
    Manages automatic isolation and externalization of sensitive configuration secrets
    to the .env file, substituting references with ${VAR_NAME} in system.yaml.
    """

    def __init__(self, dotenv_path: Optional[str] = None, config_path: Optional[str] = None):
        if dotenv_path:
            self.dotenv_path = os.path.abspath(dotenv_path)
        elif config_path:
            # Typically config_path is <project_root>/config/system.yaml -> <project_root>/.env
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(config_path)))
            self.dotenv_path = os.path.join(base_dir, ".env")
        else:
            found = dotenv.find_dotenv()
            if found:
                self.dotenv_path = os.path.abspath(found)
            else:
                self.dotenv_path = os.path.abspath(".env")

        self.logger = get_logger("EnvSecretManager")
        if os.path.exists(self.dotenv_path):
            dotenv.load_dotenv(self.dotenv_path, override=True)

    def _discover_secret_targets(self, model: Dict[str, Any]) -> List[Tuple[Tuple[str, ...], str]]:
        """
        Discovers all paths in the model that are eligible for secret externalization.
        Returns a list of (path_tuple, default_var_name).
        """
        targets: List[Tuple[Tuple[str, ...], str]] = []

        # 1. Canonical paths
        for path_tuple, var_name in CANONICAL_SECRET_PATHS.items():
            targets.append((path_tuple, var_name))

        # 2. Node auth_key fields
        nodes = model.get("nodes")
        if isinstance(nodes, dict):
            for node_id in nodes.keys():
                clean_id = re.sub(r"[^A-Z0-9]", "_", str(node_id).upper())
                if not clean_id.startswith("NODE_"):
                    clean_id = f"NODE_{clean_id}"
                var_name = f"{clean_id}_AUTH_KEY"
                targets.append((("nodes", node_id, "auth_key"), var_name))

        # 3. Webhook sensitive headers
        notifications = model.get("notifications")
        if isinstance(notifications, dict):
            webhooks = notifications.get("webhooks")
            if isinstance(webhooks, dict):
                for w_id, w_cfg in webhooks.items():
                    if isinstance(w_cfg, dict):
                        headers = w_cfg.get("headers")
                        if isinstance(headers, dict):
                            clean_w = re.sub(r"[^A-Z0-9]", "_", str(w_id).upper())
                            if not clean_w.startswith("WEBHOOK_"):
                                clean_w = f"WEBHOOK_{clean_w}"
                            for hk in headers.keys():
                                if any(sec in str(hk).lower() for sec in ["auth", "token", "key", "secret", "bearer"]):
                                    clean_h = re.sub(r"[^A-Z0-9]", "_", str(hk).upper())
                                    var_name = f"{clean_w}_{clean_h}"
                                    targets.append((("notifications", "webhooks", w_id, "headers", hk), var_name))

        return targets

    def extract_and_sync_secrets(
        self,
        visual_model: Dict[str, Any],
        current_raw_yaml: Optional[str] = None,
        commit: bool = False,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Inspects visual_model for sensitive secrets.
        1. Plaintext secrets are replaced by ${VAR_NAME} in a clean copy of visual_model.
        2. Any existing template in current_raw_yaml is respected.
        3. If commit is True:
           - Atomic backup of .env to .env.bak
           - Writes secrets to .env via dotenv.set_key
           - Updates os.environ in-memory
        4. Returns (sanitized_visual_model, env_changes_audit_list).
        """
        model_copy = copy.deepcopy(visual_model)
        existing_dict: Dict[str, Any] = {}

        if current_raw_yaml:
            parsed, err, _ = parse_yaml(current_raw_yaml)
            if not err and parsed is not None:
                existing_dict = to_plain_dict(parsed)

        targets = self._discover_secret_targets(model_copy)
        env_changes: List[Dict[str, Any]] = []
        secrets_to_commit: Dict[str, str] = {}

        for path_tuple, default_var_name in targets:
            val = get_val_at_path(model_copy, path_tuple)
            if val is None or str(val).strip() == "":
                continue

            # If user explicitly entered an env template, keep it
            if is_env_template(val):
                continue

            # Check if active configuration on disk already uses an env template
            existing_val = get_val_at_path(existing_dict, path_tuple)
            existing_var = get_env_template_var_name(existing_val) if existing_val else None
            if existing_var and ENV_VAR_REGEX.match(existing_var):
                var_name = existing_var
            else:
                var_name = default_var_name

            # If masked sentinel, preserve existing template or variable reference
            if is_secret_masked(val):
                template_to_set = existing_val if is_env_template(existing_val) else f"${{{var_name}}}"
                set_val_at_path(model_copy, path_tuple, template_to_set)
                continue

            # Plaintext secret entered by operator: validate security
            validate_secret_security(var_name, val)
            str_val = str(val).strip()
            current_env_val = os.environ.get(var_name)

            needs_env_write = (current_env_val != str_val)
            needs_externalization = not is_env_template(existing_val)

            if needs_env_write:
                secrets_to_commit[var_name] = str_val

            if needs_env_write or needs_externalization:
                action = "created" if current_env_val is None else "updated"
                env_changes.append({
                    "variable": var_name,
                    "path": ".".join(str(p) for p in path_tuple),
                    "masked_value": "••••••••",
                    "action": action,
                })

            # Replace plaintext in model with ${VAR_NAME}
            set_val_at_path(model_copy, path_tuple, f"${{{var_name}}}")

        # Commit to .env if requested and changes exist
        if commit and secrets_to_commit:
            self._commit_to_env(secrets_to_commit)

        return model_copy, env_changes

    def _commit_to_env(self, secrets: Dict[str, str]) -> None:
        """
        Atomically backup .env to .env.bak, write new/updated keys via set_key,
        and synchronize in-memory os.environ.
        """
        # Ensure target file exists
        if not os.path.exists(self.dotenv_path):
            example_path = f"{self.dotenv_path}.example"
            if os.path.exists(example_path):
                shutil.copy2(example_path, self.dotenv_path)
            else:
                os.makedirs(os.path.dirname(self.dotenv_path), exist_ok=True)
                with open(self.dotenv_path, "w", encoding="utf-8") as f:
                    f.write("# Distributed IoT Controller Environment Configuration (.env)\n")

        # Create backup before modification
        backup_path = f"{self.dotenv_path}.bak"
        try:
            shutil.copy2(self.dotenv_path, backup_path)
        except Exception as e:
            self.logger.warning(f"Could not create .env backup at {backup_path}: {e}")

        # Apply each key and update os.environ
        try:
            for var_name, secret_val in secrets.items():
                dotenv.set_key(self.dotenv_path, var_name, secret_val, quote_mode="always")
                os.environ[var_name] = secret_val
                self.logger.info(f"Isolated secret for '{var_name}' into .env and synchronized os.environ")
        except Exception as e:
            # If writing failed and backup exists, attempt rollback
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, self.dotenv_path)
                    self.logger.warning(f"Rolled back .env from {backup_path} after failure: {e}")
                except Exception:
                    pass
            raise EnvSecurityError(f"Failed to write secrets to .env: {e}")
