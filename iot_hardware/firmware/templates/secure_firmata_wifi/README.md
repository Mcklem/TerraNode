# Secure StandardFirmata WiFi Template

Plantilla oficial de firmware para nodos TerraNode basada en ESP8266 (NodeMCU v2 / ESP-12E).

## Características
- **Autenticación Sysex (0x7E):** Requiere que el controlador TerraNode envíe un token secreto antes de admitir cualquier operación sobre pines o buses.
- **Watchdog Fail-Safe:** Si transcurren más de `WATCHDOG_TIMEOUT_MS` sin tráfico con el controlador, revoca la autenticación y ejecuta un reset seguro de pines para proteger actuadores y relés.
- **Soporte I2C y Servos:** Habilita el control transparente de periféricos mediante Firmata 2.5.
