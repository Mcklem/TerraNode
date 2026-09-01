from pymata4 import pymata4

NODEMCU_IP = "192.168.1.37"
FIRMATA_PORT = 3030

# D2 = GPIO4
SERVO_PIN = 4

board = None

try:
    print(f"Conectando a {NODEMCU_IP}:{FIRMATA_PORT}...")

    board = pymata4.Pymata4(
        ip_address=NODEMCU_IP,
        ip_port=FIRMATA_PORT
    )

    print("✓ Conectado")

    print("Configurando servo...")

    board.set_pin_mode_servo(SERVO_PIN)

    print("Servo preparado.")
    print("Introduce un ángulo entre 0 y 180.")
    print("Escribe 'exit' para salir.")

    while True:

        command = input("\nÁngulo: ").strip().lower()

        if command == "exit":
            break

        try:
            angle = int(command)

            if angle < 0 or angle > 180:
                print("El ángulo debe estar entre 0 y 180")
                continue

            print(f"Moviendo servo a {angle}°")

            board.servo_write(SERVO_PIN, angle)

        except ValueError:
            print("Introduce un número válido")

except KeyboardInterrupt:
    print("\nInterrumpido")

except Exception as e:
    print(f"\nERROR: {e}")

finally:

    if board:
        try:
            board.shutdown()
        except Exception:
            pass

    print("Programa terminado")