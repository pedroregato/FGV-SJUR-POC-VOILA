import sqlite3
from pathlib import Path

# Caminho para o banco (ajuste se necessário)
db_path = Path.cwd().parent.parent / "data" / "sjur_recortes.db"

# Conectar ao banco
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verificar colunas existentes
cursor.execute("PRAGMA table_info(emails_processados);")
colunas = [linha[1] for linha in cursor.fetchall()]

# Adicionar a coluna se não existir
if "data_processamento" not in colunas:
    print("🛠️ Adicionando coluna 'data_processamento'...")
    cursor.execute("ALTER TABLE emails_processados ADD COLUMN data_processamento TEXT;")
    conn.commit()
    print("✅ Coluna adicionada com sucesso.")
else:
    print("ℹ️ A coluna 'data_processamento' já existe.")

conn.close()
