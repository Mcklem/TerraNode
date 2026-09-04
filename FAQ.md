¿Que ocurre si una regla y un scheduler entran en colision?


    En TerraNode, tanto el motor de reglas de sensores (RuleEngine) como el programador de horarios (TimeScheduler) canalizan todas sus órdenes a través de un único mediador central: el 
    CommandDispatcher
    .

    A continuación se detalla cómo el sistema resuelve los diferentes escenarios de colisión y prevalencia:

    1. 🏆 Jerarquía General de Prioridad y Prevalencia
    text


    ┌────────────────────────────────────────────────────────────────────────┐
    │ NIVEL 1: OVERRIDE MANUAL DE OPERADOR (LIVE_MANUAL)                     │
    │ Bloquea y anula de forma absoluta a Reglas y Schedulers.               │
    └───────────────────────────────────┬────────────────────────────────────┘
                                        │ (Solo si el dispositivo está en modo AUTO)
    ┌───────────────────────────────────▼────────────────────────────────────┐
    │ NIVEL 2: MOTOR DE AUTOMATIZACIÓN EN MODO AUTO                          │
    │ Procesa de forma secuencial y asíncrona:                               │
    │   • RuleEngine    (Event-driven por lecturas de sensores)             │
    │   • TimeScheduler (Time-driven por calendario/intervalos)              │
    └────────────────────────────────────────────────────────────────────────┘
    2. ⚡ Escenarios de Colisión y Comportamiento del Sistema
    Escenario A: Coincidencia en la misma acción (ej. Regla y Scheduler envían turn_on a la vez)
    Comportamiento: Idempotencia.
    El primer comando en llegar a través del bucle de eventos asíncrono (asyncio) enciende el relé/actuador. El segundo comando invoca turn_on milisegundos después; al estar ya en estado ON, el actuador revalida el estado sin provocar parpadeos o conflictos físicos.
    Escenario B: Contradicción en el mismo instante (ej. Regla envía turn_off pero el Scheduler envía turn_on)
    Comportamiento: Prevalencia Temporal Estricta (Último comando procesado).
    El CommandDispatcher procesa las solicitudes secuencialmente. El comando que sea despachado en el último milisegundo determinará el estado físico final del actuador.
    Auditoría: Ambos intentos quedan registrados con su timestamp exacto en la tabla actuator_history y en schedule_history, permitiendo consultar en la API /api/v1/history exactamente qué componente actuó y en qué orden.
    Escenario C: Interrupción durante una Duración Activa (duration)
    Ejemplo: El TimeScheduler enciende la bomba a las 08:00 por 15 minutos (duration: 900). A las 08:05, la humedad del suelo sube demasiado y una regla de protección emite turn_off.
    Comportamiento:
    A las 08:05, la regla apaga la bomba para proteger el cultivo.
    A las 08:15 (al vencer los 15 minutos de duración del scheduler), se ejecuta el stop_command: turn_off programado. Como la bomba ya estaba en OFF, la orden se completa de forma segura.
    Escenario D: Conflicto con un Override Manual de Usuario (MANUAL_ON / MANUAL_OFF)
    Comportamiento: Bloqueo Absoluto.
    Si un operador fijó el actuador en modo manual desde la API REST o la interfaz web, el CommandDispatcher bloquea y rechaza de inmediato tanto a las reglas automáticas como al scheduler, emitiendo un evento command.blocked y registrando el intento en la bitácora.

