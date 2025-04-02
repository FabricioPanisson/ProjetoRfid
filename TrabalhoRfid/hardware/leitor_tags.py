import RPi.GPIO as GPIO
import requests
from time import sleep

pushbutton_pin = 8
user_id = 1  # Substitua com o ID real de teste

GPIO.setmode(GPIO.BOARD)
GPIO.setup(pushbutton_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def send_access_request():
    try:
        response = requests.post('http://localhost:5000/access', json={"user_id": user_id})
        if response.status_code == 201:
            print(response.json())
        else:
            print("Erro ao registrar acesso:", response.status_code)
    except Exception as e:
        print("Erro:", e)

if __name__ == "__main__":
    print("Iniciando leitura do botão...")
    try:
        while True:
            if GPIO.input(pushbutton_pin) == GPIO.HIGH:
                print("Botão pressionado")
                send_access_request()
                sleep(0.5)
    except KeyboardInterrupt:
        print("Interrompido pelo usuário")
    finally:
        GPIO.cleanup()
