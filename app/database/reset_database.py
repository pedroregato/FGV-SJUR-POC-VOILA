# reset_database.py

from app.database.db_connection import get_connection
from app.database.db_schema import criar_tabelas

def resetar_banco():
    conn = get_connection()
    cur = conn.cursor()

    print("🧨 Apagando tabelas existentes...")
    cur.execute("DROP TABLE IF EXISTS metadados_citacoes_fgv;")
    cur.execute("DROP TABLE IF EXISTS recortes;")
    cur.execute("DROP TABLE IF EXISTS emails;")
    cur.execute("DROP TABLE IF EXISTS emails_processados;")

    conn.commit()
    conn.close()

    print("⚙️ Recriando tabelas...")
    criar_tabelas()
    print("✅ Banco de dados reiniciado com sucesso.")

if __name__ == "__main__":
    resetar_banco()
