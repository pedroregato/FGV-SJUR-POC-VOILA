import sqlite3
import pandas as pd
from app.database.db_connection import get_connection

def listar_justificativas():
    conn = get_connection()
    query = """
        SELECT id, message_id, tipo, justificativa_ia
        FROM recortes
        ORDER BY id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Exibe as 10 primeiras como amostra
    print("\n📋 Justificativas encontradas:")
    for _, row in df.iterrows():
        print(f"📝 ID {row['id']} | Tipo: {row['tipo']}")
        justificativa = (row['justificativa_ia'] or '').strip()
        if justificativa:
            print(f"   💬 Justificativa: {justificativa[:120]}{'...' if len(justificativa) > 120 else ''}")
        else:
            print("   ⚠️ Sem justificativa registrada.")
        print()

    # Estatísticas
    total = len(df)
    com_just = df["justificativa_ia"].fillna("").str.strip().astype(bool).sum()
    sem_just = total - com_just
    print("📊 Estatísticas:")
    print(f"- Total de recortes: {total}")
    print(f"- Com justificativa: {com_just}")
    print(f"- Sem justificativa: {sem_just}")

if __name__ == "__main__":
    listar_justificativas()
