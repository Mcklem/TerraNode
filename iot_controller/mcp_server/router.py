from fastapi import FastAPI
from mcp_server.server import get_mcp_app
from utils.logging import get_logger

logger = get_logger("MCPRouter")


def mount_mcp_to_fastapi(app: FastAPI, path: str = "/mcp") -> None:
    """Mounts the MCP Server SSE Starlette application into the main FastAPI application.

    :param app: Main FastAPI application instance.
    :param path: URL prefix path where MCP SSE endpoints will be served.
    """
    try:
        mcp_app = get_mcp_app()
        normalized_path = path if path.startswith("/") else f"/{path}"
        app.mount(normalized_path, mcp_app)
        logger.info(f"MCP Server SSE endpoints mounted successfully at '{normalized_path}'")
    except Exception as e:
        logger.error(f"Failed to mount MCP Server onto FastAPI: {e}", exc_info=True)
