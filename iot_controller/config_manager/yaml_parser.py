import copy
import io
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarint import BinaryInt, HexCapsInt, HexInt, OctalInt, ScalarInt
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, SingleQuotedScalarString

MASKED_SECRET_SENTINEL = "••••••••"
LEGACY_MASK_PREFIX = "********"


def create_yaml_engine(preserve_quotes: bool = True) -> YAML:
    """Create and configure a ruamel.yaml round-trip engine."""
    yaml_eng = YAML(typ="rt")
    yaml_eng.preserve_quotes = preserve_quotes
    yaml_eng.indent(mapping=2, sequence=4, offset=2)
    yaml_eng.width = 4096  # Prevent wrapping long lines
    return yaml_eng


def parse_yaml(content: str) -> Tuple[Optional[CommentedMap], Optional[str], Optional[int]]:
    """
    Parse a YAML string in round-trip mode.
    Returns: (parsed_data, error_message, error_line)
    """
    if not content or not content.strip():
        return CommentedMap(), None, None

    yaml_eng = create_yaml_engine()
    try:
        data = yaml_eng.load(content)
        if data is None:
            data = CommentedMap()
        elif not isinstance(data, (dict, CommentedMap)):
            return None, "Configuration root must be a YAML dictionary/mapping.", 1
        return data, None, None
    except YAMLError as e:
        line = getattr(e, "problem_mark", None)
        line_num = (line.line + 1) if line else None
        return None, str(e), line_num
    except Exception as e:
        return None, str(e), None


def serialize_yaml(data: Any) -> str:
    """Serialize CommentedMap or dict back to YAML string preserving comments."""
    yaml_eng = create_yaml_engine()
    out = io.StringIO()
    yaml_eng.dump(data, out)
    return out.getvalue()


def to_plain_dict(obj: Any) -> Any:
    """Recursively convert ruamel.yaml structures to native Python primitives (dict, list, etc.)."""
    if isinstance(obj, (HexInt, HexCapsInt)):
        return f"0x{obj:02x}"
    if isinstance(obj, (CommentedMap, dict)):
        return {str(k): to_plain_dict(v) for k, v in obj.items()}
    if isinstance(obj, (CommentedSeq, list)):
        return [to_plain_dict(item) for item in obj]
    return obj


def preserve_scalar_type(key: str, new_val: Any, current_val: Any = None) -> Any:
    """
    Preserve hexadecimal, octal, binary and quoted scalar formatting when updating CommentedMap.
    Ensures that hex integers in YAML (such as 'address: 0x77') are never changed to plain decimal
    integers ('119') or quoted strings, preserving exact hardware configuration compatibility.
    """
    is_address_key = key in ("address", "i2c_address") or str(key).endswith("_address")

    # If key represents a hardware/I2C address or existing scalar is a HexInt:
    if is_address_key or isinstance(current_val, (HexInt, HexCapsInt)):
        if isinstance(new_val, str) and re.match(r"^0x[0-9a-fA-F]+$", new_val.strip()):
            return HexInt(int(new_val.strip(), 16))
        if isinstance(new_val, int) and not isinstance(new_val, bool):
            return HexInt(new_val)

    # Any value given explicitly as a hex string (e.g. '0x3C')
    if isinstance(new_val, str) and re.match(r"^0x[0-9a-fA-F]+$", new_val.strip()):
        return HexInt(int(new_val.strip(), 16))

    # Octal & Binary integer preservation
    if isinstance(current_val, OctalInt) and isinstance(new_val, int) and not isinstance(new_val, bool):
        return OctalInt(new_val)
    if isinstance(current_val, BinaryInt) and isinstance(new_val, int) and not isinstance(new_val, bool):
        return BinaryInt(new_val)

    # If existing scalar is an env var template and new_val matches its resolved value, preserve the template
    if isinstance(current_val, str) and "${" in current_val:
        from core.config import interpolate_env_vars
        if str(new_val) == str(interpolate_env_vars(current_val)):
            return current_val

    # String quote style preservation
    if isinstance(current_val, DoubleQuotedScalarString) and isinstance(new_val, str):
        return DoubleQuotedScalarString(new_val)
    if isinstance(current_val, SingleQuotedScalarString) and isinstance(new_val, str):
        return SingleQuotedScalarString(new_val)

    return new_val


