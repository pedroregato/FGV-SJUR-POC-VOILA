import argparse
from pathlib import Path
import sys

# Ajuste do path relativo ao root do projeto
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.sjur_agent import rodar_pipeline_sjur
from app.database.db_schema import criar_tabelas

# Diretórios esperados
HTML_DIR = Path("data/emails_html")
JSON_DIR = Path("data/emails_json")
LOG_DIR = Path("logs")

for path in [HTML_DIR, JSON_DIR, LOG_DIR]:
    if path.exists() and path.is_dir():
        print(f"✅ Pasta acessível: {path}")
    elif path.exists():
        print(f"⚠️ Caminho existe mas não é uma pasta: {path}")
    else:
        print(f"❌ Pasta não encontrada: {path}")

REQUIRED_DIRECTORIES = [HTML_DIR, JSON_DIR, LOG_DIR]

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
    print("✅ Criando ou atualizando estrutura do banco de dados...")
    from app.database.db_connection import get_connection
    conn = get_connection()
    try:
        criar_tabelas(conn)
        print("✅ Estrutura do banco de dados atualizada com sucesso.")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Homologação do pipeline de ingestão de e-mails da SERDON.")
    parser.add_argument("--limit", type=int, default=None, help="Número de e-mails a processar (opcional)")
    parser.add_argument("--mock", action="store_true", help="Usa mock de metadados em vez da LLM")
    args = parser.parse_args()

    print(f"📬 Iniciando processamento de até {args.limit or 'todos'} e-mails. Modo mock: {args.mock}")

    # verificar_estrutura_basica()
    # verificar_tabelas_banco()

    print("🚀 Iniciando homologação do pipeline...")
    rodar_pipeline_sjur(
        pasta_html=HTML_DIR,
        pasta_json=JSON_DIR,
        limite=args.limit,
        salvar_logs=True,
        usar_mock_llm=args.mock
    )
    print("✅ Homologação concluída com sucesso.")

if __name__ == "__main__":
    main()
