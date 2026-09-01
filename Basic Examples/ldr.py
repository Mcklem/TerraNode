from pymata4 import pymata4
import time

NODEMCU_IP = "192.168.1.37"
FIRMATA_PORT = 3030

ANALOG_PIN = 0  # A0

board = None

try:
    print(f"Conectando a {NODEMCU_IP}:{FIRMATA_PORT}...")

    board = pymata4.Pymata4(
        ip_address=NODEMCU_IP,
        ip_port=FIRMATA_PORT
    )

    print("✓ Firmata conectado")

    # Configurar A0 como entrada analógica
    board.set_pin_mode_analog_input(ANALOG_PIN)

    print("✓ A0 configurado")
    print("Leyendo sensor de luz...")
    print("Pulsa CTRL+C para salir\n")

    while True:

        value = board.analog_read(ANALOG_PIN)

        print(f"Luz: {value}")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nDeteniendo...")

except Exception as e:
    print(f"\nERROR: {e}")

finally:
    if board:
        try:
            board.shutdown()
        except:
            pass