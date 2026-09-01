from pymata4 import pymata4
import time
import threading
import math

NODEMCU_IP = "192.168.1.37"
FIRMATA_PORT = 3030

BMP180 = 0x77

CONTROL = 0xF4
DATA = 0xF6
CALIBRATION = 0xAA

# OSS = 0 -> máxima velocidad
OSS = 0

calibration = None
temperature_raw = None
pressure_raw = None

calibration_event = threading.Event()
temperature_event = threading.Event()
pressure_event = threading.Event()


# =========================================================
# UTILIDADES
# =========================================================

def signed16(msb, lsb):
    value = (msb << 8) | lsb

    if value & 0x8000:
        value -= 65536

    return value


def unsigned16(msb, lsb):
    return (msb << 8) | lsb


# =========================================================
# CALLBACK I2C
# =========================================================

def i2c_callback(data):

    global calibration
    global temperature_raw
    global pressure_raw

    if len(data) < 4:
        print("I2C: respuesta demasiado corta:", data)
        return

    register = data[2]

    # -----------------------------------------------------
    # CALIBRACIÓN
    # -----------------------------------------------------

    if register == CALIBRATION:

        raw = data[3:-1]

        if len(raw) != 22:
            print(
                f"ERROR calibración: "
                f"esperados 22 bytes, recibidos {len(raw)}"
            )
            return

        AC1 = signed16(raw[0], raw[1])
        AC2 = signed16(raw[2], raw[3])
        AC3 = signed16(raw[4], raw[5])

        AC4 = unsigned16(raw[6], raw[7])
        AC5 = unsigned16(raw[8], raw[9])
        AC6 = unsigned16(raw[10], raw[11])

        B1 = signed16(raw[12], raw[13])
        B2 = signed16(raw[14], raw[15])

        MB = signed16(raw[16], raw[17])
        MC = signed16(raw[18], raw[19])
        MD = signed16(raw[20], raw[21])

        calibration = {
            "AC1": AC1,
            "AC2": AC2,
            "AC3": AC3,
            "AC4": AC4,
            "AC5": AC5,
            "AC6": AC6,
            "B1": B1,
            "B2": B2,
            "MB": MB,
            "MC": MC,
            "MD": MD
        }

        calibration_event.set()


    # -----------------------------------------------------
    # RESULTADO TEMPERATURA
    # -----------------------------------------------------

    elif register == DATA:

        raw = data[3:-1]

        if len(raw) == 2:

            msb = raw[0]
            lsb = raw[1]

            temperature_raw = (msb << 8) | lsb

            temperature_event.set()


        elif len(raw) == 3:

            msb = raw[0]
            lsb = raw[1]
            xlsb = raw[2]

            pressure_raw = (
                ((msb << 16) |
                 (lsb << 8) |
                 xlsb)
                >> (8 - OSS)
            )

            pressure_event.set()


# =========================================================
# LECTURA TEMPERATURA
# =========================================================

def read_temperature(board):

    global temperature_raw

    temperature_event.clear()
    temperature_raw = None

    # Iniciar conversión temperatura
    board.i2c_write(
        BMP180,
        [CONTROL, 0x2E]
    )

    time.sleep(0.01)

    board.i2c_read(
        BMP180,
        DATA,
        2,
        callback=i2c_callback
    )

    if not temperature_event.wait(1):
        raise RuntimeError(
            "Timeout leyendo temperatura"
        )

    return temperature_raw


# =========================================================
# LECTURA PRESIÓN
# =========================================================

def read_pressure(board):

    global pressure_raw

    pressure_event.clear()
    pressure_raw = None

    # Comando presión:
    #
    # 0x34 + (OSS << 6)

    command = 0x34 + (OSS << 6)

    board.i2c_write(
        BMP180,
        [CONTROL, command]
    )

    # Tiempo de conversión según OSS
    if OSS == 0:
        time.sleep(0.005)

    elif OSS == 1:
        time.sleep(0.008)

    elif OSS == 2:
        time.sleep(0.014)

    else:
        time.sleep(0.026)

    board.i2c_read(
        BMP180,
        DATA,
        3,
        callback=i2c_callback
    )

    if not pressure_event.wait(1):
        raise RuntimeError(
            "Timeout leyendo presión"
        )

    return pressure_raw


