from pymata4 import pymata4
import time

NODEMCU_IP = "192.168.1.37"
NODEMCU_PORT = 3030
ANALOG_PIN = 0  # A0

board = pymata4.Pymata4(
    ip_address=NODEMCU_IP,
    ip_port=NODEMCU_PORT
)

def callback(data):
    value = data[2]
    print(f"Lectura: {value}")

board.set_pin_mode_analog_input(ANALOG_PIN, callback)

print("Sensor capacitivo conectado.")
print("Realizando lecturas... Ctrl+C para salir.\n")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nDeteniendo...")

finally:
    board.shutdown()