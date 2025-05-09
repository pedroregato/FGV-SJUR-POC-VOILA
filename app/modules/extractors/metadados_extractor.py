import os
import re
import json
import requests
from dotenv import load_dotenv
import logging
from typing import Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis do .env
load_dotenv()

# Configurações do LLM
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_MODEL = "deepseek-chat"
LLM_TIMEOUT = 60

DEEPSEEK_PROMPT_METADADOS = """
Extraia os seguintes campos do texto da publicação:

- orgao
- comarca
- classe
- data_publicacao
- unidade_fgv
- obrigacoes: uma lista com todas as frases que expressem ordens, determinações ou obrigações (ex: verbos no imperativo como "Recolha", "Apresente", "Cumpra-se", "Cite-se")

Os campos tribunal, número do processo, UF e conteudo_publicado já foram extraídos por outros meios e não precisam ser retornados.
A data deve estar no formato YYYY-MM-DD. Se o texto contiver "certame", "gabarito" ou "concurso", a unidade_fgv deve ser "FGV Conhecimento".

Retorne apenas JSON com os 6 campos indicados, mesmo se algum estiver em branco ou a lista estiver vazia.
"""

def parse_numero_processo(numero_processo: str) -> dict:
    padrao = r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$"
    match = re.match(padrao, numero_processo)
    if not match:
        raise ValueError("Formato inválido. Esperado: NNNNNNN-DD.AAAA.J.TR.OOOO")

    sequencial, digito, ano, justica_id, tribunal_id, orgao_cnj = match.groups()
    uf_codigo = tribunal_id
    orgao_local = orgao_cnj[2:]

    ufs = {
        "01": "AC", "02": "AL", "03": "AP", "04": "AM", "05": "BA",
        "06": "CE", "07": "DF", "08": "ES", "09": "GO", "10": "MA",
        "11": "MT", "12": "MS", "13": "MG", "14": "PA", "15": "PB",
        "16": "PR", "17": "PE", "18": "PI", "19": "RJ", "20": "RN",
        "21": "RS", "22": "RO", "23": "RR", "24": "SC", "25": "SP",
        "26": "SP", "27": "SE", "28": "TO"
    }

    tribunais = {
        "07": "TRF1", "08": "TRF2", "09": "TRF3", "10": "TRF4", "11": "TRF5",
        "12": "TRF6", "13": "TRT1", "14": "TRT2", "15": "TRT3", "16": "TRT4",
        "17": "TRT5", "18": "TRT6", "19": "TJ-RJ", "20": "TJ-RN", "21": "TJ-RS",
        "22": "TJ-RO", "23": "TJ-RR", "24": "TJ-SC", "25": "TJ-SP", "26": "TJ-SE",
        "27": "TJ-TO", "28": "TJ-BA"
    }

    return {
        "numero_processo": numero_processo,
        "uf": ufs.get(uf_codigo, "Desconhecido"),
        "tribunal": tribunais.get(tribunal_id, "Desconhecido")
    }

def contar_ocorrencias_igpm(texto: str) -> int:
    padrao = r"\bIGP[- ]?M\b"
    return len(re.findall(padrao, texto, flags=re.IGNORECASE))

def extrair_conteudo_publicado_regex(texto: str) -> str:
    match = re.search(r"(?i)conte[uú]do:\s*(.*)", texto)
    if match:
        return match.group(1).strip()
    return "indeterminado"

def extrair_metadados_publicacao(texto: str) -> Optional[dict]:
    if not texto or not DEEPSEEK_API_KEY:
        logger.error("Texto vazio ou chave de API não configurada.")
        return None

    match = re.search(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", texto)
    numero_processo = match.group(0) if match else None

    if not numero_processo:
        logger.warning("Número do processo não encontrado no texto.")
        return None

    info_processo = parse_numero_processo(numero_processo)
    contador_igpm = contar_ocorrencias_igpm(texto)
    conteudo_publicado = extrair_conteudo_publicado_regex(texto)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": DEEPSEEK_PROMPT_METADADOS},
            {"role": "user", "content": texto[:10000]}
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=LLM_TIMEOUT
        )
        response.raise_for_status()
        resposta = response.json()

        conteudo = resposta['choices'][0]['message']['content']
        try:
            dados_llm = json.loads(conteudo)
        except json.JSONDecodeError as e:
            logger.error(f"Falha ao decodificar JSON retornado pela LLM: {e}\nConteúdo recebido:\n{conteudo}")
            return None

        resultado = {
            "numero_processo": info_processo["numero_processo"],
            "tribunal": info_processo["tribunal"],
            "uf": info_processo["uf"],
            "igpm_count": contador_igpm,
            "conteudo_publicado": conteudo_publicado,
            **dados_llm
        }

        return resultado

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.error(f"Erro na requisição ou no processamento: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        return None

if __name__ == "__main__":
    texto_exemplo = """
    Sr. Advogado, LISTAS DE INTIMACOES DISPONIBILIZADAS NO PJE 1º GRAU (Ultimos 60 Dias) Esta pagina contem as listas diarias de intimacoes eletronicas dirigidas aos advogados e as partes disponibilizadas no Sistema PJe 1º Grau. As listas so contem as intimacoes disponibilizadas no Sistema PJe (nao constam das listas intimacoes relativas a processos fisicos). Cada lista e incluida nesta pagina no dia util seguinte ao da disponibilizacao das intimacoes eletronicas no Sistema PJe 1º Grau. As listas nao tem valor de intimacao e sim de comunicacao das intimacoes expedidas aos advogados por meio eletronico. Os processos em segredo de justica nao estao incluidos. ATENCAO: ESTE SERVICO NAO INTERFERE NA CONTAGEM DE PRAZO S NOS PROCESSOS ELETRONICOS, OS QUAIS SEGUIRAO A FORMA PREVISTA NO ART. 5º DA LEI Nº 11.419/2006. Justica Federal no Rio Grande do Norte – JFRN Lista de intimacoes disponibilizadas no PJe 1º grau Data da disponibilizacao das intimacoes listadas: 03/04/2025 Total de registros: 517 Relatorio gerado em : 03/04/2025 14:23:29 0000 - NPU: 0801950-78.2025.4.05.8400 Polo Ativo: WESLEY KELVIN DA SILVA FRANCISCO Polo Passivo: CONSELHO FEDERAL DA ORDEM DOS ADVOGADOS DO BRASIL/ FUNDACAO GETULIO VARGAS /PRESIDENTE DO CONSELHO FEDERAL DA ORDEM DOS ADVOGADOS DO BRASIL/PRESIDENTE DA FUNDACAO GETULIO VARGAS (FGV) Parte a qual se refere a intimacao: CONSELHO FEDERAL DA ORDEM DOS ADVOGADOS DO BRASIL Advogado ao qual e dirigida a intimacao: - OAB do advogado ao qual e dirigida a intimacao: - Advogados cadastrados no polo ativo: ALISSON ROCHA DOS SANTOS Advogados cadastrados no polo passivo: - Data e hora da disponibilizaca o da Intimacao no Painel: 03/04/2025 10:45:03 Identificador do documento: 4058400.16435694
    """

    metadados = extrair_metadados_publicacao(texto_exemplo)
    print(json.dumps(metadados, indent=2, ensure_ascii=False))
