# db_schema_ctrl
# Controle


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

def criar_tabelas_controle(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recortes_processados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_origem INTEGER,
            data_carga TEXT,
            LastModificationTime_origem TEXT,
            data_processamento TEXT
        );
    """)

    conn.commit()


