from app.modules.serdon_processor.extrair_json_recortes import gerar_json_do_email, parse_email_html, extract_processos
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.modules.serdon_processor.outlook_ingestor import OutlookIngestor
from app.modules.serdon_processor.extrair_json_recortes import gerar_json_do_email, parse_email_html, extract_processos
from app.modules.classifiers.deepseek_classifier import classificar_publicacao
from app.modules.extractors.partes_extractor import extrair_partes_processo as extrair_partes
from app.database.db_operations import (
    registrar_email_processado,
    registrar_publicacao,
    registrar_partes,
    registrar_metadados
)

__all__ = [
    "gerar_json_do_email",
    "parse_email_html",
    "extract_processos"
]
def rodar_pipeline_sjur(
    pasta_html: Path,
    pasta_json: Path,
    limite: Optional[int] = None,
    salvar_logs: bool = False
):
    print("🚀 Iniciando pipeline do SJUR...\n")

    ingestor = OutlookIngestor()
    emails = ingestor.obter_emails()

    if limite:
        emails = emails[:limite]

    for idx, email in enumerate(emails, start=1):
        print(f"📧 [{idx}] Processando email ID: {email.EntryID} | Assunto: {email.Subject}")

        # Gera JSON da publicação
        caminho_json = gerar_json_do_email(email, pasta_html, pasta_json)
        if not caminho_json or not caminho_json.exists():
            print("⚠️ Email ignorado (sem publicação detectada).\n")
            continue

        # Lê o conteúdo do JSON
        with open(caminho_json, "r", encoding="utf-8") as f:
            json_publicacao = f.read()

        # Classificação com DeepSeek
        classificacao = classificar_publicacao(json_publicacao)

        # Extração de partes
        partes_extraidas = extrair_partes(json_publicacao)

        # Data atual para registro
        data_processamento = datetime.now().isoformat()

        # Message ID
        message_id = email.EntryID

        # Metadados
        metadados = {
            "assunto": email.Subject or "",
            "remetente": email.SenderEmailAddress or "",
            "data_recebimento": email.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S") if email.ReceivedTime else ""
        }

        # Registro no banco de dados
        registrar_email_processado(message_id, data_processamento)
        registrar_publicacao(message_id, classificacao, json_publicacao)
        registrar_partes(message_id, partes_extraidas)
        registrar_metadados(message_id, metadados)

        print("✅ Registro concluído.\n")

    print("🎉 Pipeline finalizado com sucesso.")

