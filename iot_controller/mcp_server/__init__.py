"""TerraNode MCP Server Package.

Provides an independent Model Context Protocol (MCP) server module
reusing TerraNode core backend services (DeviceManager, LiveCommandService, HealthMonitor).
"""

from mcp_server.server import mcp_server, get_mcp_app

__all__ = ["mcp_server", "get_mcp_app"]
