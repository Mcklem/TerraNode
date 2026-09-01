# Distributed IoT Hardware Controller (Raspberry Pi Central Controller)

Plataforma modular y extensible en **Python 3** diseñada para ejecutarse como controlador central en **Raspberry Pi**, gestionando múltiples nodos **NodeMCU ESP8266** conectados vía WiFi mediante **StandardFirmataWiFi** (`pymata4`).

---

## 1. Arquitectura del Sistema

El sistema implementa una arquitectura por capas estrictamente desacopladas basadas en configuración:

```text
                               Central Controller (Raspberry Pi)
                    ┌──────────────────────────────────────────────────┐
                    │                   main.py                        │
                    │                      │                           │
                    │               ControllerSystem                   │
                    │ ┌────────────────────┼─────────────────────────┐ │
                    │ │ ConfigLoader       │ NodeManager             │ │
                    │ │ PinManager         │ DeviceManager           │ │
                    │ │ Scheduler          │ EventBus                │ │
                    │ │ RuleEngine         │ HealthMonitor           │ │
                    │ │ SQLite Storage     │ DeviceRegistry          │ │
                    │ └────────────────────┴─────────────────────────┘ │
                    └──────────────────────┬───────────────────────────┘
                                           │ LAN / WiFi
                         ┌─────────────────┼─────────────────┐
                         │                 │                 │
                         ▼                 ▼                 ▼
                    NodeMCU #1        NodeMCU #2        NodeMCU #N
                  Firmata WiFi      Firmata WiFi      Firmata WiFi
                         │                 │                 │
                    ┌────┼────┐       ┌────┼────┐       ┌────┼────┐
                   LDR  BMP  RELAY   SERVO SOIL  ...   PUMP  ...  ...
```

### Principios Arquitectónicos
1. **Configuration-Driven**: Todos los nodos, dispositivos y reglas de automatización se definen en `config/system.yaml`. Añadir o quitar dispositivos no requiere modificar el código central.
2. **Abstracción de Hardware**: Las capas superiores y el motor de reglas trabajan exclusivamente con identidades semánticas (`soil_01.read()`, `irrigation_pump.turn_on()`, `vent_servo.set_position(90)`) resolviendo internamente los pines físicos y buses I2C.
3. **Resiliencia & Tolerancia a Fallos**: La desconexión o fallo de un nodo/sensor no detiene el controlador central. El monitor de salud reconecta automáticamente con backoff exponencial.

---

## 2. Estructura del Proyecto

```text
iot_controller/
├── main.py                    # Punto de entrada principal
├── requirements.txt           # Dependencias de Python
├── README.md                  # Manual de arquitectura y uso
│
├── config/
│   └── system.yaml            # Configuración completa del sistema
│
├── core/
│   ├── system.py              # Orquestador del sistema (14-step startup)
│   ├── config.py              # Cargador y validador de configuración YAML
│   ├── node_manager.py        # Gestor del ciclo de vida de nodos hardware
│   ├── device_manager.py      # Gestor de creación y estado de dispositivos
│   ├── pin_manager.py         # Registro y detección de conflictos de pines
│   ├── registry.py            # Registro dinámico de drivers (DeviceRegistry)
│   ├── event_bus.py           # Bus de eventos asíncrono pub-sub
│   └── scheduler.py           # Programador central de lecturas de sensores
│
├── nodes/
│   ├── base_node.py           # Clase abstracta BaseNode y mapa de pines NodeMCU
│   ├── firmata_node.py        # Implementación FirmataNode sobre Pymata4 TCP
│   └── mock_node.py           # Nodo simulación en memoria para tests offline
│
├── devices/
│   ├── base_device.py         # Abstracción BaseDevice y estados
│   ├── sensor.py              # Clase base Sensor
│   ├── actuator.py            # Clase base Actuator
│   ├── sensors/
│   │   ├── ldr.py             # Driver sensor de luz LDR (analógico A0)
│   │   ├── bmp180.py          # Driver sensor I2C BMP180 (Temp, Presión, Altitud)
│   │   └── soil_moisture.py   # Driver humedad de suelo con calibración dry/wet
│   └── actuators/
│       ├── relay.py           # Driver relé digital con soporte active_low
│       └── servo.py           # Driver servo PWM con rango 0°-180°
│
├── automation/
│   ├── rule_engine.py         # Motor de reglas declarativas YAML
│   └── conditions.py          # Evaluador de operadores relacionales (<, >, ==, etc.)
│
├── storage/
│   ├── database.py            # Gestor de base de datos SQLite asíncrona (controller.db)
│   └── repositories.py        # Persistencia de mediciones y registros históricos
│
├── monitoring/
│   └── health.py              # Monitor de salud y reconexión automática de nodos
│
├── utils/
│   └── logging.py             # Formateador de logs con contexto [node_id][device_id]
│
└── tests/                     # Suite de pruebas unitarias e integración
    ├── test_config.py
    ├── test_pin_manager.py
    ├── test_node_manager.py
    ├── test_device_manager.py
    ├── test_drivers.py
    ├── test_event_bus.py
    ├── test_scheduler.py
    ├── test_rule_engine.py
    ├── test_storage.py
    └── test_system.py
```

---

## 3. Instalación y Requisitos

### Requisitos previos
- Python 3.9 o superior.
- NodeMCU ESP8266 flasheado con **StandardFirmataWiFi** (escuchando en puerto TCP `3030`).

### Instalación de dependencias
```bash
pip install -r requirements.txt
```

---

## 4. Ejecución del Sistema

### Modo Simulación / Pruebas Offline (Sin Hardware Físico)
Puedes ejecutar todo el controlador en modo simulación utilizando el flag `--mock`:
```bash
python main.py --mock
```

### Modo Producción (Hardware Real)
Asegúrate de configurar las IPs de tus NodeMCU en `config/system.yaml` y ejecuta:
```bash
python main.py
```

O especificando una ruta de configuración personalizada:
```bash
python main.py --config config/mi_instalacion.yaml
```

---

## 5. Ejecución de la Suite de Pruebas Unitarias

El proyecto incluye una suite completa de pruebas unitarias e integración que **no requieren hardware físico** para ejecutarse:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 6. Guía de Extensión: Añadir un Nuevo Dispositivo

Para añadir un nuevo sensor o actuador al sistema:

1. **Crear el Driver**: Hereda de `Sensor` o `Actuator` e implementa los métodos correspondientes en `devices/sensors/` o `devices/actuators/`.
2. **Registrar el Driver**: Añádelo al diccionario `DEVICE_REGISTRY` en `core/registry.py`:
   ```python
   DEVICE_REGISTRY.register("mi_sensor", MiSensorClass)
   ```
3. **Configurar en YAML**: Declara el dispositivo en `config/system.yaml`:
   ```yaml
   devices:
     nuevo_sensor_01:
       type: mi_sensor
       node: weather_01
       pin: D3
       poll_interval: 15
   ```
No es necesario modificar `main.py`, `NodeManager`, `RuleEngine`, ni ninguna otra clase del núcleo.
