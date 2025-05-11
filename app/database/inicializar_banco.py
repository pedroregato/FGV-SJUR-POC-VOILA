# inicializar_banco.py

from app.database.db_connection import get_connection
from app.database.db_schema import criar_tabelas

def inicializar_banco():
    print("🚀 Iniciando criação da estrutura do banco de dados...")
    try:
        conn = get_connection()
        criar_tabelas(conn)
        print("✅ Estrutura do banco criada ou atualizada com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao inicializar o banco: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    inicializar_banco()
