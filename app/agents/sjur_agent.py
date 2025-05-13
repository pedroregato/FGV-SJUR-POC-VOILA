from pathlib import Path
from datetime import datetime
import json
from bs4 import BeautifulSoup

from app.integrations.outlook_utils import gerar_link_outlook_por_message_id
from app.modules.serdon_processor.outlook_ingestor import OutlookIngestor

from app.modules.serdon_processor.extrair_json_recortes import gerar_json_do_email
from app.modules.classifiers.deepseek_classifier import DeepSeekLegalClassifier
from app.modules.extractors.partes_extractor import extrair_partes_processo
from app.modules.extractors.metadados_extractor import extrair_metadados_publicacao
from app.modules.extractors.mock_metadados import gerar_mock_metadados
from app.database.db_operations import (
    registrar_email,
    registrar_recorte,
    registrar_partes,
    registrar_metadados,
    registrar_metadados_dict,
    email_ja_foi_processado  # caso queira evitar reprocessamento duplicado
)
def rodar_pipeline_sjur(pasta_html: Path, pasta_json: Path, limite: int = None, salvar_logs: bool = False, usar_mock_llm: bool = False):
    print("🚀 Iniciando pipeline do SJUR...\n")

    ingestor = OutlookIngestor(pasta_html=pasta_html, pasta_json=pasta_json)
    emails = ingestor.emails_extraidos[:limite] if limite else ingestor.emails_extraidos
    llm_classifier = DeepSeekLegalClassifier()

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

            # (Opcional) Evita processamento duplicado
            if email_ja_foi_processado(message_id):
                print(f"⚠️ Email já processado anteriormente (message_id: {message_id}). Ignorando...\n")
                continue

            url_email = gerar_link_outlook_por_message_id(email_obj.EntryID)

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
                data_processamento=data_processamento,
                url_email=url_email  # ✅ argumento adicionado
            )

            for recorte in dados_json.get("pesquisas", []):
                publicacao_bruta = recorte.get("publicacao", "")

                # Se vier como dicionário, extrai campos comuns de texto
                if isinstance(publicacao_bruta, dict):
                    publicacao_bruta = (
                        publicacao_bruta.get("conteudo")
                        or publicacao_bruta.get("texto")
                        or publicacao_bruta.get("raw_text")
                        or ""
                    )

                # Verificação de tipo e conteúdo
                if not isinstance(publicacao_bruta, str) or not publicacao_bruta.strip():
                    print(f"⚠️ Recorte ignorado (sem texto válido extraído). Tipo original: {type(recorte.get('publicacao'))} — Conteúdo: {recorte.get('publicacao')}\n")
                    continue

                resultado = llm_classifier.classify_text(publicacao_bruta)
                tipo = resultado.classification
                justificativa = resultado.justification  # ⬅️ isto é essencial

                id_recorte = registrar_recorte(
                    message_id=message_id,
                    nome_pesquisado=recorte.get("nome_pesquisado", ""),
                    tribunal=recorte.get("tribunal", ""),
                    secretaria=recorte.get("secretaria", ""),
                    data_publicacao=recorte.get("data_publicacao", ""),
                    publicacao=publicacao_bruta,
                    tipo=tipo,
                    justificativa_ia=justificativa
                )

                partes = extrair_partes_processo(publicacao_bruta)
                registrar_partes(id_recorte, partes)

                if usar_mock_llm:
                    print("🧪 Usando metadados mock para este recorte.")
                    metadados = gerar_mock_metadados(publicacao_bruta)
                else:
                    print("🔍 Extraindo metadados reais via LLM para este recorte.")
                    metadados = extrair_metadados_publicacao(publicacao_bruta)

                if metadados:
                    registrar_metadados_dict(id_recorte, metadados)

            print("✅ Registro concluído.\n")

        except Exception as e:
            print(f"❌ Erro ao processar email [{idx}]: {e}\n")
