from pathlib import Path
from datetime import datetime
import json
import re
from bs4 import BeautifulSoup

from app.modules.serdon_processor.outlook_ingestor import OutlookIngestor
from app.modules.serdon_processor.extrair_json_recortes import gerar_json_do_email
from app.modules.classifiers.deepseek_classifier import classificar_publicacao
from app.modules.extractors.partes_extractor import extrair_partes_processo
from app.modules.extractors.metadados_extractor import extrair_metadados_publicacao
from app.database.db_operations import (
    registrar_email,
    registrar_recorte,
    registrar_partes,
    registrar_metadados
)


from app.modules.extractors.mock_metadados import gerar_mock_metadados

# Dentro de sjur_agent.py
def rodar_pipeline_sjur(pasta_html: Path, pasta_json: Path, limite: int = None, salvar_logs: bool = False, usar_mock_llm: bool = False):
    print("🚀 Iniciando pipeline do SJUR...\n")

    ingestor = OutlookIngestor(pasta_html=pasta_html, pasta_json=pasta_json)
    emails = ingestor.emails_extraidos[:limite] if limite else ingestor.emails_extraidos

    for idx, email_obj in enumerate(emails, start=1):
        try:
            print(f"📧 [{idx}] Processando email ID: {email_obj.EntryID} | Assunto: {email_obj.Subject}")

            caminho_json = gerar_json_do_email(email_obj, pasta_html, pasta_json)
            if not caminho_json or not caminho_json.exists():
                print("⚠️ Email ignorado (sem recortes detectados).\n")
                continue

            with open(caminho_json, "r", encoding="utf-8") as f:
                dados_json = json.load(f)

            message_id = dados_json["message_id"]
            data_recebimento = dados_json.get("data_recebimento")
            data_processamento = datetime.now().isoformat()
            assunto = dados_json.get("assunto")
            remetente = dados_json.get("remetente")
            escritorio = dados_json["dados_escritorio"].get("escritorio")
            codigo = dados_json["dados_escritorio"].get("codigo")
            area = dados_json["dados_escritorio"].get("area")
            jornal = dados_json["dados_escritorio"].get("jornal")
            data_disponibilizacao = dados_json["dados_escritorio"].get("data_disponibilizacao")

            registrar_email(
                message_id=message_id,
                data_recebimento=data_recebimento,
                assunto=assunto,
                remetente=remetente,
                escritorio=escritorio,
                codigo=codigo,
                area=area,
                jornal=jornal,
                data_disponibilizacao=data_disponibilizacao,
                data_processamento=data_processamento
            )

            for recorte in dados_json.get("pesquisas", []):
                texto = recorte.get("publicacao", "")
                if not isinstance(texto, str) or not texto.strip():
                    print(f"⚠️ Recorte ignorado (texto vazio ou inválido).\n")
                    continue

                tipo = classificar_publicacao(texto).classification

                id_recorte = registrar_recorte(
                    message_id=message_id,
                    nome_pesquisado=recorte.get("nome_pesquisado", ""),
                    tribunal=recorte.get("tribunal", ""),
                    secretaria=recorte.get("secretaria", ""),
                    data_publicacao=recorte.get("data_publicacao", ""),
                    publicacao=texto,
                    tipo=tipo
                )

                partes = extrair_partes_processo(texto)
                registrar_partes(id_recorte, partes)

                # Diagnóstico do uso de mock
                if usar_mock_llm:
                    print("🧪 Usando metadados mock para este recorte.")
                    metadados = gerar_mock_metadados(texto)
                else:
                    if not isinstance(texto, str):
                        print(
                            f"❌ ERRO: Tipo inesperado recebido para extração de metadados: {type(texto)} — conteúdo:\n{texto}\n")
                        continue
                    print("🔍 Extraindo metadados reais via LLM para este recorte.")
                    metadados = extrair_metadados_publicacao(texto)

            print("✅ Registro concluído.\n")

        except Exception as e:
            print(f"❌ Erro ao processar email [{idx}]: {e}\n")


