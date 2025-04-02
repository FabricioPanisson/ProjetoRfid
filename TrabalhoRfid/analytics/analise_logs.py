import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Ler os logs do banco de dados
conn = sqlite3.connect('data.db')
df = pd.read_sql_query("SELECT * FROM access_logs", conn)
conn.close()

# Converter datas
df['attempt_time'] = pd.to_datetime(df['attempt_time'])
df['date'] = df['attempt_time'].dt.date

# Exemplo: total de acessos permitidos por dia
df_permitidos = df[df['allowed'] == 1]
entradas_por_dia = df_permitidos.groupby('date')['id'].count().reset_index()
entradas_por_dia.columns = ['date', 'count']

print("Acessos permitidos por dia:")
print(entradas_por_dia)

# Gráfico rápido
entradas_por_dia.plot(x='date', y='count', kind='bar')
plt.title("Acessos Permitidos por Dia")
plt.xlabel("Data")
plt.ylabel("Quantidade")
plt.tight_layout()
plt.show()
