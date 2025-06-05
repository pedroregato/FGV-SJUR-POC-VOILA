import sqlite3
from pathlib import Path
import logging
import streamlit as st

# Caminho do banco de dados
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sjur_recortes.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

print(f'DB_PATH: {DB_PATH}')

# Configura logger local
logger = logging.getLogger(__name__)

# Verificação reforçada
if not DB_PATH.is_file():
    logger.error(f"ERRO CRÍTICO: O caminho {DB_PATH} não é um arquivo válido")
    logger.error("Verifique se o volume foi montado corretamente no container")
    st.error("Banco de dados não encontrado - Contate o administrador")
    st.stop()

# Tabelas obrigatórias
TABELAS_ESPERADAS = {"emails", "recortes", "partes", "metadados"}


def verificar_estrutura_banco(conn: sqlite3.Connection) -> bool:
    """Verifica se todas as tabelas esperadas existem no banco."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabelas_encontradas = {row[0] for row in cursor.fetchall()}
        faltando = TABELAS_ESPERADAS - tabelas_encontradas

        if faltando:
            st.error(f"⚠️ Banco de dados está incompleto. Tabelas ausentes: {', '.join(faltando)}")
            logger.error(f"Tabelas ausentes no banco: {faltando}")
            return False

        return True
    except Exception as e:
        logger.exception("Erro ao verificar estrutura do banco")
        st.error("Erro ao verificar a estrutura do banco de dados.")
        return False


def get_connection():
    """Retorna a conexão SQLite, validando existência e integridade do banco"""
    logger.info(f"🔍 Tentando conectar ao banco em: {DB_PATH}")

    if not DB_PATH.exists():
        st.error(f"❌ Banco de dados não encontrado em: {DB_PATH}")
        logger.error(f"Arquivo do banco ausente: {DB_PATH}")
        st.stop()

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        if not verificar_estrutura_banco(conn):
            st.stop()

        logger.info("✅ Conexão com o banco estabelecida com sucesso.")
        return conn

    except sqlite3.Error as e:
        logger.exception(f"Erro ao conectar ao banco SQLite em {DB_PATH}")
        st.error(f"Erro ao conectar ao banco de dados. Verifique a integridade do arquivo em {DB_PATH}.")
        st.stop()
