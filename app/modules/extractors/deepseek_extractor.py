import os
import re
import json
import requests
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis do .env
load_dotenv()

# Configurações do LLM
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_MODEL = "deepseek-chat"
LLM_TIMEOUT = 30  # segundos

DEEPSEEK_PROMPT = """
Você é um especialista em análise processual com profundo conhecimento da estrutura de documentos jurídicos.
Sua tarefa é identificar e classificar as partes processuais seguindo rigorosamente estas regras:

## Regras de Classificação:

1. CLASSIFICAÇÃO PRIORITÁRIA:
   - Quando encontrar padrões como "AUTOR: X" e "REU: Y, Z" no mesmo recorte:
     * X é sempre o autor principal
     * Y e Z são sempre réus conjuntos
     * IGNORE qualquer outra classificação anterior por ordem de menção

2. ORDEM DAS PARTES:
   Motivação: Esta regra é particularmente útil quando não se consegue deduzir claramente quem é réu e autor no texto.
   - A PRIMEIRA parte mencionada após "Parte:" é SEMPRE o AUTOR/EXEQUENTE/RECORRENTE
   - A ÚLTIMA parte mencionada após "Parte:" é SEMPRE o RÉU/EXECUTADO/RECORRIDO
   - Partes intermediárias devem ser classificadas por VÍNCULO:
     * Se houver conexão clara com o autor (mesmo grupo econômico, mesma área), classifique como AUTOR
     * Se houver conexão clara com o réu, classifique como RÉU
     * Caso ambíguo, classifique como INTERESSADO

3. NORMALIZAÇÃO:
   - Remova completamente:
     * Números de OAB (ex: OAB/SP 123456)
     * Números de processo/documentos
     * Termos como "Advogado:", "Parte:", "Processo:"
   - Mantenha apenas:
     * Nomes completos de pessoas físicas (em MAIÚSCULAS)
     * Razões sociais completas de empresas (em MAIÚSCULAS)
     * Órgãos/entidades completos (em MAIÚSCULAS)

4. ADVOGADOS:
   - Associe cada advogado à parte correspondente pela ORDEM:
     * Advogados listados após o autor são do AUTOR
     * Advogados listados após o réu são do RÉU
   - Remova completamente a OAB e mantenha apenas NOME COMPLETO

5. SAÍDA:
   - Gere STRICT JSON válido com:
     * autor: [nomes]
     * reu: [nomes]
     * interessados: [nomes]
     * advogados_autor: [nomes]
     * advogados_reu: [nomes]
     
## Sinônimos
1. Sinônimos de réu: impetrado, reu, coator, demandado     
2. Sinônimos de autor: impetrante, requerente, demandante

## Exemplo 1:
Input: 
"Parte: EMPRESA A LTDA Parte: EMPRESA B SA Advogado: JOÃO SILVA - OAB/SP 123456 Advogado: MARIA SOUZA - OAB/RJ 654321"

Output:
{
  "autor": ["EMPRESA A LTDA"],
  "reu": ["EMPRESA B SA"],
  "interessados": [],
  "advogados_autor": ["JOÃO SILVA", "MARIA SOUZA"],
  "advogados_reu": []
}

## Exemplo 2:
Input: 
"Parte: FULANO DE TAL Parte: CICLANO SILVA Parte: EMPRESA X LTDA Advogado: CARLOS PEREIRA - OAB/MG 789012"

Output:
{
  "autor": ["FULANO DE TAL"],
  "reu": ["EMPRESA X LTDA"],
  "interessados": ["CICLANO SILVA"],
  "advogados_autor": ["CARLOS PEREIRA"],
  "advogados_reu": []
}

## Exemplo 3 (Caso Complexo):
Input:
"Parte: BANCO DO BRASIL SA Parte: FUNDACAO GETULIO VARGAS Parte: MINISTERIO PUBLICO FEDERAL Advogado: ANA PAULA - OAB/DF 456789 Advogado: PEDRO HENRIQUE - OAB/SP 987654"

Output:
{
  "autor": ["BANCO DO BRASIL SA"],
  "reu": ["MINISTERIO PUBLICO FEDERAL"],
  "interessados": ["FUNDACAO GETULIO VARGAS"],
  "advogados_autor": ["ANA PAULA", "PEDRO HENRIQUE"],
  "advogados_reu": []
}

Retorne APENAS o JSON válido, sem comentários ou explicações.
"""

@dataclass
class PartesProcesso:
    autor: List[str]
    reu: List[str]
    interessados: List[str]
    advogados_autor: List[str]
    advogados_reu: List[str]

    def __post_init__(self):
        """Remove duplicatas, normaliza e filtra entidades vazias."""

        def processar_lista(lista: List[str]) -> List[str]:
            return sorted(
                list(
                    set(
                        self.limpar_entidade(nome)
                        for nome in lista
                        if nome and self.limpar_entidade(nome)
                    )
                ),
                key=lambda x: x  # Ordena alfabeticamente
            )

        self.autor = processar_lista(self.autor)
        self.reu = processar_lista(self.reu)
        self.interessados = processar_lista(self.interessados)
        self.advogados_autor = processar_lista(self.advogados_autor)
        self.advogados_reu = processar_lista(self.advogados_reu)
    @ staticmethod
    def limpar_entidade(texto: str) -> str:
        """Remove ruídos e normaliza."""
        if not texto:
            return ""

        # Remove OAB, documentos e outras informações irrelevantes
        texto = re.sub(r"\(OAB:[^)]+\)", "", texto)
        texto = re.sub(r"\b(?:DOC|Proc|Processo|n°?|nº?)\.?\s*[\d.-]+", "", texto)
        texto = re.sub(r"\b(?:fls?\.?|folha|fls)\s*\d+", "", texto, flags=re.IGNORECASE)

        # Remove termos processuais repetitivos
        texto = re.sub(r"\b(?:impetrante|impetrado|autor|reu|advogado|advogada)\b", "", texto, flags=re.IGNORECASE)

        # Normaliza espaços e formatação
        texto = re.sub(r"[^\w\s]", " ", texto)  # Substitui pontuação por espaço
        texto = re.sub(r"\s+", " ", texto).strip()  # Remove espaços extras
        return texto.upper()


