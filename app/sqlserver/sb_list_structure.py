import pandas as pd
from app.sqlserver.db_connection import get_engine


# Lista das tabelas de interesse
tabelas = ["dbo.Email", "dbo.Recorte", "dbo.Parte", "dbo.Metadado"]


def listar_estrutura_tabela(conn, tabela: str):
    schema, nome_tabela = tabela.split('.')
    query = f"""
        SELECT 
            COLUMN_NAME AS Coluna,
            DATA_TYPE AS Tipo,
            CHARACTER_MAXIMUM_LENGTH AS Tamanho,
            IS_NULLABLE AS PermiteNulo
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE 
            TABLE_SCHEMA = '{schema}' 
            AND TABLE_NAME = '{nome_tabela}'
        ORDER BY ORDINAL_POSITION;
    """

    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"⚠️ Erro ao obter estrutura da tabela {tabela}: {e}")
        return None


def main():
    conn = get_engine()

    for tabela in tabelas:
        print(f"\n🔹 Estrutura da Tabela: {tabela}")
        estrutura = listar_estrutura_tabela(conn, tabela)

        if estrutura is not None:
            print(estrutura.to_string(index=False))
        else:
            print(f"⚠️ Não foi possível obter a estrutura da tabela {tabela}")

    conn.close()


if __name__ == "__main__":
    main()
