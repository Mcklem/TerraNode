import argparse
import asyncio
import os
import sys
from typing import Optional

# Ensure current directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.settings import settings
from core.system import ControllerSystem
from mcp_server import mcp_server, get_mcp_app
from utils.logging import get_logger, setup_logging

logger = get_logger("MainMCP")


async def main_mcp_async(
    config_path: Optional[str],
    db_url: Optional[str],
    use_mock: Optional[bool],
    transport: str,
    port: int,
) -> None:
    setup_logging(settings.get_log_level_int())

    active_config = config_path or settings.config_path
    active_db_url = db_url or settings.database_url
    active_mock = use_mock if use_mock is not None else settings.mock_nodes

    logger.info(
        f"Starting TerraNode MCP Standalone Server: config='{active_config}', db_url='{active_db_url}', mock={active_mock}, transport='{transport}'"
    )

    # Boot core ControllerSystem (without internal API server) to initialize dependencies
    system = ControllerSystem(
        config_path=active_config,
        database_url=active_db_url,
        use_mock=active_mock,
    )

    try:
        await system.start()
        logger.info("TerraNode backend system initialized. Launching MCP Server transport...")

        if transport == "stdio":
            logger.info("MCP Server listening on standard I/O (STDIO JSON-RPC)...")
            if hasattr(mcp_server, "run_stdio_async"):
                await mcp_server.run_stdio_async()
            else:
                await mcp_server.run(transport="stdio")
        elif transport == "sse":
            import uvicorn
            from fastapi import FastAPI
            from mcp_server.router import mount_mcp_to_fastapi

            mcp_app_container = FastAPI(title="TerraNode Standalone MCP Server")
            mount_mcp_to_fastapi(mcp_app_container, path="/mcp")

            config = uvicorn.Config(
                app=mcp_app_container,
                host="0.0.0.0",
                port=port,
                log_level="info",
            )
            server = uvicorn.Server(config)
            logger.info(f"MCP Standalone SSE Server running on http://0.0.0.0:{port}/mcp")
            await server.serve()
        else:
            raise ValueError(f"Unsupported transport '{transport}'. Choose 'stdio' or 'sse'.")

    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
    except Exception as e:
        logger.critical(f"MCP Server error: {e}", exc_info=True)
    finally:
        logger.info("Stopping TerraNode backend system...")
        await system.stop()


def main():
    parser = argparse.ArgumentParser(description="TerraNode Standalone MCP Server")
    parser.add_argument("-c", "--config", help="Path to system.yaml config file")
    parser.add_argument("-d", "--db", help="Database connection URL or path")
    parser.add_argument("-m", "--mock", action="store_true", help="Run with simulated MockNodes")
    parser.add_argument(
        "-t",
        "--transport",
        choices=["stdio", "sse"],
        default=settings.mcp_transport,
        help="MCP Transport protocol ('stdio' or 'sse', default: from settings / .env)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8001,
        help="Port for standalone SSE server (default: 8001)",
    )
    args = parser.parse_args()

    mock_opt = True if args.mock else None

    try:
        asyncio.run(main_mcp_async(args.config, args.db, mock_opt, args.transport, args.port))
    except KeyboardInterrupt:
        print("\nShutdown requested by user. Exiting.")


if __name__ == "__main__":
    main()
