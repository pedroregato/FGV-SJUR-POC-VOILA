import logging
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


# 🔧 Carregar variáveis de ambiente
load_dotenv()

# 🔗 Configurações do banco
servidor = os.getenv("SQLSERVER_SERVER")
banco = os.getenv("SQLSERVER_DB")
usuario = os.getenv("SQLSERVER_USER")
senha = os.getenv("SQLSERVER_PWD")

# 🔍 Tabelas que esperamos encontrar no banco
TABELAS_ESPERADAS = {"dbo.Email", "dbo.Recorte", "dbo.Parte", "dbo.Metadado"}

# 🎯 Configuração de log
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_connection_string() -> str:
    """
    Monta a connection string para SQLAlchemy com SQL Server (ODBC Driver).
    """
    return (
        f"mssql+pyodbc://{usuario}:{senha}@{servidor}/{banco}"
        "?driver=ODBC+Driver+17+for+SQL+Server"
        "&TrustServerCertificate=yes"
        "&timeout=5"
    )


def verificar_estrutura_banco(engine: Engine) -> bool:
    """
    Verifica se as tabelas esperadas existem no banco de dados.
    """
    try:
        inspector = inspect(engine)
        tabelas_no_banco = {
            f"{schema}.{table}"
            for schema in inspector.get_schema_names()
            for table in inspector.get_table_names(schema=schema)
        }

        faltando = TABELAS_ESPERADAS - tabelas_no_banco

        if faltando:
            logger.error(f"❌ Tabelas ausentes no banco: {faltando}")
            raise Exception(f"Banco de dados incompleto. Tabelas ausentes: {', '.join(faltando)}")

        logger.info(f"✅ Estrutura do banco OK. Tabelas encontradas: {tabelas_no_banco}")
        return True

    except SQLAlchemyError as e:
        logger.exception(f"Erro ao verificar estrutura do banco: {e}")
        raise


def get_engine() -> Engine:
    """
    Retorna um objeto SQLAlchemy Engine conectado ao SQL Server.
    """
    try:
        conn_str = get_connection_string()
        logger.info(f"🔗 Tentando conexão com {servidor}.{banco}")

        engine = create_engine(conn_str)

        # Verifica se a estrutura está correta
        verificar_estrutura_banco(engine)

        logger.info(f"✅ Conexão estabelecida com {servidor}.{banco}")
        return engine

    except Exception as e:
        logger.error(f"❌ Erro ao conectar no banco {servidor}.{banco}: {e}")
        raise


def testar_conexao():
    """
    Função simples para testar a conexão e listar as tabelas.
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT GETDATE() AS DataHora"))
        for row in result:
            print(f"🕒 Data e hora do servidor: {row.DataHora}")


if __name__ == "__main__":
    testar_conexao()
