import argparse
from pathlib import Path
import sys
import sqlite3

# Ajuste de importações relativo ao root do projeto
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.sjur_agent import rodar_pipeline_sjur
from app.database.db_connection import get_connection

# Diretórios esperados
HTML_DIR = Path("data/emails_html")
JSON_DIR = Path("data/emails_json")
LOG_DIR = Path("logs")

REQUIRED_DIRECTORIES = [HTML_DIR, JSON_DIR, LOG_DIR]
REQUIRED_TABLES = ["emails_processados", "publicacoes", "partes", "metadados"]


def verificar_estrutura_basica():
    print("✅ Verificando estrutura do projeto...")
    for pasta in REQUIRED_DIRECTORIES:
        if not pasta.exists():
            print(f"🟡 Criando pasta: {pasta}")
            pasta.mkdir(parents=True, exist_ok=True)
        elif not pasta.is_dir():
            raise RuntimeError(f"❌ Caminho {pasta} existe mas não é um diretório válido.")
    print("✅ Estrutura de diretórios verificada com sucesso.")


def verificar_tabelas_banco():
    print("✅ Verificando estrutura do banco de dados...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas_existentes = {row[0] for row in cursor.fetchall()}

        for tabela in REQUIRED_TABLES:
            if tabela not in tabelas_existentes:
                print(f"🟡 Tabela ausente: {tabela} — criando...")
                if tabela == "emails_processados":
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS emails_processados (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message_id TEXT UNIQUE,
                            data_processamento TEXT
                        );
                    """)
                elif tabela == "publicacoes":
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS publicacoes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message_id TEXT,
                            texto TEXT,
                            tipo TEXT
                        );
                    """)
                elif tabela == "partes":
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS partes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message_id TEXT,
                            parte TEXT,
                            papel TEXT
                        );
                    """)
                elif tabela == "metadados":
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS metadados (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message_id TEXT,
                            chave TEXT,
                            valor TEXT
                        );
                    """)
            elif tabela == "emails_processados":
                cursor.execute("PRAGMA table_info(emails_processados)")
                colunas = [row[1] for row in cursor.fetchall()]
                if "data_processamento" not in colunas:
                    print("🛠️ Adicionando coluna 'data_processamento' na tabela emails_processados...")
                    cursor.execute("ALTER TABLE emails_processados ADD COLUMN data_processamento TEXT")

        conn.commit()
        print("✅ Estrutura do banco de dados verificada e ajustada.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Homologação do pipeline de ingestão de e-mails da SERDON.")
    parser.add_argument("--limit", type=int, default=None, help="Número de e-mails a processar (opcional)")
    args = parser.parse_args()

    verificar_estrutura_basica()
    verificar_tabelas_banco()

    print("🚀 Iniciando homologação do pipeline...")
    rodar_pipeline_sjur(
        pasta_html=HTML_DIR,
        pasta_json=JSON_DIR,
        limite=args.limit,
        salvar_logs=True
    )
    print("✅ Homologação concluída com sucesso.")


if __name__ == "__main__":
    main()
