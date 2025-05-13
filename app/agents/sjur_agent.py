from pathlib import Path
from datetime import datetime
import json
import logging
from typing import Optional, Dict, List, Any
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
    registrar_metadados_dict,
    email_ja_foi_processado
)

# Configuração do logger
logger = logging.getLogger(__name__)


class PipelineStats:
    """Classe para armazenar estatísticas do pipeline"""

    def __init__(self):
        self.total_emails = 0
        self.emails_processados = 0
        self.recortes_processados = 0
        self.erros = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            'total_emails': self.total_emails,
            'emails_processados': self.emails_processados,
            'recortes_processados': self.recortes_processados,
            'erros': self.erros
        }


def validar_dados_email(dados_json: Dict[str, Any]) -> bool:
    """Valida a estrutura básica dos dados do email"""
    required_fields = ['message_id', 'dados_escritorio']
    for field in required_fields:
        if field not in dados_json:
            logger.error(f"Campo obrigatório faltando no JSON: {field}")
            return False
    return True


def processar_recorte(
        recorte: Dict[str, Any],
        message_id: str,
        llm_classifier: DeepSeekLegalClassifier,
        usar_mock_llm: bool,
        stats: PipelineStats
) -> Optional[int]:
    """Processa um único recorte do email"""
    try:
        publicacao_bruta = recorte.get("publicacao", "")

        if isinstance(publicacao_bruta, dict):
            publicacao_bruta = (
                    publicacao_bruta.get("conteudo")
                    or publicacao_bruta.get("texto")
                    or publicacao_bruta.get("raw_text")
                    or ""
            )

        if not isinstance(publicacao_bruta, str) or not publicacao_bruta.strip():
            logger.warning(f"Recorte ignorado - sem texto válido. Tipo: {type(recorte.get('publicacao'))}")
            return None

        # Classificação do texto
        resultado = llm_classifier.classify_text(publicacao_bruta)

        # Registro do recorte
        id_recorte = registrar_recorte(
            message_id=message_id,
            nome_pesquisado=recorte.get("nome_pesquisado", ""),
            tribunal=recorte.get("tribunal", ""),
            secretaria=recorte.get("secretaria", ""),
            data_publicacao=recorte.get("data_publicacao", ""),
            publicacao=publicacao_bruta,
            tipo=resultado.classification,
            justificativa_ia=resultado.justification
        )
        stats.recortes_processados += 1

        # Extração de partes
        partes = extrair_partes_processo(publicacao_bruta)
        registrar_partes(id_recorte, partes)

        # Extração de metadados
        metadados = (
            gerar_mock_metadados(publicacao_bruta)
            if usar_mock_llm
            else extrair_metadados_publicacao(publicacao_bruta))

        if metadados:
            registrar_metadados_dict(id_recorte, metadados)

        return id_recorte

    except Exception as e:
        logger.error(f"Erro ao processar recorte: {e}", exc_info=True)
        stats.erros += 1
        return None


def rodar_pipeline_sjur(
        pasta_html: Path,
        pasta_json: Path,
        limite: Optional[int] = None,
        salvar_logs: bool = False,
        usar_mock_llm: bool = False
) -> Dict[str, int]:
    """Processa emails do SJUR extraindo informações jurídicas.

    Args:
        pasta_html: Diretório contendo os emails em HTML
        pasta_json: Diretório para salvar os JSONs processados
        limite: Número máximo de emails a processar (None para todos)
        salvar_logs: Se deve salvar logs detalhados
        usar_mock_llm: Usar dados mockados para testes

    Returns:
        Dicionário com estatísticas de processamento:
        {
            'total_emails': int,
            'emails_processados': int,
            'recortes_processados': int,
            'erros': int
        }
    """
    # Configuração inicial
    if salvar_logs:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename='pipeline_sjur.log'
        )

    stats = PipelineStats()
    logger.info("🚀 Iniciando pipeline do SJUR")

    try:
        # Inicialização dos componentes
        ingestor = OutlookIngestor(pasta_html=pasta_html, pasta_json=pasta_json)
        emails = ingestor.emails_extraidos[:limite] if limite else ingestor.emails_extraidos
        llm_classifier = DeepSeekLegalClassifier()
        stats.total_emails = len(emails)

        for idx, email_obj in enumerate(emails, start=1):
            email_id = email_obj.EntryID
            try:
                logger.info(f"📧 [{idx}/{len(emails)}] Processando email ID: {email_id} | Assunto: {email_obj.Subject}")

                caminho_json = gerar_json_do_email(email_obj, pasta_html, pasta_json)
                if not caminho_json or not caminho_json.exists():
                    logger.warning(f"Email {email_id} ignorado - sem recortes detectados")
                    continue

                # Carregamento e validação dos dados
                with open(caminho_json, "r", encoding="utf-8") as f:
                    dados_json = json.load(f)

                if not validar_dados_email(dados_json):
                    logger.error(f"Estrutura inválida no JSON do email {email_id}")
                    stats.erros += 1
                    continue

                message_id = dados_json["message_id"]

                # Verificação de duplicatas
                if email_ja_foi_processado(message_id):
                    logger.info(f"Email {message_id} já processado anteriormente - ignorando")
                    continue

                # Registro do email
                url_email = gerar_link_outlook_por_message_id(email_obj.EntryID)
                registrar_email(
                    message_id=message_id,
                    data_recebimento=dados_json.get("data_recebimento"),
                    assunto=dados_json.get("assunto"),
                    remetente=dados_json.get("remetente"),
                    escritorio=dados_json["dados_escritorio"].get("escritorio"),
                    codigo=dados_json["dados_escritorio"].get("codigo"),
                    area=dados_json["dados_escritorio"].get("area"),
                    jornal=dados_json["dados_escritorio"].get("jornal"),
                    data_disponibilizacao=dados_json["dados_escritorio"].get("data_disponibilizacao"),
                    data_processamento=datetime.now().isoformat(),
                    url_email=url_email
                )
                stats.emails_processados += 1

                # Processamento dos recortes
                for recorte in dados_json.get("pesquisas", []):
                    processar_recorte(recorte, message_id, llm_classifier, usar_mock_llm, stats)

                logger.info(f"✅ Email {message_id} processado com sucesso")

            except Exception as e:
                logger.error(f"❌ Erro ao processar email {email_id}: {e}", exc_info=True)
                stats.erros += 1

    except Exception as e:
        logger.critical(f"Falha crítica no pipeline: {e}", exc_info=True)
        stats.erros += 1
        raise

    logger.info(f"🏁 Pipeline concluído. Estatísticas: {stats.to_dict()}")
    return stats.to_dict()