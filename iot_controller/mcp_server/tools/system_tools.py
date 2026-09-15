import json
from typing import Any
from api.dependencies import system_container


def register_system_tools(mcp: Any) -> None:
    """Register node, health, rule, and override system tools on the MCPServer instance."""

    @mcp.tool(
        name="list_nodes",
        description=(
            "Lists all physical and mock hardware nodes registered in NodeManager, including connection state "
            "(CONNECTED, DISCONNECTED, ERROR), driver type, host IP, and port."
        ),
    )
    def list_nodes() -> str:
        if system_container.node_manager is None:
            return json.dumps({"error": "NodeManager is not initialized."})

        nodes = system_container.node_manager.get_all_nodes()
        result = []
        for node in nodes:
            result.append(
                {
                    "id": node.id,
                    "driver": getattr(node, "driver", "unknown"),
                    "host": getattr(node, "host", None),
                    "port": getattr(node, "port", None),
                    "connected": node.is_connected(),
                }
            )
        return json.dumps({"count": len(result), "nodes": result}, indent=2, default=str)

    @mcp.tool(
        name="get_system_health",
        description=(
            "Retrieves operational health diagnostics for TerraNode, including total nodes online, "
            "active device counts, and system status metrics."
        ),
    )
    def get_system_health() -> str:
        if system_container.health_monitor is None:
            return json.dumps({"status": "HealthMonitor not active", "nodes_online": 0})

        health_data = system_container.health_monitor.get_status()
        return json.dumps(health_data, indent=2, default=str)

    @mcp.tool(
        name="list_overrides",
        description=(
            "Retrieves all devices currently under manual override (MANUAL_ON, MANUAL_OFF, MANUAL_VALUE), "
            "preventing automated rules from changing their state."
        ),
    )
    def list_overrides() -> str:
        if system_container.override_registry is None:
            return json.dumps({"count": 0, "overrides": []})

        overrides = system_container.override_registry.get_all_overrides()
        result = [
            {
                "device_id": dev_id,
                "mode": ov.mode.value,
                "set_at": ov.timestamp,
                "reason": ov.reason,
            }
            for dev_id, ov in overrides.items()
        ]
        return json.dumps({"count": len(result), "overrides": result}, indent=2, default=str)

    @mcp.tool(
        name="toggle_rule",
        description="Enables or disables a sensor-driven automation rule in RuleEngine by rule ID.",
    )
    def toggle_rule(rule_id: str, enabled: bool) -> str:
        if system_container.rule_engine is None:
            return json.dumps({"error": "RuleEngine is not initialized."})

        success = system_container.rule_engine.set_rule_enabled(rule_id, enabled)
        return json.dumps({"rule_id": rule_id, "enabled": enabled, "success": success})
