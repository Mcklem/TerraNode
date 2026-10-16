import json
from typing import Any
from api.dependencies import system_container


def register_resources(mcp: Any) -> None:
    """Register dynamic system and device resources for AI clients."""

    @mcp.resource(
        uri="terranode://system/summary",
        name="TerraNode System Summary",
        description="Dynamic system overview containing health status, node counts, and active overrides.",
        mime_type="application/json",
    )
    def system_summary_resource() -> str:
        health = (
            system_container.health_monitor.get_system_health()
            if system_container.health_monitor
            else {}
        )
        nodes_cnt = (
            len(system_container.node_manager.get_all_nodes())
            if system_container.node_manager
            else 0
        )
        devices_cnt = (
            len(system_container.device_manager.get_all_devices())
            if system_container.device_manager
            else 0
        )
        overrides_cnt = (
            len(system_container.override_registry.get_all_overrides())
            if system_container.override_registry
            else 0
        )

        summary = {
            "health": health,
            "total_nodes": nodes_cnt,
            "total_devices": devices_cnt,
            "active_overrides": overrides_cnt,
        }
        return json.dumps(summary, indent=2, default=str)

    @mcp.resource(
        uri="terranode://devices/state",
        name="TerraNode Realtime Device States",
        description="Real-time map of all devices, control modes, and latest sensor readings.",
        mime_type="application/json",
    )
    def devices_state_resource() -> str:
        if system_container.device_manager is None:
            return json.dumps({})

        devices = system_container.device_manager.get_all_devices()
        result = {}
        for dev in devices:
            dev_id = getattr(dev, "id", str(dev))
            control_state = (
                system_container.override_registry.get_state(dev_id)
                if system_container.override_registry
                else None
            )
            status_val = dev.status.value if hasattr(dev, "status") and hasattr(dev.status, "value") else str(getattr(dev, "status", "UNKNOWN"))
            state = dev.get_state() if hasattr(dev, "get_state") else {}
            result[dev_id] = {
                "name": getattr(dev, "name", dev_id),
                "type": getattr(dev, "type", getattr(dev, "device_type", "unknown")),
                "control_mode": control_state.mode.value if control_state else "AUTO",
                "status": status_val,
                "state": state,
            }
        return json.dumps(result, indent=2, default=str)
