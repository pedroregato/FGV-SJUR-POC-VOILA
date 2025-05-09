import sqlite3
import pandas as pd
from app.database.db_connection import get_connection
from app.database.db_schema import criar_tabelas


# Lista das tabelas de interesse
tabelas = ["emails_processados", "publicacoes", "partes", "metadados"]

# Conecta ao banco
conn = get_connection()

for tabela in tabelas:
    print(f"\n🔹 Tabela: {tabela}")

    # Obtém a contagem total de registros
    try:
        total = pd.read_sql_query(f"SELECT COUNT(*) as total FROM {tabela}", conn).iloc[0]['total']
        print(f"📊 Total de registros: {total}")
    except Exception as e:
        print(f"⚠️ Erro ao contar registros: {e}")
        continue

    # Exibe os 10 primeiros registros
    try:
        df_preview = pd.read_sql_query(f"SELECT * FROM {tabela} LIMIT 10", conn)
        print(df_preview)
    except Exception as e:
        print(f"⚠️ Erro ao buscar registros: {e}")

conn.close()
