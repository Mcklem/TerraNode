import difflib
from typing import Any, Dict, List, Set, Tuple
from config_manager.models import DiffResult
from config_manager.yaml_parser import (
    MASKED_SECRET_SENTINEL,
    create_yaml_engine,
    mask_secrets,
    mask_secrets_in_commented_map,
    normalize_devices,
    parse_yaml,
    serialize_yaml,
    to_plain_dict,
)


def redact_secrets_in_yaml_text(yaml_text: str) -> str:
    """Parse YAML, mask any secrets directly on CommentedMap, and serialize preserving comments, formatting, and hex scalars."""
    parsed, err, _ = parse_yaml(yaml_text)
    if err or parsed is None:
        return yaml_text
    mask_secrets_in_commented_map(parsed)
    return serialize_yaml(parsed)


def compute_unified_diff(current_yaml: str, proposed_yaml: str) -> str:
    """Generate a clean unified diff between current and proposed YAML with secrets redacted."""
    redacted_cur = redact_secrets_in_yaml_text(current_yaml)
    redacted_prop = redact_secrets_in_yaml_text(proposed_yaml)

    cur_lines = redacted_cur.splitlines(keepends=True)
    prop_lines = redacted_prop.splitlines(keepends=True)

    diff = difflib.unified_diff(
        cur_lines,
        prop_lines,
        fromfile="active/system.yaml",
        tofile="proposed/system.yaml",
        n=3,
    )
    return "".join(diff)


def compute_structured_diff(
    current_dict: Dict[str, Any],
    proposed_dict: Dict[str, Any],
) -> Tuple[List[str], List[str], List[str]]:
    """
    Compare current and proposed normalized dictionaries.
    Returns: (added_keys, removed_keys, modified_keys)
    """
    cur_norm = normalize_devices(current_dict or {})
    prop_norm = normalize_devices(proposed_dict or {})

    added: List[str] = []
    removed: List[str] = []
    modified: List[str] = []

    sections = ["system", "nodes", "devices", "rules", "schedules", "notifications"]

    for sec in sections:
        cur_sec = cur_norm.get(sec, {})
        prop_sec = prop_norm.get(sec, {})

        if not isinstance(cur_sec, dict):
            cur_sec = {}
        if not isinstance(prop_sec, dict):
            prop_sec = {}

        cur_keys = set(cur_sec.keys())
        prop_keys = set(prop_sec.keys())

        # Added
        for k in sorted(prop_keys - cur_keys):
            added.append(f"{sec}.{k}")

        # Removed
        for k in sorted(cur_keys - prop_keys):
            removed.append(f"{sec}.{k}")

        # Modified
        for k in sorted(cur_keys & prop_keys):
            if cur_sec[k] != prop_sec[k]:
                modified.append(f"{sec}.{k}")

    return added, removed, modified


class DiffEngine:
    """Provides visual diffing and structural change analysis."""

    @classmethod
    def generate_diff(cls, current_yaml: str, proposed_yaml: str) -> DiffResult:
        """Generate comprehensive diff result."""
        unified = compute_unified_diff(current_yaml, proposed_yaml)
        has_changes = bool(unified.strip())

        cur_parsed, _, _ = parse_yaml(current_yaml)
        prop_parsed, _, _ = parse_yaml(proposed_yaml)

        cur_plain = to_plain_dict(cur_parsed) if cur_parsed else {}
        prop_plain = to_plain_dict(prop_parsed) if prop_parsed else {}

        added, removed, modified = compute_structured_diff(cur_plain, prop_plain)

        return DiffResult(
            unified_diff=unified,
            has_changes=has_changes,
            added_keys=added,
            removed_keys=removed,
            modified_keys=modified,
        )