def normalize_devices(raw_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flattens devices defined under `nodes.<node_id>.devices.<dev_id>`
    into top-level `devices.<dev_id>` with an injected `"node": node_id`.
    Returns a copy of the normalized dict.
    """
    normalized = to_plain_dict(raw_config)
    if not isinstance(normalized, dict):
        return {}

    nodes = normalized.get("nodes", {})
    devices = normalized.get("devices", {})
    if not isinstance(devices, dict):
        devices = {}

    if isinstance(nodes, dict):
        for node_id, node_cfg in nodes.items():
            if not isinstance(node_cfg, dict):
                continue
            node_devices = node_cfg.get("devices")
            if isinstance(node_devices, dict):
                for dev_id, dev_cfg in node_devices.items():
                    if isinstance(dev_cfg, dict):
                        dev_copy = dict(dev_cfg)
                        dev_copy.setdefault("node", node_id)
                        devices[dev_id] = dev_copy

    normalized["devices"] = devices
    return normalized


def is_secret_masked(value: Any) -> bool:
    """Determine if a secret value is currently masked."""
    if not isinstance(value, str):
        return False
    val_clean = value.strip()
    return (
        val_clean == MASKED_SECRET_SENTINEL
        or val_clean == LEGACY_MASK_PREFIX
        or (len(val_clean) > 0 and all(c == "•" or c == "*" for c in val_clean))
        or val_clean == "__MASKED_SECRET__"
    )


SECRET_KEY_NAMES = {"auth_key", "password", "bot_token"}


def mask_secrets(data: Any) -> Any:
    """
    Create a deep copy of data with sensitive credentials replaced by MASKED_SECRET_SENTINEL.
    Target fields: `auth_key`, `password`, `bot_token`, and auth/token webhook headers.
    """
    plain = to_plain_dict(data)

    def _mask_node(n: Any):
        if isinstance(n, dict):
            for k, v in n.items():
                if k in SECRET_KEY_NAMES and v is not None and v != "":
                    n[k] = MASKED_SECRET_SENTINEL
                elif k == "headers" and isinstance(v, dict):
                    for hk, hv in v.items():
                        if any(sec in hk.lower() for sec in ["auth", "token", "key", "secret"]) and hv:
                            v[hk] = MASKED_SECRET_SENTINEL
                elif isinstance(v, (dict, list)):
                    _mask_node(v)
        elif isinstance(n, list):
            for item in n:
                _mask_node(item)

    _mask_node(plain)
    return plain


def mask_secrets_in_commented_map(target_map: CommentedMap) -> CommentedMap:
    """
    Mask secrets in-place on a CommentedMap to preserve comments, quotes, and scalar types (like HexInt).
    Used by the diff engine so credentials are redacted without destroying YAML formatting or comments.
    """
    if not isinstance(target_map, (dict, CommentedMap)):
        return target_map

    # 1. Nodes auth_key
    nodes = target_map.get("nodes")
    if isinstance(nodes, (dict, CommentedMap)):
        for node_id, node_cfg in nodes.items():
            if isinstance(node_cfg, (dict, CommentedMap)):
                if "auth_key" in node_cfg and node_cfg["auth_key"]:
                    node_cfg["auth_key"] = MASKED_SECRET_SENTINEL

    # 2. Notifications
    notif = target_map.get("notifications")
    if isinstance(notif, (dict, CommentedMap)):
        email = notif.get("email")
        if isinstance(email, (dict, CommentedMap)):
            if "password" in email and email["password"]:
                email["password"] = MASKED_SECRET_SENTINEL

        tel = notif.get("telegram")
        if isinstance(tel, (dict, CommentedMap)):
            if "bot_token" in tel and tel["bot_token"]:
                tel["bot_token"] = MASKED_SECRET_SENTINEL

        webhooks = notif.get("webhooks")
        if isinstance(webhooks, (dict, CommentedMap)):
            for w_id, w_cfg in webhooks.items():
                if isinstance(w_cfg, (dict, CommentedMap)):
                    headers = w_cfg.get("headers")
                    if isinstance(headers, (dict, CommentedMap)):
                        for hk, hv in list(headers.items()):
                            if any(sec in hk.lower() for sec in ["auth", "token", "key", "secret"]) and hv:
                                headers[hk] = MASKED_SECRET_SENTINEL

    return target_map


def unmask_secrets(new_data: Any, reference_data: Any) -> Any:
    """
    Restore original secret values from reference_data if new_data has a masked or empty sentinel.
    Target fields: `auth_key`, email `password`, telegram `bot_token`, and webhook header secrets.
    """
    ref_plain = to_plain_dict(reference_data) if reference_data is not None else {}
    new_plain = to_plain_dict(new_data) if new_data is not None else {}

    # 1. Node auth_key
    ref_nodes = ref_plain.get("nodes", {}) if isinstance(ref_plain, dict) else {}
    new_nodes = new_plain.get("nodes", {}) if isinstance(new_plain, dict) else {}

    if isinstance(new_nodes, dict) and isinstance(ref_nodes, dict):
        for node_id, new_node_cfg in new_nodes.items():
            if not isinstance(new_node_cfg, dict):
                continue
            ref_node_cfg = ref_nodes.get(node_id, {})
            if not isinstance(ref_node_cfg, dict):
                continue

            orig_key = ref_node_cfg.get("auth_key")
            new_key = new_node_cfg.get("auth_key")

            if orig_key:
                if new_key is None or is_secret_masked(new_key) or new_key == "":
                    new_node_cfg["auth_key"] = orig_key

    # 2. Notifications secrets
    ref_notif = ref_plain.get("notifications", {}) if isinstance(ref_plain, dict) else {}
    new_notif = new_plain.get("notifications", {}) if isinstance(new_plain, dict) else {}

    if isinstance(new_notif, dict) and isinstance(ref_notif, dict):
        # Email password
        ref_email = ref_notif.get("email", {})
        new_email = new_notif.get("email", {})
        if isinstance(ref_email, dict) and isinstance(new_email, dict):
            orig_pwd = ref_email.get("password")
            curr_pwd = new_email.get("password")
            if orig_pwd and (curr_pwd is None or is_secret_masked(curr_pwd) or curr_pwd == ""):
                new_email["password"] = orig_pwd

        # Telegram bot_token
        ref_tel = ref_notif.get("telegram", {})
        new_tel = new_notif.get("telegram", {})
        if isinstance(ref_tel, dict) and isinstance(new_tel, dict):
            orig_tok = ref_tel.get("bot_token")
            curr_tok = new_tel.get("bot_token")
            if orig_tok and (curr_tok is None or is_secret_masked(curr_tok) or curr_tok == ""):
                new_tel["bot_token"] = orig_tok

        # Webhook headers
        ref_webhooks = ref_notif.get("webhooks", {})
        new_webhooks = new_notif.get("webhooks", {})
        if isinstance(ref_webhooks, dict) and isinstance(new_webhooks, dict):
            for w_id, new_w in new_webhooks.items():
                if not isinstance(new_w, dict):
                    continue
                ref_w = ref_webhooks.get(w_id, {})
                if not isinstance(ref_w, dict):
                    continue
                ref_headers = ref_w.get("headers", {})
                new_headers = new_w.get("headers", {})
                if isinstance(ref_headers, dict) and isinstance(new_headers, dict):
                    for hk, hv in new_headers.items():
                        if is_secret_masked(hv) and hk in ref_headers:
                            new_headers[hk] = ref_headers[hk]

    return new_plain


def restore_masked_secrets_in_commented_map(
    target_map: CommentedMap,
    reference_data: Any,
) -> None:
    """
    In-place scan of target_map to replace any masked secret with the real secret from reference_data.
    Preserves all comments and existing structure.
    """
    ref_plain = to_plain_dict(reference_data) if reference_data is not None else {}
    ref_nodes = ref_plain.get("nodes", {}) if isinstance(ref_plain, dict) else {}

    # Nodes
    target_nodes = target_map.get("nodes")
    if isinstance(target_nodes, (dict, CommentedMap)) and isinstance(ref_nodes, dict):
        for node_id, node_cfg in target_nodes.items():
            if isinstance(node_cfg, (dict, CommentedMap)):
                ref_node = ref_nodes.get(node_id, {})
                if isinstance(ref_node, dict):
                    orig_key = ref_node.get("auth_key")
                    curr_key = node_cfg.get("auth_key")
                    if orig_key and (curr_key is None or is_secret_masked(curr_key) or curr_key == ""):
                        node_cfg["auth_key"] = orig_key

    # Notifications
    ref_notif = ref_plain.get("notifications", {}) if isinstance(ref_plain, dict) else {}
    target_notif = target_map.get("notifications")
    if isinstance(target_notif, (dict, CommentedMap)) and isinstance(ref_notif, dict):
        # Email
        ref_email = ref_notif.get("email", {})
        target_email = target_notif.get("email")
        if isinstance(target_email, (dict, CommentedMap)) and isinstance(ref_email, dict):
            orig_pwd = ref_email.get("password")
            curr_pwd = target_email.get("password")
            if orig_pwd and (curr_pwd is None or is_secret_masked(curr_pwd) or curr_pwd == ""):
                target_email["password"] = orig_pwd

        # Telegram
        ref_tel = ref_notif.get("telegram", {})
        target_tel = target_notif.get("telegram")
        if isinstance(target_tel, (dict, CommentedMap)) and isinstance(ref_tel, dict):
            orig_tok = ref_tel.get("bot_token")
            curr_tok = target_tel.get("bot_token")
            if orig_tok and (curr_tok is None or is_secret_masked(curr_tok) or curr_tok == ""):
                target_tel["bot_token"] = orig_tok

        # Webhooks
        ref_webhooks = ref_notif.get("webhooks", {})
        target_webhooks = target_notif.get("webhooks")
        if isinstance(target_webhooks, (dict, CommentedMap)) and isinstance(ref_webhooks, dict):
            for w_id, w_cfg in target_webhooks.items():
                if isinstance(w_cfg, (dict, CommentedMap)):
                    ref_w = ref_webhooks.get(w_id, {})
                    if isinstance(ref_w, dict):
                        ref_headers = ref_w.get("headers", {})
                        curr_headers = w_cfg.get("headers")
                        if isinstance(curr_headers, (dict, CommentedMap)) and isinstance(ref_headers, dict):
                            for hk, hv in curr_headers.items():
                                if is_secret_masked(hv) and hk in ref_headers:
                                    curr_headers[hk] = ref_headers[hk]



def apply_visual_model_to_commented_map(
    target_map: CommentedMap,
    visual_model: Dict[str, Any],
    original_reference: Optional[Dict[str, Any]] = None,
) -> CommentedMap:
    """
    Updates target_map in-place using the structured visual model.
    Preserves all comments, ordering, and structure where elements exist.
    """
    # Unmask any preserved secrets
    clean_model = unmask_secrets(visual_model, original_reference or target_map)

    # 1. Update system section
    if "system" in clean_model and isinstance(clean_model["system"], dict):
        if "system" not in target_map or not isinstance(target_map["system"], (dict, CommentedMap)):
            target_map["system"] = CommentedMap()
        sys_target = target_map["system"]
        for k, v in clean_model["system"].items():
            sys_target[k] = preserve_scalar_type(k, v, sys_target.get(k))
        # Remove any keys deleted from visual model
        for k in list(sys_target.keys()):
            if k not in clean_model["system"]:
                del sys_target[k]

    # 2. Update nodes and their nested devices
    # In TerraNode canonical YAML, devices are nested under nodes[node_id]['devices'].
    # The visual model provides both `nodes` and `devices` (which each have a `node` pointer).
    nodes_model = clean_model.get("nodes", {})
    devices_model = clean_model.get("devices", {})

    # Group devices by node_id
    devices_by_node: Dict[str, Dict[str, Any]] = {}
    if isinstance(devices_model, dict):
        for dev_id, dev_cfg in devices_model.items():
            if isinstance(dev_cfg, dict):
                node_id = dev_cfg.get("node")
                if node_id:
                    dev_clean = dict(dev_cfg)
                    dev_clean.pop("node", None)  # Clean out redundant parent pointer
                    devices_by_node.setdefault(node_id, {})[dev_id] = dev_clean

    if "nodes" not in target_map or not isinstance(target_map["nodes"], (dict, CommentedMap)):
        target_map["nodes"] = CommentedMap()
    nodes_target = target_map["nodes"]

    if isinstance(nodes_model, dict):
        # Update or add nodes
        for node_id, node_cfg in nodes_model.items():
            if not isinstance(node_cfg, dict):
                continue
            if node_id not in nodes_target or not isinstance(nodes_target[node_id], (dict, CommentedMap)):
                nodes_target[node_id] = CommentedMap()
            curr_node = nodes_target[node_id]

            # Copy node fields
            for k, v in node_cfg.items():
                if k == "devices":
                    continue  # Handled separately
                curr_node[k] = preserve_scalar_type(k, v, curr_node.get(k))

            # Remove deleted node fields
            for k in list(curr_node.keys()):
                if k != "devices" and k not in node_cfg:
                    del curr_node[k]

            # Update nested devices for this node
            node_devs = devices_by_node.get(node_id, {})
            if node_devs or "devices" in curr_node:
                if "devices" not in curr_node or not isinstance(curr_node["devices"], (dict, CommentedMap)):
                    curr_node["devices"] = CommentedMap()
                target_devs = curr_node["devices"]

                for dev_id, dev_props in node_devs.items():
                    if dev_id not in target_devs or not isinstance(target_devs[dev_id], (dict, CommentedMap)):
                        target_devs[dev_id] = CommentedMap()
                    curr_dev = target_devs[dev_id]

                    for pk, pv in dev_props.items():
                        if isinstance(pv, dict):
                            if pk not in curr_dev or not isinstance(curr_dev[pk], (dict, CommentedMap)):
                                curr_dev[pk] = CommentedMap()
                            target_sub = curr_dev[pk]
                            for subk, subv in pv.items():
                                target_sub[subk] = preserve_scalar_type(subk, subv, target_sub.get(subk))
                            for subk in list(target_sub.keys()):
                                if subk not in pv:
                                    del target_sub[subk]
                        else:
                            curr_dev[pk] = preserve_scalar_type(pk, pv, curr_dev.get(pk))

                    for pk in list(curr_dev.keys()):
                        if pk not in dev_props:
                            del curr_dev[pk]

                # Remove deleted devices from this node
                for dev_id in list(target_devs.keys()):
                    if dev_id not in node_devs:
                        del target_devs[dev_id]

        # Remove deleted nodes
        for node_id in list(nodes_target.keys()):
            if node_id not in nodes_model:
                del nodes_target[node_id]

    # If the original file had top-level devices and any device had no node or top-level devices were used:
    if "devices" in target_map and isinstance(target_map["devices"], (dict, CommentedMap)):
        # If devices are already nested under nodes, we can clean up or synchronize top-level devices
        if not devices_by_node:
            del target_map["devices"]

    # 3. Update rules section
    rules_model = clean_model.get("rules", {})
    if isinstance(rules_model, dict):
        if "rules" not in target_map or not isinstance(target_map["rules"], (dict, CommentedMap)):
            target_map["rules"] = CommentedMap()
        rules_target = target_map["rules"]

        for rule_id, rule_cfg in rules_model.items():
            if not isinstance(rule_cfg, dict):
                continue
            if rule_id not in rules_target or not isinstance(rules_target[rule_id], (dict, CommentedMap)):
                rules_target[rule_id] = CommentedMap()
            curr_rule = rules_target[rule_id]

            for k, v in rule_cfg.items():
                curr_rule[k] = preserve_scalar_type(k, v, curr_rule.get(k))
            for k in list(curr_rule.keys()):
                if k not in rule_cfg:
                    del curr_rule[k]

        for rule_id in list(rules_target.keys()):
            if rule_id not in rules_model:
                del rules_target[rule_id]

    # 4. Update schedules section
    schedules_model = clean_model.get("schedules", {})
    if isinstance(schedules_model, dict):
        if "schedules" not in target_map or not isinstance(target_map["schedules"], (dict, CommentedMap)):
            target_map["schedules"] = CommentedMap()
        sched_target = target_map["schedules"]

        for sched_id, sched_cfg in schedules_model.items():
            if not isinstance(sched_cfg, dict):
                continue
            if sched_id not in sched_target or not isinstance(sched_target[sched_id], (dict, CommentedMap)):
                sched_target[sched_id] = CommentedMap()
            curr_sched = sched_target[sched_id]

            for k, v in sched_cfg.items():
                curr_sched[k] = preserve_scalar_type(k, v, curr_sched.get(k))
            for k in list(curr_sched.keys()):
                if k not in sched_cfg:
                    del curr_sched[k]

        for sched_id in list(sched_target.keys()):
            if sched_id not in schedules_model:
                del sched_target[sched_id]

    # 5. Update notifications section
    notifications_model = clean_model.get("notifications")
    if isinstance(notifications_model, dict):
        if "notifications" not in target_map or not isinstance(target_map["notifications"], (dict, CommentedMap)):
            target_map["notifications"] = CommentedMap()
        notif_target = target_map["notifications"]

        for sub_sec in ["email", "telegram", "webhooks"]:
            if sub_sec in notifications_model and isinstance(notifications_model[sub_sec], dict):
                if sub_sec not in notif_target or not isinstance(notif_target[sub_sec], (dict, CommentedMap)):
                    notif_target[sub_sec] = CommentedMap()
                target_sub = notif_target[sub_sec]

                if sub_sec == "webhooks":
                    webhooks_map = notifications_model["webhooks"]
                    for w_id, w_cfg in webhooks_map.items():
                        if not isinstance(w_cfg, dict):
                            continue
                        if w_id not in target_sub or not isinstance(target_sub[w_id], (dict, CommentedMap)):
                            target_sub[w_id] = CommentedMap()
                        w_item = target_sub[w_id]
                        for wk, wv in w_cfg.items():
                            if wk == "headers" and isinstance(wv, dict):
                                if "headers" not in w_item or not isinstance(w_item["headers"], (dict, CommentedMap)):
                                    w_item["headers"] = CommentedMap()
                                target_h = w_item["headers"]
                                for hk, hv in wv.items():
                                    target_h[hk] = preserve_scalar_type(hk, hv, target_h.get(hk))
                                for hk in list(target_h.keys()):
                                    if hk not in wv:
                                        del target_h[hk]
                            else:
                                w_item[wk] = preserve_scalar_type(wk, wv, w_item.get(wk))
                        for wk in list(w_item.keys()):
                            if wk not in w_cfg:
                                del w_item[wk]
                    # Remove deleted webhooks
                    for w_id in list(target_sub.keys()):
                        if w_id not in webhooks_map:
                            del target_sub[w_id]
                else:
                    sub_model = notifications_model[sub_sec]
                    for k, v in sub_model.items():
                        target_sub[k] = preserve_scalar_type(k, v, target_sub.get(k))
                    for k in list(target_sub.keys()):
                        if k not in sub_model:
                            del target_sub[k]
            elif sub_sec in notif_target and sub_sec not in notifications_model:
                del notif_target[sub_sec]

        for k in list(notif_target.keys()):
            if k not in notifications_model:
                del notif_target[k]

    return target_map
