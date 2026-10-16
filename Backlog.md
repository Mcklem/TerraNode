# 🌿 TerraNode — Technical Audit & Engineering Backlog (`Backlog.md`)

> **Fecha de Creación:** 15 de Septiembre de 2026  
> **Versión:** 1.1 (Actualizado: corrección de falso positivo `secrets.h` y parametrización de secretos)  
> **Alcance:** `iot_controller`, `iot_hardware`, `iot_web`, `Basic Examples` y configuraciones.  
> **Propósito:** Documento maestro de auditoría técnica, deuda acumulada y backlog accionable de ingeniería para llevar TerraNode de prototipo a entorno de producción seguro, escalable y tolerante a fallos.

---

## 📌 Índice
1. [Resumen Ejecutivo](#-resumen-ejecutivo)
2. [Checklist de Revisión Técnica Integral](#-checklist-de-revisión-técnica-integral)
   - [1. Arquitectura](#1-arquitectura)
   - [2. Código](#2-código)
   - [3. Datos / Base de Datos](#3-datos--base-de-datos)
   - [4. Rendimiento](#4-rendimiento)
   - [5. Escalabilidad](#5-escalabilidad)
   - [6. API / Comunicación](#6-api--comunicación)
   - [7. Concurrencia](#7-concurrencia)
   - [8. Fiabilidad](#8-fiabilidad)
   - [9. Seguridad](#9-seguridad)
   - [10. Observabilidad](#10-observabilidad)
   - [11. Tests](#11-tests)
   - [12. Configuración y Despliegue](#12-configuración-y-despliegue)
   - [13. Dependencias](#13-dependencias)
   - [14. Mantenibilidad](#14-mantenibilidad)
   - [15. Olores de Código Identificados](#15-olores-de-código-identificados)
   - [16. Fiabilidad Específica IoT (ESP8266 / NodeMCU / Firmata)](#16-fiabilidad-específica-iot-esp8266--nodemcu--firmata)
3. [Matriz de Problemas Clasificada](#-matriz-de-problemas-clasificada)
4. [Backlog de Ingeniería por Fases](#-backlog-de-ingeniería-por-fases)
   - [Fase 1: Seguridad Crítica y Protección Física de Hardware](#fase-1-seguridad-crítica-y-protección-física-de-hardware-inmediata)
   - [Fase 2: Persistencia, Resiliencia y Tolerancia a Fallos](#fase-2-persistencia-resiliencia-y-tolerancia-a-fallos)
   - [Fase 3: Rendimiento, Escalabilidad y Protocolos de Red](#fase-3-rendimiento-escalabilidad-y-protocolos-de-red)
   - [Fase 4: Observabilidad, DevOps y Mantenimiento Continuo](#fase-4-observabilidad-devops-y-mantenimiento-continuo)

---

## 📊 Resumen Ejecutivo

**TerraNode** cuenta con una arquitectura base modular y limpia:
- Desacoplamiento entre eventos mediante `EventBus` asíncrono.
- Separación de responsabilidades entre controladores semánticos (`DeviceManager`), conexión física (`NodeManager`), y validación de hardware (`PinManager`).
- Control tri-estado de precedencia (`AUTO` vs `MANUAL_ON/OFF/VALUE`) mediante `LiveCommandService` y `OverrideRegistry`.
- Suite de pruebas unitarias existente con 55 tests pasando.

Sin embargo, para su paso a producción agrícola o comercial, existen **vulnerabilidades críticas y de seguridad física**:
1. **Riesgo Físico de Relés:** El firmware en ESP8266 configura por defecto `LOW` en pines de salida ante caídas de red o reinicios. Para módulos de relé comunes (Active-Low), esto **enciende electroválvulas y bombas de agua durante apagones de red**, con riesgo de inundación o avería mecánica.
2. **API REST y MCP Expuestas sin Autenticación:** La API FastAPI carece de control de acceso. Cualquier dispositivo en la red WiFi/LAN puede activar o desactivar actuadores y modificar configuraciones.
3. **Parametrización de Secretos en Configuración:** Claves de autenticación de nodos fijadas en texto plano dentro de `system.yaml` en lugar de interpolar variables de entorno (`secrets.h` está correctamente protegido por `.gitignore`).
4. **Pérdida de Estado en Memoria:** Los modos de override manual y temporizadores de riego se almacenan en RAM y se borran al reiniciar el controlador.
5. **Crecimiento Ilimitado de Base de Datos:** La base de datos SQLite carece de tareas de purga activas, acumulando millones de registros que degradan tarjetas microSD en Raspberry Pi.

---

## 🔍 Checklist de Revisión Técnica Integral

### 1. Arquitectura
- [x] **Separación clara de responsabilidades:** Directorios modulares (`api`, `automation`, `core`, `devices`, `nodes`, `services`, `storage`).
- [ ] **Desacoplamiento e inyección de dependencias:** 
  - `ControllerSystem` inicializa componentes de forma monolítica.
  - `system_container` en [api/dependencies.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/api/dependencies.py) es un contenedor global mutable (*Service Locator* antipatrón).
- [ ] **Capas bien definidas (API → Servicio → Dominio → Infraestructura):**
  - Los endpoints de historial en [api/routes/history.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/api/routes/history.py) ejecutan consultas directas a modelos ORM saltándose la capa de persistencia.
  - El endpoint `POST /api/v1/nodes/{node_id}/pin` en [api/routes/nodes.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/api/routes/nodes.py) rompe el dominio permitiendo escrituras directas sobre pines físicos.
- [ ] **Código duplicado / Violaciones DRY:**
  - Código idéntico de paginación (`count` + `filter` + `offset` + `limit`) repetido en 5 endpoints de historial.
  - `SecureStandardFirmataWiFi.ino` es un fork con copy-paste íntegro de `StandardFirmataWiFi.ino` (más de 500 líneas duplicadas) en lugar de una librería modular.
- [ ] **Facilidad para sustituir componentes:**
  - Fácil reemplazo de nodos físicos gracias a `BaseNode` (`FirmataNode`, `SecureFirmataNode`, `MockNode`).
  - Acoplamiento a SQLite mediante comandos `PRAGMA` específicos en [storage/database.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/storage/database.py#L137), complicando la migración a PostgreSQL sin refactorización.

### 2. Código
- [ ] **Complejidad y clases sobredimensionadas:**
  - Monolito de firmware `SecureStandardFirmataWiFi.ino` (568 líneas) aunando WiFi, Sysex, Watchdog, I2C, Servos y GPIO.
  - `FirmataNode` ([nodes/firmata_node.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/nodes/firmata_node.py)) con 358 líneas incluyendo hilos, monkey patching e ioctl a bajo nivel.
- [ ] **Nombres, tipado y convenciones:**
  - Inconsistencia de idioma (código y logs en inglés; descripciones Swagger en español).
  - Tipado degradado a `Any` en [core/system.py:L41-L47](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/core/system.py#L41-L47).
  - Uso de `PinManager` en type hints sin importación explícita en [api/dependencies.py:L15](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/api/dependencies.py#L15).
- [ ] **Código muerto y TODOs:**
  - `purge_old_data` en [storage/repositories.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/storage/repositories.py#L252) nunca es llamada.
  - Suscripción al tópico `override.expired` en [storage/repositories.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/storage/repositories.py#L45) que nadie emite.
- [ ] **Manejo incorrecto de excepciones:**
  - Múltiples bloques `except Exception: pass` que ocultan errores en apagado, heartbeat y registro de señales ([main.py:L58](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/main.py#L58), [relay.py:L30](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/devices/actuators/relay.py#L30)).
  - Eventos de auditoría descartados silenciosamente con `except asyncio.QueueFull: pass` ([repositories.py:L116](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/storage/repositories.py#L116)).
- [ ] **Valores hardcodeados:**
  - Claves de autenticación de nodos fijadas en texto plano en `system.yaml` (requiere soporte de interpolación de variables de entorno en `ConfigLoader`).
  - Timeout de 6000ms fijo en el proxy de Next.js ([route.ts:L46](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_web/app/api/terranode/%5B...path%5D/route.ts#L46)).

### 3. Datos / Base de Datos
- [x] **Índices adecuados:** Índices compuestos presentes en `(device_id, timestamp)` y `(node_id, timestamp)`.
- [ ] **Consultas y transacciones:**
  - `Database.run_in_session` hace `session.commit()` incluso en consultas de lectura `SELECT` ([storage/database.py:L159](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/storage/database.py#L159)), penalizando el archivo WAL.
  - Doble consulta `COUNT(*)` + `SELECT` en cada llamada a paginación de historial.
- [ ] **Crecimiento de tablas y archivado:**
  - Ingesta continua en SQLite sin política activa de retención ni checkpointing automatizado. Con 10 sensores muestreando cada 5s se generan ~172.800 filas diarias.

### 4. Rendimiento
- [ ] **Cuellos de botella de CPU y Red:**
  - Recepción socket byte a byte mediante `sock.recv(1)` en `FirmataNode._safe_tcp_receiver` ([nodes/firmata_node.py:L32](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/nodes/firmata_node.py#L32)).
  - Bucle busy-wait con `time.sleep` en el reporter de `pymata4`.
- [ ] **I/O innecesario:**
  - Polling agresivo del Frontend: el hook `useTerraNode` ([iot_web/hooks/use-terranode.ts:L25](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_web/hooks/use-terranode.ts#L25)) emite **6 peticiones HTTP cada 2 segundos**.
- [ ] **Publicación bloqueante en EventBus:**
  - `EventBus.publish` espera con `await asyncio.gather` que todos los suscriptores terminen antes de retornar el control ([core/event_bus.py:L59](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/core/event_bus.py#L59)).

### 5. Escalabilidad
- [ ] **Límites de concurrencia y conexiones:**
  - Cada nodo Firmata crea 2 hilos nativos en Python. A partir de 50–100 nodos, la contención del GIL y los cambios de contexto colapsan el host.
  - Escala a 1.000 o 100.000 nodos inviable con sockets TCP directos; requiere arquitectura MQTT.
- [ ] **Estado en memoria que impide escalado horizontal:**
  - Overrides manuales en `OverrideRegistry` y temporizadores activos en `TimeScheduler` residen en la RAM. Imposible balancear entre múltiples contenedores.
- [ ] **Single Point of Failure (SPOF):**
  - Si el controlador central cae, los nodos físicos quedan ciegos y no ejecutan lógica local de salvaguarda.

### 6. API / Comunicación
- [x] **Contratos y versionado:** Endpoints bajo prefijo `/api/v1/` con modelos Pydantic v2 y OpenAPI/Swagger (`/docs`).
- [ ] **Idempotencia:** Disparos de cronogramas (`/trigger`) sin cabecera de idempotencia; múltiples clics generan múltiples tareas de duración concurrentes.
- [ ] **Rate Limiting:** Inexistente. Vulnerable a saturación por ráfagas.
- [ ] **Timeouts y Circuit Breakers:** Sin circuit breaker ante caídas de nodos en la API.

### 7. Concurrencia
- [ ] **Condición de carrera en `TimeScheduler`:** Si se dispara una programación manual con duración mientras otra está activa, se sobrescribe en el diccionario `_active_duration_tasks` sin cancelar la anterior, provocando apagado prematuro ([automation/time_scheduler.py:L240](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/automation/time_scheduler.py#L240)).
- [ ] **Carrera en TLS de `SecureFirmataNode`:** El socket se envuelve con SSL tras haber arrancado los hilos lectores en `pymata4`, causando colisiones de descriptores.

### 8. Fiabilidad
- [ ] **Recuperación tras reinicio:** Reinicios provocan la pérdida total de programaciones en curso y anulaciones manuales de emergencia.
- [ ] **Reconexión destructiva:** `HealthMonitor` apaga relés arbitrariamente al reconectar un nodo reconectado ([monitoring/health.py:L104](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/monitoring/health.py#L104)).
- [ ] **Falta de Circuit Breakers:** Errores I2C continuos bloquean el sensor indefinidamente sin aislar el fallo.

### 9. Seguridad
- [ ] **Autenticación/Autorización:** Cero autenticación en endpoints REST y MCP.
- [ ] **Secretos y Configuración:** Claves maestras de nodos fijadas en [system.yaml](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/config/system.yaml) en lugar de inyectarse vía variables de entorno. `secrets.h` se encuentra debidamente protegido por `.gitignore`.
- [ ] **TLS vulnerado:** `ssl.CERT_NONE` y `check_hostname=False` deshabilitan la validación criptográfica en [secure_firmata_node.py:L61](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/nodes/secure_firmata_node.py#L61).

### 10. Observabilidad
- [x] **Logs contextuales:** Loggers con etiquetas `[node:x device:y]`.
- [ ] **Logs estructurados:** Salida en texto plano, sin opción JSON para ELK/Loki.
- [ ] **Métricas:** Sin endpoint `/metrics` en formato Prometheus.
- [ ] **Trazabilidad:** Sin middleware de `X-Correlation-ID` para rastrear peticiones extremo a extremo.

### 11. Tests
- [x] **Cobertura básica:** 55 pruebas unitarias rápidas.
- [ ] **Pruebas de red realistas:** Cero tests con simulación de latencia, pérdida de paquetes o caídas abruptas de socket.
- [ ] **Pruebas de carga:** Cero pruebas de estrés concurrente sobre el despachador y SQLite.

### 12. Configuración y Despliegue
- [x] **Configuración externa:** `system.yaml` y `.env` gestionados con `Settings`.
- [ ] **Control de migraciones:** Ausencia de Alembic; uso frágil de `Base.metadata.create_all()`.
- [ ] **Contenerización y CI/CD:** Sin `Dockerfile`, sin `docker-compose.yml`, sin GitHub Actions.
- [ ] **Versiones de dependencias:** Dependencias no fijadas en `requirements.txt`.

### 13. Dependencias
- [ ] **Librería obsoleta:** `pymata4` requiere parches en caliente y utiliza hilos bloqueantes antiguos.
- [ ] **Fijación de versiones:** Falta de `requirements.lock` o `poetry.lock`.

### 14. Mantenibilidad
- [x] **Documentación base:** `README.md` y `professional_roadmap.md` claros y detallados.
- [ ] **Deuda técnica:** Acumulada en monkey patches, código C++ no modular y falta de persistencia de estado transaccional.

### 15. Olores de Código Identificados
```text
[ God Class / Monolith ]
 └── iot_hardware/SecureStandardFirmataWiFi/SecureStandardFirmataWiFi.ino (568 líneas sin modularizar)

[ Global Monkey-Patching ]
 └── iot_controller/nodes/firmata_node.py:L23,L43,L62 (Sobrescritura global de pymata4)

[ Silent Exception Swallowing ]
 ├── iot_controller/main.py:L58-59
 ├── iot_controller/nodes/firmata_node.py:L167-168
 ├── iot_controller/devices/actuators/relay.py:L30-31
 └── iot_controller/storage/repositories.py:L116-117

[ Unbounded In-Memory State ]
 ├── iot_controller/services/live_command/override_registry.py:L11
 └── iot_controller/automation/time_scheduler.py:L74

[ Infinite Reconnect Loop ]
 └── iot_controller/monitoring/health.py:L88-93 (Sin backoff exponencial ni límite de reintentos)

[ Aggressive Frontend Polling ]
 └── iot_web/hooks/use-terranode.ts:L25 (6 peticiones paralelas cada 2s)
```

### 16. Fiabilidad Específica IoT (ESP8266 / NodeMCU / Firmata)
- [ ] **Peligro Físico por Relés Active-Low:** [SecureStandardFirmataWiFi.ino:L467](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_hardware/SecureStandardFirmataWiFi/SecureStandardFirmataWiFi.ino#L467) pone los pines digitales a `LOW` al reiniciar o perder señal WiFi, activando bombas o válvulas inadvertidamente.
- [ ] **Glitch de Arranque en Relés:** [relay.py:L18-19](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/devices/actuators/relay.py#L18-L19) configura el pin como digital output antes de enviar el valor de apagado, generando un clic eléctrico transitorio.
- [ ] **Apagado Involuntario en Reconexión:** Al restablecerse la red WiFi, [health.py:L104](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/monitoring/health.py#L104) apaga todos los relés sin comprobar si el usuario los había dejado encendidos.
- [ ] **Bloqueo de Socket en ESP8266:** Si el servidor se apaga abruptamente sin `TCP FIN`, el microcontrolador queda bloqueado en `WiFiServerStream` hasta el timeout del watchdog.
- [ ] **Excepción por Lectura `None` al Iniciar:** Sensores analógicos fallan con `TypeError` si se leen antes de recibir el primer reporte analógico ([soil_moisture.py:L41](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/devices/sensors/soil_moisture.py#L41)).

---

## 📋 Matriz de Problemas Clasificada

| ID | Prioridad | Problema | Impacto | Causa Raíz | Evidencia | Solución Propuesta | Esfuerzo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | 🔴 Critical | **API REST y MCP sin Autenticación** | Cualquier intruso en la LAN puede accionar maquinaria física de alta potencia. | Falta de middlewares o esquemas de seguridad en FastAPI. | [api/app.py:L96](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/api/app.py#L96) | Implementar autenticación por API Key / Bearer Token en FastAPI y Next.js. | 1 día |
| **IOT-01** | 🔴 Critical | **Relé Active-Low se enciende al fallar red** | Peligro de inundación o incendio al desconectarse el WiFi, ya que el pin pasa a LOW. | En el firmware C++, el reset del watchdog fija todos los pines a `OUTPUT` (`LOW`). | [SecureStandardFirmataWiFi.ino:L467](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_hardware/SecureStandardFirmataWiFi/SecureStandardFirmataWiFi.ino#L467) | Modificar firmware para que el estado seguro de pines de salida sea `HIGH` por defecto. | 4 horas |
| **REL-01** | 🔴 Critical | **Pérdida de Overrides y Timers al Reiniciar** | Tras un corte eléctrico, bombas apagadas por mantenimiento se vuelven a encender. | Estados de override y temporizadores residen solo en memoria RAM. | [override_registry.py:L11](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/services/live_command/override_registry.py#L11), [time_scheduler.py:L74](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/automation/time_scheduler.py#L74) | Persistir estados en SQLite (`active_overrides`, `active_schedules`) y restaurarlos al iniciar. | 1 día |
| **IOT-02** | 🔴 High | **Reconexión apaga relés arbitrariamente** | Parpadeos de red apagan actuadores que estaban trabajando en ciclos largos. | `HealthMonitor` invoca `dev.start()`, que ejecuta `await self.turn_off()`. | [health.py:L104](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/monitoring/health.py#L104), [relay.py:L19](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/devices/actuators/relay.py#L19) | Comprobar último estado conocido y `OverrideRegistry` antes de reiniciar el actuador. | 3 horas |
| **CON-01** | 🔴 High | **Carrera en Duraciones de Schedules** | Apagado prematuro de bombas si se solapan dos programaciones sobre el mismo dispositivo. | Se sobrescribe la referencia en `_active_duration_tasks` sin llamar a `.cancel()`. | [time_scheduler.py:L240](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/automation/time_scheduler.py#L240) | Cancelar explícitamente cualquier tarea previa activa para ese schedule antes de iniciar la nueva. | 1 hora |
| **SEC-03** | 🔴 High | **Bypass de Certificados TLS (`CERT_NONE`)** | Falsa seguridad: socket vulnerable a espionaje y suplantación en red local. | Uso de `ssl.CERT_NONE` y `check_hostname=False`. | [secure_firmata_node.py:L60](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/nodes/secure_firmata_node.py#L60) | Implementar mTLS con certificados válidos o eliminar la falsa opción TLS. | 1 día |
| **SEC-02** | 🟠 Medium | **Claves de Nodos en Configuración (`system.yaml`)** | Riesgo de filtrar tokens de nodos si se comparte o publica el archivo `system.yaml`. | Falta de interpolación de variables de entorno en `ConfigLoader`. `secrets.h` está en `.gitignore`. | [system.yaml:L104,L123](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/config/system.yaml#L104) | Modificar `ConfigLoader` para resolver `${VAR}` y extraer claves a `.env`. | 3 horas |
| **DAT-01** | 🟠 Medium | **Crecimiento Ilimitado de Base de Datos** | La base de datos SQLite crecerá hasta saturar la tarjeta SD de la Raspberry Pi. | El método `purge_old_data` no tiene ninguna tarea programada asociada. | [repositories.py:L252](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/storage/repositories.py#L252) | Programar tarea periódica diaria que purgue datos > 30 días y ejecute `PRAGMA wal_checkpoint`. | 2 horas |
| **DAT-02** | 🟠 Medium | **Commit Innecesario en Lecturas SELECT** | Sobrecarga de I/O en SQLite y bloqueos transaccionales en consultas GET históricas. | `run_in_session` ejecuta `commit()` siempre al salir del bloque `with`. | [database.py:L159](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/storage/database.py#L159) | Separar en sesiones de solo lectura (`read_session`) y sesiones de escritura (`write_session`). | 2 horas |
| **PERF-01**| 🟠 Medium | **Polling Masivo desde Frontend Next.js** | Saturación del event loop de FastAPI con 6 peticiones HTTP concurrentes cada 2s. | Hook `useTerraNode` consulta 6 endpoints en paralelo periódicamente. | [use-terranode.ts:L25](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_web/hooks/use-terranode.ts#L25) | Implementar Server-Sent Events (SSE) o WebSocket `/ws` para emitir eventos reactivos. | 2 días |
| **PERF-02**| 🟠 Medium | **Syscall Overhead por `recv(1)`** | Alto consumo de CPU en el proceso Python al recibir tramas byte a byte por socket. | `_safe_tcp_receiver` lee 1 byte por llamada al sistema. | [firmata_node.py:L32](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/nodes/firmata_node.py#L32) | Leer búferes de 64/128 bytes e iterar en memoria. | 3 horas |
| **IOT-03** | 🟡 Low | **Crash por lectura `None` en Sensores ADC** | Excepción `TypeError` en sensores de humedad y LDR al iniciar antes del primer paquete. | Falta validación `if raw_val is None: return self.get_state()`. | [soil_moisture.py:L41](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/devices/sensors/soil_moisture.py#L41) | Añadir guardia para retornar el estado anterior si el valor analógico aún no llegó. | 30 min |
| **OPS-01** | 🟡 Low | **Sin Control de Versiones de Esquema** | Dificultad para aplicar cambios en bases de datos en producción sin romper datos existentes. | Uso exclusivo de `Base.metadata.create_all()`. | [database.py:L133](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/storage/database.py#L133) | Integrar **Alembic** (`alembic init`) y gestionar migraciones formales. | 4 horas |
| **OBS-01** | 🔵 Improvement | **Sin Métricas Prometheus ni Request IDs** | Dificultad para diagnosticar caídas o integrar con Grafana. | Falta de middlewares de observabilidad en FastAPI. | [api/app.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/api/app.py) | Integrar `prometheus-fastapi-instrumentator` y middleware de correlación. | 3 horas |
| **DEV-01** | 🔵 Improvement | **Falta de Docker y Versiones no Fijadas** | Diferencias de comportamiento entre máquinas de desarrollo y campo. | Sin `Dockerfile`, dependencias con `>=`. | [requirements.txt](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/requirements.txt) | Crear `Dockerfile` y fijar versiones exactas (`requirements.lock`). | 2 horas |

---

## 🚀 Backlog de Ingeniería por Fases

### Fase 1: Seguridad Crítica y Protección Física de Hardware (INMEDIATA)
*Objetivo: Evitar daños materiales en la instalación física y cerrar vectores de ataque directos.*

- [ ] **[SEC-01] Protección de API REST y MCP con Autenticación**
  - [ ] Implementar middleware de API Key en FastAPI con cabecera `X-API-Key` o `Authorization: Bearer`.
  - [ ] Configurar `API_SECRET_KEY` en `.env` y validación centralizada.
  - [ ] Actualizar proxy de Next.js ([iot_web/app/api/terranode/[...path]/route.ts](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_web/app/api/terranode/%5B...path%5D/route.ts)) para inyectar la clave en peticiones salientes.
  - [ ] Permitir endpoints públicos mínimos (`/api/v1/health` en modo ping básico).

- [ ] **[IOT-01] Corrección de Estado Seguro en Relés Active-Low**
  - [ ] Modificar `SecureStandardFirmataWiFi.ino`: en `systemResetCallback()`, configurar los pines de salida en estado `HIGH` para evitar que los relés active-low se cierren al perder señal WiFi o reiniciar.
  - [ ] En [devices/actuators/relay.py:L18](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/devices/actuators/relay.py#L18), escribir el valor de reposo (`HIGH` en active-low) inmediatamente al inicializar para eliminar el pulso o glitch transitorio.

- [ ] **[IOT-02] Protección de Estado Físico en Reconexiones**
  - [ ] Modificar `HealthMonitor._attempt_node_reconnect` en [monitoring/health.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/monitoring/health.py): tras reconectar el nodo, no invocar `dev.start()` a ciegas (que apaga los relés).
  - [ ] Consultar el estado deseado en `OverrideRegistry` y restaurar el estado que tenía el actuador antes de la desconexión.

---

### Fase 2: Persistencia, Resiliencia y Tolerancia a Fallos
*Objetivo: Garantizar que el sistema sobreviva a reinicios sin descontrol de riego ni pérdida de auditoría.*

- [ ] **[SEC-02] Soporte de Variables de Entorno en `system.yaml` (Interpolación de Secretos)**
  - [ ] Extender `ConfigLoader` ([core/config.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/core/config.py)) con un resolver regex que soporte sintaxis `${VAR_NAME:-default}`.
  - [ ] Mover `auth_key` y credenciales sensibles a variables de entorno en `.env` y documentar en `.env.example`.

- [ ] **[REL-01] Persistencia de Overrides y Tareas de Calendario**
  - [ ] Crear tabla `system_state` en SQLAlchemy para almacenar el modo de control (`AUTO`, `MANUAL_ON`, etc.), fuente y expiración TTL de cada dispositivo.
  - [ ] Modificar `OverrideRegistry` para leer/guardar cambios en base de datos.
  - [ ] Crear tabla `active_schedules` para persistir temporizadores de duración en curso; si el host se reinicia durante un riego de 15 minutos, recalcular el tiempo restante y reanudar el timer o apagar de forma segura.

- [ ] **[CON-01] Cancelación Limpia de Temporizadores en `TimeScheduler`**
  - [ ] En [automation/time_scheduler.py:L240](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/automation/time_scheduler.py#L240), antes de lanzar un nuevo timer para `sched_id`, verificar si existe en `self._active_duration_tasks` y llamar a `task.cancel()`.
  - [ ] Manejar la excepción `asyncio.CancelledError` dentro del callback para evitar ejecución desfasada del `stop_command`.

- [ ] **[DAT-01] Purga Automatizada de Historial y Mantenimiento SQLite**
  - [ ] Añadir tarea periódica diaria en `Scheduler` que invoque `StorageManager.purge_old_data(retention_days=30)`.
  - [ ] Ejecutar `PRAGMA wal_checkpoint(TRUNCATE)` y `VACUUM` mensual para liberar espacio en disco.

- [ ] **[IOT-03] Guardia contra Lecturas `NoneType` en Sensores**
  - [ ] En [devices/sensors/soil_moisture.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/devices/sensors/soil_moisture.py) y [devices/sensors/ldr.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/devices/sensors/ldr.py), comprobar si `raw_val is None` antes de cálculos aritméticos y registrar estado transitorio sin arrojar excepción.

---

### Fase 3: Rendimiento, Escalabilidad y Protocolos de Red
*Objetivo: Eliminar cuellos de botella de CPU y red, permitiendo escalar el número de dispositivos.*

- [ ] **[PERF-01] Migración del Frontend a Server-Sent Events (SSE) / WebSocket**
  - [ ] Crear endpoint `/api/v1/events/stream` (SSE) en FastAPI que transmita eventos del `EventBus` (`device.value_changed`, `node.status_changed`, `command.executed`).
  - [ ] Actualizar el hook `useTerraNode` en Next.js para suscribirse al flujo reactivo, eliminando el polling HTTP cada 2 segundos.

- [ ] **[PERF-02] Optimización de Búfer en Receptores TCP de Firmata**
  - [ ] Modificar `_safe_tcp_receiver` en [nodes/firmata_node.py](file:///c:/Users/Player%201/Desktop/Python%20Files/TerraNode/iot_controller/nodes/firmata_node.py) para utilizar `sock.recv(64)` o `sock.recv(128)` e ingresar los bytes en lote en `the_deque`, reduciendo el 95% de las llamadas al sistema.

- [ ] **[DAT-02] Optimización de Sesiones de Base de Datos**
  - [ ] Dividir el helper `Database.run_in_session` en dos variantes: `run_read_session` (solo lectura, sin commit) y `run_write_session` (transaccional).

- [ ] **[SEC-03] Decisión de Arquitectura en TLS de Nodos**
  - [ ] Si los microcontroladores ESP8266 no soportan servidor TLS por limitaciones de RAM/CPU, retirar la opción ficticia con `CERT_NONE` y basar la seguridad en una VLAN/subred aislada junto a la autenticación Sysex por token.
  - [ ] Si se migra a ESP32 o Raspberry Pi Pico W, implementar TLS mutuo (mTLS) con validación estricta de certificados.

---

### Fase 4: Observabilidad, DevOps y Mantenimiento Continuo
*Objetivo: Facilitar despliegues reproducibles, monitorización remota y trazabilidad.*

- [ ] **[OPS-01] Gestión de Migraciones con Alembic**
  - [ ] Inicializar Alembic en `iot_controller/alembic`.
  - [ ] Generar migración inicial correspondiente al esquema actual.
  - [ ] Integrar ejecución de migraciones automáticas al inicio del sistema.

- [ ] **[OBS-01] Instrumentación de Métricas y Trazabilidad**
  - [ ] Integrar `prometheus-fastapi-instrumentator` exponiendo `/metrics` para Prometheus y Grafana.
  - [ ] Añadir middleware para inyectar `X-Correlation-ID` en peticiones HTTP y propagarlo a los eventos del `EventBus`.

- [ ] **[DEV-01] Contenerización con Docker y Docker Compose**
  - [ ] Crear `Dockerfile` optimizado multi-stage para `iot_controller`.
  - [ ] Crear `Dockerfile` para `iot_web` (Next.js).
  - [ ] Crear `docker-compose.yml` que orqueste backend, frontend y base de datos con persistencia en volúmenes.
  - [ ] Fijar dependencias en `requirements.txt` con versiones exactas.

- [ ] **[TEST-01] Suite de Pruebas de Resiliencia**
  - [ ] Añadir pruebas de integración con simulación de sockets desconectados abruptamente.
  - [ ] Implementar prueba de concurrencia simulando ráfagas de comandos sobre actuadores.

---
*Documento mantenido activamente en el repositorio TerraNode.*
