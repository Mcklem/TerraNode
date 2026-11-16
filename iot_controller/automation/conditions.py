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


def evaluate_condition(
    condition_cfg: Dict[str, Any],
    payload: Dict[str, Any],
    is_currently_triggered: bool = False,
) -> bool:
    """Evaluate a declarative condition against an event payload with optional hysteresis deadband support."""
    if not condition_cfg:
        return False

    target_dev = condition_cfg.get("device")
    target_prop = condition_cfg.get("property", "value")
    op_symbol = condition_cfg.get("operator", "==")
    threshold = condition_cfg.get("value")
    hysteresis = condition_cfg.get("hysteresis", 0)

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
        val_f = float(actual_val)
        thresh_f = float(threshold)
        hyst_f = abs(float(hysteresis)) if hysteresis else 0.0

        if is_currently_triggered and hyst_f > 0.0:
            # Apply deadband: retain active state until signal crosses hysteresis reset margin
            if op_symbol in (">", ">="):
                return val_f > (thresh_f - hyst_f)
            elif op_symbol in ("<", "<="):
                return val_f < (thresh_f + hyst_f)

        return op_func(val_f, thresh_f)
    except (ValueError, TypeError):
        return op_func(actual_val, threshold)
