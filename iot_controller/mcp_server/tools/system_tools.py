import json
from typing import Any, Optional
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

        health_data = system_container.health_monitor.get_system_health()
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
                "device_id": st.device_id,
                "mode": st.mode.value,
                "set_at": st.set_at,
                "last_action": st.last_action,
                "source": st.override_source,
            }
            for st in overrides
        ]
        return json.dumps({"count": len(result), "overrides": result}, indent=2, default=str)

    @mcp.tool(
        name="list_rules",
        description="Lists all automation rules, their configurations, thresholds, enabled states, and trigger statuses.",
    )
    def list_rules() -> str:
        if system_container.rule_engine is None:
            return json.dumps({"error": "RuleEngine is not initialized."})

        rules = system_container.rule_engine.get_rule_states()
        return json.dumps({"count": len(rules), "rules": rules}, indent=2, default=str)

    @mcp.tool(
        name="toggle_rule",
        description="Enables or disables a sensor-driven automation rule in RuleEngine by rule ID.",
    )
    def toggle_rule(rule_id: str, enabled: Optional[bool] = None) -> str:
        if system_container.rule_engine is None:
            return json.dumps({"error": "RuleEngine is not initialized."})

        cfg = system_container.rule_engine.rules_config.get(rule_id)
        if not cfg:
            return json.dumps({"error": f"Rule '{rule_id}' not found."})

        if enabled is not None:
            cfg["enabled"] = enabled
            if not enabled:
                system_container.rule_engine._rule_states[rule_id] = False
            new_state = enabled
        else:
            new_state = system_container.rule_engine.toggle_rule(rule_id)

        return json.dumps({"rule_id": rule_id, "enabled": new_state, "success": True})
