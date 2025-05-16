import sqlite3
import pandas as pd
from app.database.db_connection import get_connection

def verificar_reu_com_substring(substring: str = "vargas"):
    try:
        # Conecta ao banco
        conn = get_connection()

        # Consulta com filtro por papel = réu e substring insensível a caixa
        query = """
        SELECT *
        FROM partes
        WHERE LOWER(papel) = 'reu'
          AND LOWER(parte) LIKE ?
        """

        df = pd.read_sql_query(query, conn, params=[f"%{substring.lower()}%"])

        if df.empty:
            print(f"🔍 Nenhum réu encontrado contendo '{substring}'.")
        else:
            print(f"✅ Encontrados {len(df)} réus contendo '{substring}':\n")
            print(df)

        return df

    except Exception as e:
        print(f"❌ Erro durante a verificação: {e}")
        return pd.DataFrame()

# Executar
if __name__ == "__main__":
    verificar_reu_com_substring("vargas")
