# scripts/main.py

import argparse
import logging
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para encontrar os módulos
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.modules.classifiers.archival_heuristic_classifier import ArchivalHeuristicClassifier
from scripts.collectors.outlook_collector import get_outlook_items
from scripts.processors.email_processor import process_email
from scripts.writers.file_writer import write_outputs


def setup_logging(level: str):
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        format="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")


def main():
    p = argparse.ArgumentParser(
        description="Pipeline de Coleta e Processamento de E-mails para Análise de Arquivamento.")
    p.add_argument("--account", required=True, help="Nome da conta do Outlook.")
    p.add_argument("--folder", default="inbox", help="Pasta-alvo (ex: 'inbox' ou 'Caixa de Entrada/Subpasta').")
    p.add_argument("--days", type=int, help="Número de dias para buscar (ex: 7 para a última semana).")
    p.add_argument("--limit", type=int, default=0, help="Limite máximo de e-mails a processar (0 para ilimitado).")
    p.add_argument("--out", default="outputs", help="Diretório de saída.")
    p.add_argument("--reset-out", action="store_true", help="Limpa o diretório de saída antes de executar.")
    p.add_argument("--log", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = p.parse_args()

    setup_logging(args.log)
    log = logging.getLogger(__name__)

    if args.reset_out and Path(args.out).exists():
        log.warning(f"Limpando diretório de saída: {args.out}")
        shutil.rmtree(args.out)

    Path(args.out).mkdir(parents=True, exist_ok=True)

    # --- 1. CARREGAR CLASSIFICADOR ---
    try:
        rules_path = project_root / "app" / "modules" / "classifiers" / "archival_heuristic_rules.json"
        classifier = ArchivalHeuristicClassifier(rules_path=rules_path)
        log.info(f"Classificador carregado de: {rules_path}")
    except Exception as e:
        log.error(f"Falha fatal ao carregar o classificador: {e}")
        sys.exit(1)

    # --- 2. COLETAR E-MAILS ---
    date_filter = None
    if args.days:
        start_date = datetime.now() - timedelta(days=args.days)
        date_filter = f"[ReceivedTime] >= '{start_date.strftime('%m/%d/%Y %I:%M %p')}'"

    try:
        log.info(f"Coletando e-mails de '{args.account}/{args.folder}'...")
        mail_items = get_outlook_items(args.account, args.folder, date_filter, args.limit)
        log.info(f"{len(mail_items)} e-mails coletados.")
    except Exception as e:
        log.error(f"Falha ao coletar e-mails: {e}")
        sys.exit(1)

    # --- 3. PROCESSAR E-MAILS ---
    processed_records = []
    total = len(mail_items)
    for i, item in enumerate(mail_items):
        log.info(f"Processando e-mail {i + 1}/{total}: {getattr(item, 'Subject', 'N/A')}")
        try:
            processed_data = process_email(item, classifier)
            if processed_data:
                processed_records.append(processed_data)
        except Exception as e:
            log.error(f"Erro ao processar e-mail '{getattr(item, 'Subject', 'N/A')}': {e}")

    # --- 4. GRAVAR SAÍDAS ---
    if not processed_records:
        log.info("Nenhum registro processado para gravar.")
        return

    try:
        log.info(f"Gravando {len(processed_records)} registros processados em '{args.out}'...")
        write_outputs(processed_records, args.out)
        log.info("Gravação concluída com sucesso.")
    except Exception as e:
        log.error(f"Falha ao gravar arquivos de saída: {e}")
        sys.exit(1)

    log.info("Pipeline executado com sucesso!")


if __name__ == "__main__":
    main()
