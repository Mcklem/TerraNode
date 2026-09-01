import argparse
import asyncio
import os
import signal
import sys
from typing import Optional

# Ensure current directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.settings import settings
from core.system import ControllerSystem
from utils.logging import get_logger, setup_logging


async def main_async(config_path: Optional[str], db_url: Optional[str], use_mock: Optional[bool]) -> None:
    setup_logging(settings.get_log_level_int())
    logger = get_logger("Main")

    active_config = config_path or settings.config_path
    active_db_url = db_url or settings.database_url
    active_mock = use_mock if use_mock is not None else settings.mock_nodes

    logger.info(f"Loaded Settings: config='{active_config}', db_url='{active_db_url}', mock={active_mock}")

    if active_mock:
        logger.info("Running in SIMULATION MODE (--mock / MOCK_NODES=true). Nodes instantiated as MockNode.")

    system = ControllerSystem(
        config_path=active_config,
        database_url=active_db_url,
        use_mock=active_mock,
    )

    try:
        await system.start()
        logger.info("Press Ctrl+C to stop.")

        stop_event = asyncio.Event()

        def _signal_handler(*args):
            stop_event.set()

        loop = asyncio.get_running_loop()
        handlers_added = False
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
                handlers_added = True
            except NotImplementedError:
                pass

        if not handlers_added:
            # Windows fallback: register standard signal handler
            try:
                signal.signal(signal.SIGINT, lambda s, f: loop.call_soon_threadsafe(stop_event.set))
                signal.signal(signal.SIGTERM, lambda s, f: loop.call_soon_threadsafe(stop_event.set))
            except Exception:
                pass

        try:
            while not stop_event.is_set():
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
        except KeyboardInterrupt:
            pass

    except Exception as e:
        logger.critical(f"System fatal error: {e}", exc_info=True)
    finally:
        await system.stop()


def main():
    parser = argparse.ArgumentParser(description="Distributed IoT Hardware Controller")
    parser.add_argument(
        "-c", "--config", help="Path to system.yaml config file (default: from .env / settings)"
    )
    parser.add_argument(
        "-d", "--db", help="Database connection URL or path (default: from .env / settings)"
    )
    parser.add_argument(
        "-m", "--mock", action="store_true", help="Run with simulated MockNodes for testing"
    )
    args = parser.parse_args()

    mock_opt = True if args.mock else None

    try:
        asyncio.run(main_async(args.config, args.db, mock_opt))
    except KeyboardInterrupt:
        print("\nShutdown requested by user. Exiting.")


if __name__ == "__main__":
    main()
