from pymata4 import pymata4
import time

NODEMCU_IP = "192.168.1.37"
FIRMATA_PORT = 3030

# D1 en NodeMCU ESP8266 corresponde normalmente a GPIO5
RELAY_PIN = 5

print("=" * 50)
print(" CONTROL DE RELÉ MEDIANTE FIRMATA WIFI")
print("=" * 50)

board = None

try:
    print(f"Conectando a {NODEMCU_IP}:{FIRMATA_PORT}...")

    board = pymata4.Pymata4(
        ip_address=NODEMCU_IP,
        ip_port=FIRMATA_PORT
    )

    print("✓ Conectado")

    board.set_pin_mode_digital_output(RELAY_PIN)

    print("Relé preparado")

    while True:

        command = input(
            "\nComando [on / off / toggle / exit]: "
        ).strip().lower()

        if command == "on":

            print("Activando relé")
            board.digital_write(RELAY_PIN, 1)

        elif command == "off":

            print("Desactivando relé")
            board.digital_write(RELAY_PIN, 0)

        elif command == "toggle":

            print("Activando relé...")
            board.digital_write(RELAY_PIN, 1)

            time.sleep(2)

            print("Desactivando relé...")
            board.digital_write(RELAY_PIN, 0)

        elif command == "exit":

            print("Cerrando...")
            break

        else:

            print("Comando no reconocido")

except KeyboardInterrupt:

    print("\nInterrumpido por usuario")

except Exception as e:

    print(f"\nERROR: {e}")

finally:

    if board:
        try:
            # Estado seguro al cerrar
            board.digital_write(RELAY_PIN, 0)
            board.shutdown()
        except Exception:
            pass

    print("Programa terminado")