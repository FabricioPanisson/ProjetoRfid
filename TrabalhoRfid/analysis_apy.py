import requests
import pandas as pd

url = "http://localhost:5000/logs_json"  # Exemplo de rota que você crie
response = requests.get(url)
if response.status_code == 200:
    logs = response.json()  # lista de dicts
    df = pd.DataFrame(logs)
    print(df.head())
else:
    print("Erro ao buscar logs:", response.status_code)


import matplotlib.pyplot as plt

# Entradas por dia (gráfico de barras)
plt.figure()
entry_count_per_day.plot(x='date', y='entry_count', kind='bar')
plt.title("Entradas por Dia")
plt.xlabel("Data")
plt.ylabel("Quantidade de Entradas")
plt.tight_layout()
plt.show()