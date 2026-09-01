from pymata4 import pymata4
import time

NODEMCU_IP = "192.168.1.37"
FIRMATA_PORT = 3030  # Puerto habitual de Firmata WiFi

print(f"Conectando con NodeMCU en {NODEMCU_IP}:{FIRMATA_PORT}...")

try:
    board = pymata4.Pymata4(
        ip_address=NODEMCU_IP,
        ip_port=FIRMATA_PORT
    )

    print("✓ Conexión Firmata establecida")

    # En ESP8266, D4 suele corresponder a GPIO2
    PIN = 2

    print(f"Configurando GPIO {PIN} como salida...")
    board.set_pin_mode_digital_output(PIN)

    print("Encendiendo pin...")
    board.digital_write(PIN, 1)
    time.sleep(1)

    print("Apagando pin...")
    board.digital_write(PIN, 0)

    print("✓ PRUEBA COMPLETADA CORRECTAMENTE")

except Exception as e:
    print("✗ ERROR")
    print(e)

finally:
    try:
        board.shutdown()
    except:
        pass
