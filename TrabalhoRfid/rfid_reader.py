import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import requests
from time import sleep

API_URL = "http://localhost:5000/access"  # Ajuste se necessário

# Dicionário: user_id -> True (já está dentro) ou False (está fora)
status_usuarios = {}

def send_access_request(user_id, event_type):
    try:
        data = {
            "user_id": user_id,
            "event_type": event_type
        }
        resp = requests.post(API_URL, json=data)
        if resp.status_code == 201:
            print("Resposta do servidor:", resp.json())
        else:
            print("Erro ao registrar acesso:", resp.status_code, resp.text)
    except Exception as e:
        print("Erro na conexão:", e)

def main():
    reader = SimpleMFRC522()
    print("Aproxime o cartão RFID. (CTRL+C para encerrar)")

    try:
        while True:
            print("Esperando cartão...")
            user_id, text = reader.read()
            print(f"Cartão detectado! ID={user_id}, Texto={text.strip()}")

            if user_id in status_usuarios and status_usuarios[user_id] is True:
                # Se está True => estava dentro, agora será "exit"
                event_type = "exit"
                status_usuarios[user_id] = False
            else:
                # Se não estava no dicionário ou estava False => "entry"
                event_type = "entry"
                status_usuarios[user_id] = True

            send_access_request(user_id, event_type)
            sleep(2)
    except KeyboardInterrupt:
        print("Encerrando...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
