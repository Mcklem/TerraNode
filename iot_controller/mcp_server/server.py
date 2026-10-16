from typing import Any
from mcp_server.tools.device_tools import register_device_tools
from mcp_server.tools.system_tools import register_system_tools
from mcp_server.resources import register_resources
from mcp_server.prompts import register_prompts

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer


def create_mcp_server() -> Any:
    """Factory function to build and configure the TerraNode MCP server instance."""
    mcp = MCPServer(
        name="TerraNode IoT Controller",
        instructions="TerraNode MCP Server for AI Agent Control and Monitoring of Distributed IoT Hardware."
    )

    # Register tools, resources, and prompts
    register_device_tools(mcp)
    register_system_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    return mcp


mcp_server = create_mcp_server()


def get_mcp_app() -> Any:
    """Returns the Starlette/ASGI application for SSE transport mounting."""
    if hasattr(mcp_server, "sse_app"):
        return mcp_server.sse_app()
    elif hasattr(mcp_server, "create_asgi_app"):
        return mcp_server.create_asgi_app()
    raise RuntimeError("MCP server instance does not support SSE/ASGI app generation.")
