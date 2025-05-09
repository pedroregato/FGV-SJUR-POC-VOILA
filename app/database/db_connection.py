import sqlite3
from pathlib import Path

# Caminho padrão do banco (pode ser parametrizado)
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sjur_recortes.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Para acesso por nome de coluna
    return conn
