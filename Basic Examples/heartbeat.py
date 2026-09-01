from pymata4 import pymata4
import time
import sys

NODEMCU_IP = "192.168.1.37"
FIRMATA_PORT = 3030

# LED integrado del NodeMCU
LED_PIN = 2

print("=" * 50)
print(" NODEMCU FIRMATA WIFI - PRUEBA DE VIDA")
print("=" * 50)

try:
    print(f"\n[+] Conectando a {NODEMCU_IP}:{FIRMATA_PORT}")

    board = pymata4.Pymata4(
        ip_address=NODEMCU_IP,
        ip_port=FIRMATA_PORT
    )

    print("[+] Conexión establecida correctamente")
    print("[+] Configurando LED integrado")

    board.set_pin_mode_digital_output(LED_PIN)

    contador = 0

    print("\n[+] Iniciando heartbeat")
    print("[+] Pulsa CTRL+C para detener\n")

    while True:
        contador += 1

        inicio = time.time()

        # En muchos NodeMCU el LED es activo en LOW
        board.digital_write(LED_PIN, 0)

        time.sleep(0.3)

        board.digital_write(LED_PIN, 1)

        tiempo = (time.time() - inicio) * 1000

        print(
            f"[OK] Heartbeat #{contador:04d} | "
            f"Comando enviado | "
            f"Tiempo ciclo: {tiempo:.1f} ms"
        )

        time.sleep(0.7)

except KeyboardInterrupt:
    print("\n\n[!] Deteniendo prueba...")

except Exception as e:
    print("\n[ERROR] Se perdió la comunicación")
    print(e)

finally:
    try:
        board.digital_write(LED_PIN, 1)
        board.shutdown()
        print("[+] Conexión cerrada correctamente")
    except:
        pass

    sys.exit()