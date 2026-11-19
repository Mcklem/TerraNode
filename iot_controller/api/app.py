import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import config, devices, events, firmware, health, history, nodes, notifications, overrides, rules, schedules


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.dependencies import system_container
    system_instance = None
    if system_container.node_manager is None:
        from core.system import ControllerSystem
        system_instance = ControllerSystem()
        await system_instance.start()
    try:
        yield
    finally:
        if system_instance:
            await system_instance.stop()


tags_metadata = [
    {
        "name": "Notifications",
        "description": (
            "Servicios de **notificaciones multi-canal** (Telegram Bot, Correo Electrónico SMTP y Webhooks personalizados), "
            "pruebas de conectividad en vivo y diagnósticos de alertas."
        ),
    },
    {
        "name": "Configuration",
        "description": (
            "Gestión visual y YAML de la **configuración del sistema (`system.yaml`)**, "
            "validación multi-nivel, diffs automáticos, historial de respaldos y recarga en caliente."
        ),
    },
    {
        "name": "Devices",
        "description": (
            "Operaciones sobre **sensores y actuadores**. Permite consultar lecturas en tiempo real, "
            "estados de salud hardware, emitir **comandos de control manual** (`turn_on`, `turn_off`, `set_position`) "
            "y restablecer el control automático a las reglas del sistema (`AUTO`)."
        ),
    },
    {
        "name": "Schedules",
        "description": (
            "Gestión y consulta de **Programaciones Temporales y Calendario (`TimeScheduler`)**. "
            "Permite programar la activación/desactivación de actuadores por hora fija (`HH:MM`), "
            "frecuencia por intervalo, duración activa (`duration`) y días de la semana/expresiones cron."
        ),
    },
    {
        "name": "History",
        "description": (
            "Consulta de **registros históricos y auditoría** almacenados en la base de datos (telemetría de "
            "sensores, comandos ejecutados en actuadores, conexiones de nodos y eventos del sistema) "
            "con soporte completo para **paginación (`limit`, `offset`) y filtros**."
        ),
    },
    {
        "name": "Overrides",
        "description": (
            "Gestión y consulta de **Overrides de Control Manual**. Permite listar todos los dispositivos que "
            "se encuentran bloqueados en modo manual (`MANUAL_ON`, `MANUAL_OFF`, `MANUAL_VALUE`), "
            "impidiendo que el motor de automatización (`RuleEngine`) modifique su estado."
        ),
    },
    {
        "name": "Nodes",
        "description": (
            "Información sobre los nodos hardware/mock registrados en `NodeManager` e invocación de **comandos "
            "de bajo nivel directamente sobre los pines físicos** (`digital_write`, `analog_write`)."
        ),
    },
    {
        "name": "Health",
        "description": (
            "Diagnósticos de salud operacional del sistema, estado de conexión de nodos, conteo de dispositivos y "
            "verificación de persistencia."
        ),
    },
    {
        "name": "Firmware Studio",
        "description": (
            "Gestión, generación, compilación y flasheo de **firmware para nodos IoT**. "
            "Soporta plantillas declarativas (`manifest.json`), configuración dinámica de parámetros, "
            "espacios de compilación aislados y flasheo directo por Web Serial."
        ),
    },
]

DESCRIPTION_MARKDOWN = """
## 🌿 TerraNode Distributed IoT Controller API

La API RESTful de TerraNode proporciona una interfaz desacoplada para el monitoreo, la telemetría y el **control en tiempo real** de hardware IoT distribuido.

### 🔑 Conceptos Clave de Control y Prevalencia

1. **Modos de Control Tri-Estado (`ControlMode`):**
   - **`AUTO`:** El dispositivo responde a los eventos y reglas del motor de automatización (`RuleEngine`) y programadores (`Scheduler` / `TimeScheduler`).
   - **`MANUAL_ON`:** El dispositivo se encuentra forzado a encendido. **Las reglas y tareas programadas son ignoradas/bloqueadas** si intentan apagarlo.
   - **`MANUAL_OFF`:** El dispositivo se encuentra forzado a apagado. Las reglas y tareas programadas son ignoradas si intentan encenderlo.
   - **`MANUAL_VALUE`:** Para actuadores analógicos/servos fijados manualmente a un valor específico.

2. **Comandos en Vivo (*Live Commands*):**
   - Al enviar un comando mediante `POST /api/v1/devices/{device_id}/command`, la orden se ejecuta de inmediato sobre el nodo físico y **fija el modo de override manual**.
   - Para devolver el dispositivo al control automático de reglas y schedules, se debe invocar `POST /api/v1/devices/{device_id}/restore-control`.

3. **Programación Temporal (`/api/v1/schedules`):**
   - Automatización basada en horas fijas, intervalos periódicos y temporizadores de duración activa (`duration`).

4. **Consultas Históricas Paginadas (`/api/v1/history`):**
   - Todos los endpoints históricos aceptan `limit` (por defecto 50, máx 500) y `offset` (desplazamiento para paginación) junto a filtros por `device_id`, `node_id`, `source` o `topic`.
"""


def create_app() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    app = FastAPI(
        title="TerraNode IoT Controller API",
        description=DESCRIPTION_MARKDOWN,
        version="1.0.0",
        openapi_tags=tags_metadata,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    from core.settings import settings

    # Configure CORS according to environment
    if settings.environment == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        configured_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=configured_origins or ["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        )

    # API Secret Key Authentication Middleware
    # In development mode, authentication is disabled by default to facilitate local DX and testing
    enforce_auth = settings.api_secret_key and (
        settings.environment != "development" or os.getenv("ENFORCE_DEV_AUTH", "false").lower() in ("true", "1")
    )
    if enforce_auth:
        from fastapi import Request
        from fastapi.responses import JSONResponse

        @app.middleware("http")
        async def api_key_auth_middleware(request: Request, call_next):
            # Exempt documentation and basic health check
            path = request.url.path
            exempt_paths = {"/docs", "/redoc", "/openapi.json", "/api/v1/health", "/favicon.ico"}
            if path in exempt_paths or request.method == "OPTIONS":
                return await call_next(request)

            # Check X-API-Key or Authorization: Bearer
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    api_key = auth_header[7:].strip()

            import secrets
            if not api_key or not secrets.compare_digest(api_key, settings.api_secret_key):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: Invalid or missing API Key."},
                )
            return await call_next(request)

    # Register routers
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(notifications.router)
    app.include_router(nodes.router)
    app.include_router(devices.router)
    app.include_router(overrides.router)
    app.include_router(events.router)
    app.include_router(history.router)
    app.include_router(rules.router)
    app.include_router(schedules.router)
    app.include_router(firmware.router)

    # Mount MCP Server SSE router if enabled in settings
    from core.settings import settings
    if settings.enable_mcp and settings.mcp_transport == "sse":
        from mcp_server.router import mount_mcp_to_fastapi
        mount_mcp_to_fastapi(app, path=settings.mcp_path)

    from fastapi.responses import JSONResponse

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    return app