# =========================================================
# CALCULAR TEMPERATURA
# =========================================================

def calculate_temperature(UT):

    AC5 = calibration["AC5"]
    AC6 = calibration["AC6"]
    MC = calibration["MC"]
    MD = calibration["MD"]

    X1 = ((UT - AC6) * AC5) / (2 ** 15)

    X2 = (MC * (2 ** 11)) / (X1 + MD)

    B5 = X1 + X2

    temperature = (B5 + 8) / 160.0

    return temperature, B5


# =========================================================
# CALCULAR PRESIÓN
# =========================================================

def calculate_pressure(UP, B5):

    AC1 = calibration["AC1"]
    AC2 = calibration["AC2"]
    AC3 = calibration["AC3"]

    AC4 = calibration["AC4"]

    B1 = calibration["B1"]
    B2 = calibration["B2"]

    X1 = (B5 - 4000) * (B2 / (2 ** 11))

    X2 = (AC2 * (B5 - 4000)) / (2 ** 11)

    X3 = X1 + X2

    B3 = (
        (((AC1 * 4 + X3) * (2 ** OSS)) + 2)
        / 4
    )

    X1 = AC3 * B5 / (2 ** 13)

    X2 = (B1 * (B5 * B5 / (2 ** 12))) / (2 ** 16)

    X3 = ((X1 + X2) + 2) / 4

    B4 = AC4 * (X3 + 32768) / (2 ** 15)

    B7 = (UP - B3) * (50000 / (2 ** OSS))

    if B7 < 0x80000000:

        pressure = (B7 * 2) / B4

    else:

        pressure = (B7 / B4) * 2

    X1 = (pressure / (2 ** 8)) ** 2

    X1 = (X1 * 3038) / (2 ** 16)

    X2 = (-7357 * pressure) / (2 ** 16)

    pressure = pressure + ((X1 + X2 + 3791) / (2 ** 4))

    return pressure


# =========================================================
# ALTITUD
# =========================================================

def calculate_altitude(pressure, sea_level_pressure=101325):

    return 44330 * (
        1 - (pressure / sea_level_pressure) ** 0.19029495
    )


# =========================================================
# MAIN
# =========================================================

board = None

try:

    print("=" * 60)
    print("          BMP180 / GY-68 TELEMETRÍA")
    print("=" * 60)

    print("\nConectando...")

    board = pymata4.Pymata4(
        ip_address=NODEMCU_IP,
        ip_port=FIRMATA_PORT
    )

    print("✓ Firmata conectado")

    board.set_pin_mode_i2c()

    print("✓ I2C habilitado")


    # =====================================================
    # CALIBRACIÓN
    # =====================================================

    print("\nLeyendo calibración...")

    calibration_event.clear()

    board.i2c_read(
        BMP180,
        CALIBRATION,
        22,
        callback=i2c_callback
    )

    if not calibration_event.wait(2):
        raise RuntimeError(
            "No se pudo obtener calibración"
        )

    print("✓ Calibración recibida")


    # =====================================================
    # BUCLE DE TELEMETRÍA
    # =====================================================

    print("\nSensor inicializado.")
    print("Leyendo temperatura y presión.")
    print("CTRL+C para salir.\n")

    while True:

        # ---------------------------------------------
        # Temperatura
        # ---------------------------------------------

        UT = read_temperature(board)

        temperature, B5 = calculate_temperature(UT)


        # ---------------------------------------------
        # Presión
        # ---------------------------------------------

        UP = read_pressure(board)

        pressure = calculate_pressure(
            UP,
            B5
        )


        # ---------------------------------------------
        # Altitud
        # ---------------------------------------------

        altitude = calculate_altitude(
            pressure
        )


        # ---------------------------------------------
        # Mostrar
        # ---------------------------------------------

        print(
            f"\r"
            f"🌡 {temperature:6.2f} °C   "
            f"📈 {pressure / 100:8.2f} hPa   "
            f"⛰ {altitude:7.2f} m",
            end="",
            flush=True
        )

        time.sleep(1)


except KeyboardInterrupt:

    print("\n\nDeteniendo...")


except Exception as e:

    print("\n\nERROR:")
    print(e)


finally:

    if board:

        try:
            board.shutdown()

        except:
            pass