# dez_registros.py


import pandas as pd
from app.sqlserver.db_connection import get_connection

# Lista das tabelas de interesse
tabelas = ["dbo.Email", "dbo.Recorte", "dbo.Parte", "dbo.Metadado"]

# Conecta ao banco
conn = get_connection()

for tabela in tabelas:
    print(f"\n🔹 Tabela: {tabela}")

    # Obtém a contagem total de registros
    try:
        total = pd.read_sql_query(f"SELECT COUNT(*) as total FROM {tabela};", conn).iloc[0]['total']
        print(f"📊 Total de registros: {total}")
    except Exception as e:
        print(f"⚠️ Erro ao contar registros: {e}")
        continue

    # Exibe os 10 primeiros registros
    try:
        df_preview = pd.read_sql_query(f"SELECT TOP 10 * FROM {tabela};", conn)
        print(df_preview)
    except Exception as e:
        print(f"⚠️ Erro ao buscar registros: {e}")

conn.close()
