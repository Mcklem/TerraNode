# 🌿 TerraNode - Control IoT Distribuido y Automatización de Hardware

**TerraNode** es una plataforma modular, extensible y de alto rendimiento desarrollada en **Python 3** para el control en tiempo real, monitoreo de telemetría y automatización distribuida de hardware IoT (como nodos **NodeMCU ESP8266** sobre red WiFi / StandardFirmataWiFi o controladores centrales **Raspberry Pi / PC**).

---

## 🚀 Resumen del Proyecto

TerraNode permite conectar sensores y actuadores físicos de forma remota, ejecutando un motor de automatización de borde (*edge automation rule engine*), persistencia asíncrona de telemetría y una **API RESTful completa (FastAPI)** con soporte para comandos en vivo (*Live Commands*) y modos de anulación manual (*Manual Overrides*).

### 💡 Características Principales

- **Arquitectura Basada en Configuración (`YAML`)**: Define nodos, sensores, actuadores y reglas de automatización en `system.yaml` sin modificar una sola línea de código.
- **Modos de Control Tri-Estado (`ControlMode`)**:
  - **`AUTO`**: Las reglas del sistema (`RuleEngine`) y programadores (`Scheduler`) controlan los actuadores de forma automática.
  - **`MANUAL_ON` / `MANUAL_OFF` / `MANUAL_VALUE`**: Comandos emitidos desde la API REST o interfaz de usuario que **bloquean temporal o indefinidamente** las reglas automáticas (*Override Priority*).
  - **`RESTORE CONTROL`**: Devuelve los actuadores al control automático instantáneamente.
- **API RESTful Completa con FastAPI**: Documentación interactiva Swagger UI (`/docs`) y ReDoc (`/redoc`) con endpoints para dispositivos, nodos, estados de salud y anulación manual.
- **Sondeo de Sensores con Compensación de Drift**: Lecturas periódicas configurables con descarte de desviación temporal acumulativa.
- **Persistencia Asíncrona por Lotes (SQLite / SQLAlchemy)**: Ingesta de telemetría y eventos en cola asíncrona (`asyncio.Queue`) con transacciones agrupadas para eliminar bloqueos de base de datos.
- **Modo Simulación (`--mock`)**: Ejecuta el controlador completo sin hardware físico conectado, facilitando pruebas locales y desarrollo offline.
- **Auto-Reconexión y Salud de Nodos**: Monitor de salud integrado (`HealthMonitor`) que detecta caídas de red e intenta reconexiones no bloqueantes.

---

## 🏗️ Arquitectura del Sistema

```text
                               Central Controller (Raspberry Pi / PC)
                    ┌──────────────────────────────────────────────────────────┐
                    │                      main.py                             │
                    │                         │                                │
                    │                  ControllerSystem                        │
                    │ ┌───────────────────────┼──────────────────────────────┐ │
                    │ │ FastAPI Service       │ NodeManager                  │ │
                    │ │ LiveCommandService    │ DeviceManager                │ │
                    │ │ PinManager            │ EventBus (Async Pub-Sub)     │ │
                    │ │ Scheduler             │ RuleEngine (Edge Triggered)  │ │
                    │ │ StorageManager (Queue)│ HealthMonitor                │ │
                    │ └───────────────────────┴──────────────────────────────┘ │
                    └─────────────────────────┬────────────────────────────────┘
                                              │ LAN / WiFi
                            ┌─────────────────┼─────────────────┐
                            │                 │                 │
                            ▼                 ▼                 ▼
                       NodeMCU #1        NodeMCU #2        Mock Node
                      Firmata WiFi      Firmata WiFi       (Simulation)
                            │                 │                 │
                       ┌────┼────┐       ┌────┼────┐       ┌────┼────┐
                      LDR  BMP  RELAY   SERVO SOIL  ...   PUMP  ...  ...
```

---

## 📂 Estructura del Repositorio

