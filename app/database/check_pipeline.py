import sqlite3
from pathlib import Path
import pandas as pd

# Caminho para o banco
db_path = Path.cwd().parents[1] / "data" / "sjur_recortes.db"
conn = sqlite3.connect(db_path)

# Consulta os registros de interesse
query = """
    SELECT id, message_id, nome_pesquisado, tribunal, publicacao
    FROM recortes
    WHERE id IN (3, 4)
"""
df = pd.read_sql_query(query, conn)
conn.close()

# Define o caminho para salvar o CSV
csv_path = Path.cwd().parents[1] / "data" / "recortes_amostra.csv"

# Salva o DataFrame como CSV
df.to_csv(csv_path, index=False, encoding="utf-8-sig")

print(f"✅ Arquivo CSV salvo com sucesso em: {csv_path}")
