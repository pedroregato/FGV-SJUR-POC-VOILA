import pandas as pd
import sys

# Adicione o caminho correto para importar o módulo db_connection
sys.path.append("F:/FGV-SJUR/sjur-poc-voila/app/database")
from db_connection import get_connection

def consultar_justificativas_com_publicacao():
    conn = get_connection()

    query = """
    SELECT 
        r.id,
        r.message_id,
        r.nome_pesquisado,
        r.tipo,
        r.justificativa_ia,
        r.publicacao
    FROM recortes r
    ORDER BY r.id ASC
    LIMIT 2
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    for idx, row in df.iterrows():
        print("=" * 100)
        print(f"📄 Recorte ID: {row['id']}")
        print(f"✉️ Message ID: {row['message_id']}")
        print(f"👤 Nome Pesquisado: {row['nome_pesquisado']}")
        print(f"🏷️ Tipo: {row['tipo']}")
        print(f"🧾 Justificativa IA: {row['justificativa_ia']}")
        print("\n📜 Publicação:\n")
        print(row['publicacao'])
        print("=" * 100 + "\n")

if __name__ == "__main__":
    consultar_justificativas_com_publicacao()