```text
TerraNode/
├── README.md                      # Documentación general a alto nivel del repositorio
├── Basic Examples/                # Scripts sencillos de demostración y pruebas individuales
│   ├── bmp180_gy-68.py
│   ├── heartbeat.py
│   ├── ldr.py
│   ├── relay.py
│   ├── servo.py
│   └── readme.md
│
└── iot_controller/                # Paquete principal del controlador distribuido
    ├── main.py                    # Punto de entrada de la aplicación CLI
    ├── requirements.txt           # Lista de dependencias del proyecto
    ├── README.md                  # Documentación técnica detallada del controlador
    │
    ├── api/                       # Servicio Web FastAPI (Endpoints REST & Swagger UI)
    │   ├── app.py                 # Factoría y configuración de la app FastAPI
    │   ├── dependencies.py        # Inyección de dependencias de subsistemas
    │   └── routes/                # Rutas: devices, health, nodes, overrides
    │
    ├── automation/                # Motor de automatización y evaluación de condiciones
    │   ├── rule_engine.py         # Evaluador de reglas orientadas a bordes (edge-triggered)
    │   └── conditions.py          # Operadores relacionales (<, >, ==, etc.)
    │
    ├── config/                    # Plantillas y archivos de configuración del sistema
    │   ├── system.yaml            # Configuración activa
    │   └── system.example.yaml    # Ejemplo guía
    │
    ├── core/                      # Subsistemas principales y orquestador
    │   ├── system.py              # Secuencia determinista de arranque y apagado
    │   ├── config.py              # Validador y cargador de esquemas YAML
    │   ├── device_manager.py      # Ciclo de vida de dispositivos semánticos
    │   ├── node_manager.py        # Control de conexiones de nodos hardware
    │   ├── pin_manager.py         # Validación y prevención de conflictos de pines/I2C
    │   ├── scheduler.py           # Programador de lecturas periódicas de sensores
    │   ├── event_bus.py           # Bus pub-sub asíncrono desacoplado
    │   └── settings.py            # Gestión centralizada de variables de entorno (.env)
    │
    ├── devices/                   # Drivers de sensores y actuadores
    │   ├── sensors/               # Drivers: LDR, BMP180, SoilMoisture
    │   └── actuators/             # Drivers: Relay, Servo
    │
    ├── nodes/                     # Capa de abstracción de hardware y controladores
    │   ├── base_node.py           # Interfaz abstracta de nodo y mapa NodeMCU
    │   ├── firmata_node.py        # Driver de comunicación WiFi (Pymata4 / Firmata)
    │   └── mock_node.py           # Driver de simulación en memoria
    │
    ├── services/                  # Capa de servicios de control e intermediación
    │   └── live_command/          # Mediador de comandos manuales y prioridad de overrides
    │
    ├── storage/                   # Persistencia y base de datos
    │   ├── database.py            # Motor SQLAlchemy 2.0 ORM y tablas SQLite
    │   └── repositories.py        # Ingesta por lotes con cola asíncrona
    │
    ├── monitoring/                # Diagnóstico de salud y autoreconexión
    │   └── health.py              # Monitor de conectividad de nodos
    │
    └── tests/                     # Suite de pruebas unitarias e integración (38 tests)
```

---

## ⚡ Inicio Rápido

### 1. Requisitos Previos
- **Python 3.10+** instalado.

### 2. Instalación de Dependencias
```bash
cd iot_controller
pip install -r requirements.txt
```

### 3. Ejecución en Modo Simulación (`--mock`)
No necesitas hardware físico para probar la plataforma. Ejecuta en modo simulación:
```bash
python main.py --mock
```

Si deseas habilitar la API REST en modo simulación, edita el archivo `.env` o la variable de entorno `ENABLE_API=true`:
```bash
# Habilitar API REST y ejecutar con nodos simulados
ENABLE_API=true python main.py --mock
```
Ingresa desde tu navegador a `http://localhost:8000/docs` para interactuar con la interfaz Swagger de la API REST.

### 4. Ejecución de la Suite de Pruebas Unitarias
```bash
python -m unittest discover -s tests
```

---

## 📖 Documentación Adicional

Para más detalles sobre cómo configurar dispositivos en YAML, extender nuevos drivers de hardware o integrar la API REST en un Dashboard web, consulta la documentación en [iot_controller/README.md](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/README.md).
