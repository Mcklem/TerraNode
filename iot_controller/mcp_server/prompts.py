from typing import Any


def register_prompts(mcp: Any) -> None:
    """Register assistant prompt templates on the MCPServer instance."""

    @mcp.prompt(
        name="diagnose_system",
        description="Structured workflow to analyze system health, node connectivity, and detect anomalies.",
    )
    def diagnose_system_prompt() -> str:
        return (
            "You are an expert AI IoT Diagnostician for TerraNode.\n"
            "Please perform the following steps:\n"
            "1. Call `get_system_health` and `list_nodes` to inspect system state and offline nodes.\n"
            "2. Call `list_overrides` to check if any devices are locked in manual override mode.\n"
            "3. Call `list_devices` to inspect recent sensor values and alert on abnormal thresholds.\n"
            "4. Provide a clear summary with recommended actions."
        )

    @mcp.prompt(
        name="optimize_rules",
        description="Workflow to inspect sensor data and suggest rule adjustments for automation.",
    )
    def optimize_rules_prompt() -> str:
        return (
            "You are an AI Automation Specialist for TerraNode.\n"
            "1. Retrieve device statuses using `list_devices`.\n"
            "2. Query telemetry using `get_device_telemetry` for key sensors (e.g. soil moisture, light, temperature).\n"
            "3. Evaluate current threshold triggers and recommend optimizations or new automation rules."
        )
