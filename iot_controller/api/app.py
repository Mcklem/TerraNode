from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import devices, health, nodes, overrides


tags_metadata = [
    {
        "name": "Devices",
        "description": (
            "Operaciones sobre **sensores y actuadores**. Permite consultar lecturas en tiempo real, "
            "estados de salud hardware, emitir **comandos de control manual** (`turn_on`, `turn_off`, `set_position`) "
            "y restablecer el control automático a las reglas del sistema (`AUTO`)."
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
]

DESCRIPTION_MARKDOWN = """
## 🌿 TerraNode Distributed IoT Controller API

La API RESTful de TerraNode proporciona una interfaz desacoplada para el monitoreo, la telemetría y el **control en tiempo real** de hardware IoT distribuido.

### 🔑 Conceptos Clave de Control y Prevalencia

1. **Modos de Control Tri-Estado (`ControlMode`):**
   - **`AUTO`:** El dispositivo responde a los eventos y reglas del motor de automatización (`RuleEngine`) y programadores (`Scheduler`).
   - **`MANUAL_ON`:** El dispositivo se encuentra forzado a encendido. **Las reglas automáticas son ignoradas/bloqueadas** si intentan apagarlo.
   - **`MANUAL_OFF`:** El dispositivo se encuentra forzado a apagado. Las reglas automáticas son ignoradas si intentan encenderlo.
   - **`MANUAL_VALUE`:** Para actuadores analógicos/servos fijados manualmente a un valor específico.

2. **Comandos en Vivo (*Live Commands*):**
   - Al enviar un comando mediante `POST /api/v1/devices/{device_id}/command`, la orden se ejecuta de inmediato sobre el nodo físico y **fija el modo de override manual**.
   - Para devolver el dispositivo al control automático de reglas, se debe invocar `POST /api/v1/devices/{device_id}/restore-control`.

3. **Catálogo de Comandos Frecuentes por Tipo de Actuador:**
   - **Relés (`relay`):** `action: "turn_on"`, `action: "turn_off"`
   - **Servomotores (`servo`):** `action: "set_position"`, `params: {"angle": 90}`
   - **Comandos Crudos a Pines (`/api/v1/nodes/{node_id}/pin`):** `command_type: "digital_write"`, `pin: "D5"`, `value: 1`
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

