import json
from typing import Any, Dict, Optional
from api.dependencies import system_container


def register_device_tools(mcp: Any) -> None:
    """Register device management, telemetry, and override tools on the MCPServer instance."""

    @mcp.tool(
        name="list_devices",
        description=(
            "Retrieves full status of all registered IoT devices (sensors and actuators). "
            "Returns device ID, name, type, pin/bus, active control mode (AUTO/MANUAL_ON/MANUAL_OFF/MANUAL_VALUE), "
            "and the latest status or reading."
        ),
    )
    def list_devices() -> str:
        if system_container.device_manager is None:
            return json.dumps({"error": "DeviceManager is not initialized in system container."})

        devices = system_container.device_manager.get_all_devices()
        result = []
        for dev_id, dev in devices.items():
            status = dev.get_status()
            override = None
            if system_container.override_registry:
                override = system_container.override_registry.get_override(dev_id)

            dev_info = {
                "id": dev_id,
                "name": getattr(dev, "name", dev_id),
                "type": dev.__class__.__name__,
                "device_type": getattr(dev, "type", "unknown"),
                "node_id": getattr(dev, "node_id", None),
                "control_mode": override.mode.value if override else "AUTO",
                "status": status,
            }
            result.append(dev_info)

        return json.dumps({"count": len(result), "devices": result}, indent=2, default=str)

    @mcp.tool(
        name="get_device_telemetry",
        description=(
            "Fetches historical sensor readings or telemetry logs from the database for a specific device."
        ),
    )
    async def get_device_telemetry(device_id: str, limit: int = 20) -> str:
        if system_container.db is None:
            return json.dumps({"error": "Database is not initialized in system container."})

        try:
            readings = await system_container.db.get_sensor_readings(device_id=device_id, limit=limit)
            return json.dumps(
                {"device_id": device_id, "count": len(readings), "telemetry": readings},
                indent=2,
                default=str,
            )
        except Exception as e:
            return json.dumps({"error": f"Failed to retrieve telemetry: {str(e)}"})

    @mcp.tool(
        name="execute_device_command",
        description=(
            "Sends a live command to an IoT device (e.g. 'turn_on', 'turn_off', 'set_position') and puts the device "
            "into manual override mode (MANUAL_ON, MANUAL_OFF, MANUAL_VALUE). "
            "While in manual mode, automation rules and schedules will be overridden for this device."
        ),
    )
    async def execute_device_command(
        device_id: str, command: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        if system_container.live_command_service is None:
            return json.dumps({"error": "LiveCommandService is not initialized."})

        try:
            params = params or {}
            result = await system_container.live_command_service.execute_command(
                device_id=device_id,
                command_name=command,
                args=params,
                source="MCP_AGENT",
            )
            return json.dumps(
                {"success": True, "device_id": device_id, "command": command, "result": result},
                indent=2,
                default=str,
            )
        except Exception as e:
            return json.dumps({"success": False, "device_id": device_id, "error": str(e)})

    @mcp.tool(
        name="restore_device_control",
        description=(
            "Restores an IoT device back to AUTO control mode, clearing any manual overrides. "
            "This allows automation rules and schedules to control the device again."
        ),
    )
    async def restore_device_control(device_id: str) -> str:
        if system_container.live_command_service is None:
            return json.dumps({"error": "LiveCommandService is not initialized."})

        try:
            success = await system_container.live_command_service.restore_auto_control(device_id)
            return json.dumps({"success": success, "device_id": device_id, "mode": "AUTO"})
        except Exception as e:
            return json.dumps({"success": False, "device_id": device_id, "error": str(e)})
