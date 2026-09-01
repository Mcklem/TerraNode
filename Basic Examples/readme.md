# NodeMCU + Firmata WiFi — Componentes y conexiones

Este proyecto utiliza un **NodeMCU (ESP8266)** ejecutando **StandardFirmataWiFi** para permitir que un programa Python controle y lea componentes electrónicos a través de la red WiFi.

La arquitectura general es:

```text
┌─────────────────┐       WiFi / Firmata        ┌─────────────────┐
│                 │ ◄─────────────────────────► │                 │
│     Python      │                             │     NodeMCU     │
│                 │      TCP/IP puerto 3030     │    ESP8266      │
└─────────────────┘                             └────────┬────────┘
                                                         │
                         ┌───────────────────────────────┼───────────────────────────────┐
                         │                               │                               │
                      RELÉ                              LDR                            SERVO
                                                                                         │
                                                                                      BMP180
                                                                                       (I²C)
```

Configuración utilizada:

```text
NodeMCU IP:       192.168.1.37
Puerto Firmata:   3030
Firmware:         StandardFirmataWiFi
Comunicación:     WiFi / TCP-IP
Cliente Python:   Pymata4
```

---

# 1. Módulo Relé

El relé permite controlar dispositivos externos desde Python.

## Conexiones

```text
NodeMCU                 Módulo Relé
────────                ────────────

GPIO digital ─────────► IN
GND          ─────────► GND
VIN / 5V*    ─────────► VCC
```

> *La alimentación depende del módulo de relé utilizado. Muchos módulos de relé requieren 5 V.*

Ejemplo de arquitectura:

```text
Python
   │
   │ WiFi / Firmata
   ▼
NodeMCU
   │
   │ GPIO
   ▼
Módulo Relé
   │
   ├──── COM
   │
   ├──── NO
   │
   └──── NC
```

El estado del relé puede ser:

```text
OFF → circuito abierto
ON  → circuito cerrado
```

Aplicaciones posibles:

* Bombas de agua.
* Iluminación.
* Electroválvulas.
* Ventiladores.
* Otros dispositivos mediante relé o contactor.

---

# 2. Sensor de luz LDR

El LDR permite medir cambios relativos en la iluminación.

La resistencia del LDR:

```text
Más luz      → menor resistencia
Menos luz   → mayor resistencia
```

Para medirlo con el NodeMCU se utiliza un divisor de tensión.

## Conexión

```text
                 3.3V
                  │
                 LDR
                  │
                  ├──────────► A0 NodeMCU
                  │
              Resistencia
              (≈10 kΩ)
                  │
                 GND
```

La conexión eléctrica es:

```text
3.3V
 │
 ├── LDR ─────┐
 │            │
 │           A0
 │            │
 │         10 kΩ
 │            │
 └────────── GND
```

Python recibe el valor analógico a través de Firmata.

El valor puede utilizarse para determinar:

```text
Luz intensa
    │
    ▼
Valor analógico alto/bajo*
    │
    ▼
Luz media
    │
    ▼
Oscuridad
```

> El sentido exacto del valor depende de cómo se haya conectado el divisor de tensión.

Aplicaciones:

* Detección de día/noche.
* Control automático de iluminación.
* Registro de exposición solar.
* Activación de sistemas según luminosidad.

---

# 3. Servo

Se ha probado correctamente el control de un servomotor desde Python mediante Firmata.

## Conexiones

```text
Servo                    NodeMCU / Fuente externa
─────                    ───────────────────────

Rojo      ─────────────► +5V alimentación
Marrón/
Negro     ─────────────► GND
Naranja/
Amarillo  ─────────────► GPIO digital
```

Es importante compartir masa:

```text
Fuente externa GND
        │
        ├────────► Servo GND
        │
        └────────► NodeMCU GND
```

Arquitectura:

```text
Python
   │
   │ WiFi / Firmata
   ▼
NodeMCU GPIO
   │
   │ Señal PWM
   ▼
 Servo
   │
   ├── Posición
   │
   ├── Apertura
   │
   └── Cierre
```

El rango de control utilizado es:

```text
0° ───────────────────────── 180°
```

Aplicaciones:

* Apertura y cierre de compuertas.
* Mecanismos de ventilación.
* Válvulas mecánicas.
* Movimiento de sensores.
* Automatización de pequeñas estructuras.

> Para servos de tamaño medio o grande se recomienda una fuente de alimentación independiente. El NodeMCU no debe alimentar directamente un servo que consuma una cantidad significativa de corriente.

