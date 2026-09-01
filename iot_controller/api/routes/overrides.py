from fastapi import APIRouter, Depends
from typing import Any, Dict, List
from api.dependencies import get_override_registry
from services.live_command import OverrideRegistry

router = APIRouter(prefix="/api/v1/overrides", tags=["Overrides"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_active_overrides(override_reg: OverrideRegistry = Depends(get_override_registry)):
    """List all devices currently locked in manual override mode."""
    overrides = override_reg.get_all_overrides()
    result = []
    for st in overrides:
        result.append({
            "device_id": st.device_id,
            "mode": st.mode.value,
            "last_action": st.last_action,
            "override_source": st.override_source,
            "set_at": st.set_at,
            "expires_at": st.expires_at,
        })
    return result
