from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import devices, health, nodes, overrides


def create_app() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    app = FastAPI(
        title="TerraNode IoT Controller API",
        description="RESTful Web API for live hardware commands, device monitoring, overrides, and health diagnostics.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Enable CORS for web UI dashboards
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router)
    app.include_router(nodes.router)
    app.include_router(devices.router)
    app.include_router(overrides.router)

    return app