---

# 4. BMP180 / GY-68

El BMP180 se comunica mediante el bus I²C.

Se ha probado correctamente la lectura de:

* Temperatura.
* Presión atmosférica.
* Altitud estimada.

## Dirección I²C

```text
0x77
```

El CHIP ID leído correctamente fue:

```text
Registro: 0xD0
Valor:    0x55
```

Lo que confirma la comunicación correcta con un BMP180.

## Conexiones

Para el NodeMCU ESP8266:

```text
BMP180 / GY-68          NodeMCU
──────────────          ───────

VCC          ─────────► 3.3V
GND          ─────────► GND
SDA          ─────────► D2 / GPIO4
SCL          ─────────► D1 / GPIO5
```

Diagrama:

```text
                 NodeMCU
              ┌─────────────┐
              │             │
3.3V ─────────┤ 3.3V     D2 ├──────── SDA
GND  ─────────┤ GND      D1 ├──────── SCL
              │             │
              └─────────────┘
                     │
                     │ I²C
                     ▼
              ┌─────────────┐
              │ BMP180/GY68 │
              └─────────────┘
```

La comunicación se realiza mediante:

```text
Python
   │
   │ TCP/IP WiFi
   ▼
StandardFirmataWiFi
   │
   │ I²C
   ▼
BMP180
```

El sensor proporciona una lectura bruta de temperatura (`UT`) y presión (`UP`).

Estas lecturas se compensan utilizando los coeficientes de calibración internos del sensor:

```text
AC1
AC2
AC3
AC4
AC5
AC6

B1
B2

MB
MC
MD
```

Posteriormente Python calcula:

```text
Temperatura
     │
     ▼
Presión atmosférica
     │
     ▼
Altitud estimada
```

Ejemplo de lectura obtenida durante las pruebas:

```text
UT = 30701

Temperatura = 30.55 °C
```

---

# Arquitectura completa del sistema

```text
                         ┌─────────────────┐
                         │     Python      │
                         │                 │
                         │ Lógica / Control│
                         └────────┬────────┘
                                  │
                           WiFi / TCP-IP
                           Puerto 3030
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    NodeMCU      │
                         │    ESP8266      │
                         │                 │
                         │ StandardFirmata │
                         └────────┬────────┘
                                  │
            ┌─────────────────────┼──────────────────────┐
            │                     │                      │
            ▼                     ▼                      ▼
         GPIO OUT               ANALÓGICO               I²C
            │                     │                      │
            │                     │                      │
          RELÉ                   LDR                  BMP180
            │                                            │
            │                                            ├── Temperatura
            │                                            ├── Presión
            │                                            └── Altitud
            │
            ▼
       Dispositivo
       externo


                    GPIO / PWM
                        │
                        ▼
                      SERVO
```

---

# Componentes probados

| Componente      | Tipo              | Comunicación   | Estado      |
| --------------- | ----------------- | -------------- | ----------- |
| NodeMCU ESP8266 | Controlador       | WiFi / Firmata | Funcionando |
| Relé            | Salida digital    | GPIO           | Funcionando |
| LDR             | Entrada analógica | A0             | Funcionando |
| Servo           | Salida PWM        | GPIO           | Funcionando |
| BMP180 / GY-68  | Sensor ambiental  | I²C            | Funcionando |

---

# Flujo de comunicación

```text
┌─────────────┐
│   PYTHON    │
└──────┬──────┘
       │
       │ WiFi
       │ TCP/IP
       ▼
┌─────────────────────┐
│ StandardFirmataWiFi │
│                     │
│      NodeMCU        │
└──────────┬──────────┘
           │
     ┌─────┼──────┐
     │     │      │
    GPIO   A0    I²C
     │     │      │
     │     │      └──── BMP180
     │     │
     │     └─────────── LDR
     │
     ├───────────────── RELÉ
     │
     └───────────────── SERVO
```

---

# Posibles ampliaciones

El sistema puede ampliarse fácilmente con:

```text
🌱 Humedad del suelo
🌡️ Temperatura ambiental
💧 Nivel de depósito
🚰 Caudalímetro
🌧️ Pluviómetro
💨 Anemómetro
🧭 Dirección del viento
🔋 Monitorización de batería
☀️ Monitorización solar
🚿 Electroválvulas
⚡ Control de bombas
📊 Registro histórico de datos
🧠 Automatización basada en reglas
```

La arquitectura permite utilizar el NodeMCU como nodo físico de entrada/salida mientras Python actúa como sistema central de control y automatización.
