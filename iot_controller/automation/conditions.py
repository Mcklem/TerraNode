import operator
from typing import Any, Dict

OPERATORS = {
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


def evaluate_condition(condition_cfg: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """Evaluate a declarative condition against an event payload."""
    if not condition_cfg:
        return False

    target_dev = condition_cfg.get("device")
    target_prop = condition_cfg.get("property", "value")
    op_symbol = condition_cfg.get("operator", "==")
    threshold = condition_cfg.get("value")

    # Check if payload matches target device
    device_id = payload.get("id") or payload.get("device")
    if target_dev and device_id != target_dev:
        return False

    actual_val = payload.get(target_prop)
    if actual_val is None:
        return False

    op_func = OPERATORS.get(op_symbol)
    if not op_func:
        raise ValueError(f"Unsupported condition operator '{op_symbol}'")

    try:
        return op_func(float(actual_val), float(threshold))
    except (ValueError, TypeError):
        return op_func(actual_val, threshold)