def consultar_llm(texto: str) -> Optional[dict]:
    """Consulta o DeepSeek LLM para extração de partes processuais."""
    if not DEEPSEEK_API_KEY:
        logger.error("API key do DeepSeek não configurada no .env")
        return None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": DEEPSEEK_PROMPT},
            {"role": "user", "content": texto[:10000]}  # Limita o tamanho do input
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
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
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição ao DeepSeek: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao consultar LLM: {str(e)}")
        return None


def processar_resposta_llm(resposta: dict) -> Optional[PartesProcesso]:
    """Processa e valida a resposta do LLM."""
    if not resposta or 'choices' not in resposta:
        logger.error("Resposta do LLM inválida ou vazia")
        return None

    try:
        conteudo = resposta['choices'][0]['message']['content']
        dados = json.loads(conteudo)

        # Validação básica da estrutura
        if not all(key in dados for key in ['autor', 'reu', 'interessados', 'advogados_autor', 'advogados_reu']):
            logger.error("Estrutura do JSON retornado pelo LLM inválida")
            return None

        return PartesProcesso(
            autor=dados['autor'],
            reu=dados['reu'],
            interessados=dados['interessados'],
            advogados_autor=dados['advogados_autor'],
            advogados_reu=dados['advogados_reu']
        )
    except json.JSONDecodeError:
        logger.error("Resposta do LLM não é um JSON válido")
        return None
    except Exception as e:
        logger.error(f"Erro ao processar resposta do LLM: {str(e)}")
        return None


def extrair_partes_processo(texto: str) -> PartesProcesso:
    """
    Extrai partes processuais usando DeepSeek LLM com o novo prompt aprimorado.
    """
    if not texto:
        return PartesProcesso([], [], [], [], [])

    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": DEEPSEEK_PROMPT},
            {"role": "user", "content": texto[:10000]}
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        dados = response.json()

        # Processamento da resposta
        conteudo = dados['choices'][0]['message']['content']
        partes = json.loads(conteudo)

        return PartesProcesso(
            autor=partes.get('autor', []),
            reu=partes.get('reu', []),
            interessados=partes.get('interessados', []),
            advogados_autor=partes.get('advogados_autor', []),
            advogados_reu=partes.get('advogados_reu', [])
        )
    except Exception as e:
        logger.error(f"Erro na extração: {str(e)}")
        return PartesProcesso([], [], [], [], [])


# Exemplo de uso
if __name__ == "__main__":
    texto_exemplo = """
Publicacao Processo: 0804239-32.2025.8.19.0002 Orgao: 7ª Vara Civel da Comarca de Niteroi Data de disponibilizacao: 25/03/2025 Tipo de comunicacao: Intimacao Meio: Diario de Justica Eletronico Nacional Inteiro teor: https://tjrj.pje.jus.br/1g/Processo/ConsultaDocumento/listView.seam?x=25021414412467400000164184077 Parte: MARCO AURELIO TAVARES PEREZ Parte: ESTADO DO RIO DE JANEIRO Parte: FUNDACAO GETULIO VARGAS Advogado: CHRISTINA AIRES CORREA LIMA DE SIQUEIRA DIAS - OAB DF-11873 Advogado: JACQUELINE TAQUES DE SOUZA KUHN MONTEIRO - OAB RJ-063266 Advogado: PEDRO LUIZ MOREIRA AUAR PINTO - OAB RJ-234478 Advogado: BEATRIZ SARMENTO LEITE DO COUTO E SILVA - OAB RJ-001640 Advogado: LUCIANA GONCALVES NUNES MACEDO - OAB MG-83505 Advogado: MARCELO ROCHA DE MELLO MARTINS - OAB DF-06541 Conteudo: Poder Judiciario do Estado do Rio de Janeiro Comarca de Niteroi 7ª Vara Civel da Comarca de Niteroi Rua Visconde de Sepetiba, 519, 8º Andar, Centro, NITEROI - RJ - CEP: 24020-206 CERTIDAO Processo: 0804239-32.2025.8.19.0002 Classe: TUTELA CAUTELAR ANTECEDENTE (12134) AUTOR: MARCO AURELIO TAVARES PEREZ REU: ESTADO DO RIO DE JANEIRO, FUNDACAO GETULIO VARGAS Ao autor para recolher o valor das custas judiciais descritas no id. 172606343. NITEROI, 14 de fevereiro de 2025. MARCIO PONTES SOARES      """

    print("=== Extração com DeepSeek LLM ===")
    partes = extrair_partes_processo(texto_exemplo)
    print(partes)