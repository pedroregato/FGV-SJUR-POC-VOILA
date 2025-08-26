# deepseek_privado_classifier.py

import json
import os
import re
import requests
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
from dotenv import load_dotenv

from app.modules.prompts.classification_definitions import carregar_prompt_custom

# Carrega variáveis de ambiente
load_dotenv()

ClassificationLabel = Literal["citação", "intimação", "não previsto"]


@dataclass
class ClassificationResult:
    classification: ClassificationLabel
    status: str
    method: Literal["ia_deepseek_privado", "fallback_local"]
    confidence: float = 1.0
    justification: Optional[str] = None


class DeepSeekPrivadoAPIClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_PRIVADO_API_KEY")
        if not self.api_key:
            print("❌ A variável DEEPSEEK_PRIVADO_API_KEY não foi encontrada no .env ou no ambiente.")
            exit(1)

        self.api_url = os.getenv("DEEPSEEK_PRIVADO_URL", "http://20.98.105.56:3000/api/chat/completions")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def make_request(self, payload: dict, timeout: int = 10) -> Tuple[Optional[dict], Optional[str]]:
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            if response.status_code == 200:
                return response.json(), None
            return None, f"HTTP {response.status_code}: {response.text}"
        except Exception as e:
            return None, str(e)


class DeepSeekPrivadoLegalClassifier:
    def __init__(self, api_key: str = None):
        self.api_client = DeepSeekPrivadoAPIClient(api_key)
        self.classifier_type = "deepseek_privado"
        self.system_prompt = carregar_prompt_custom()
        self.cnj_regex = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

    def _validate_classification(self, classification: str, justification: str) -> bool:
        if classification not in ("citação", "intimação", "não previsto"):
            return False
        if not justification or len(justification.split()) > 30:
            return False
        return True

    def _parse_api_response(self, response: dict, original_text: str) -> ClassificationResult:
        try:
            resposta_bruta = response['choices'][0]['message']['content']
            print(f"🧠 DeepSeek Privado resposta bruta:\n{resposta_bruta}")

            # Extração do bloco JSON
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", resposta_bruta, re.DOTALL)
            if not json_match:
                json_match = re.search(r"(\{.*?\})", resposta_bruta, re.DOTALL)

            if not json_match:
                print("❌ Não foi possível encontrar bloco JSON na resposta.")
                return ClassificationResult("não previsto", "erro: json não encontrado", "fallback_local")

            json_str = json_match.group(1).strip()

            resposta_json = json.loads(json_str)
            classificacao = resposta_json.get("classificacao", "").strip().lower()
            justificativa = resposta_json.get("justificativa", "").strip()

            if not self._validate_classification(classificacao, justificativa):
                print("⚠️ Classificação não atende aos critérios formais")
                return ClassificationResult("não previsto", "erro: regras não atendidas", "fallback_local")

            return ClassificationResult(
                classificacao,
                "sucesso",
                "ia_deepseek_privado",
                justification=justificativa
            )

        except json.JSONDecodeError as e:
            print(f"❌ Erro ao decodificar JSON: {e}\nJSON extraído: {json_str}")
            return ClassificationResult("não previsto", "erro: json inválido", "fallback_local")
        except KeyError as e:
            print(f"❌ Erro de chave na resposta: {e}")
            return ClassificationResult("não previsto", "erro: formato inesperado", "fallback_local")

    def classify_text(self, text: str) -> ClassificationResult:
        if not text.strip():
            return ClassificationResult("não previsto", "erro: texto vazio", "fallback_local")

        payload = {
            "model": "rns96/deepseek-R1-ablated:f16_Q4KM",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.0,
            "max_tokens": 300,
            "top_p": 0.1
        }

        api_response, error = self.api_client.make_request(payload, timeout=30)
        if error:
            print(f"⚠️ Erro na requisição: {error}")
            return ClassificationResult("não previsto", f"erro: {error}", "fallback_local")

        return self._parse_api_response(api_response, text)


def classificar_publicacao_heuristica(texto_publicacao: str) -> ClassificationResult:
    texto = texto_publicacao.lower()

    if ("intime-se" in texto or "intimar" in texto) and any(term in texto for term in ["dia", "dias"]):
        return ClassificationResult("intimação", "heurística", "fallback_local", confidence=0.8)

    if "fundação getúlio vargas" in texto or "fgv" in texto:
        if "citação" in texto or "réu" in texto or "autor" in texto:
            return ClassificationResult("citação", "heurística", "fallback_local", confidence=0.9)

    return ClassificationResult("não previsto", "heurística", "fallback_local", confidence=0.7)


if __name__ == "__main__":
    api_key = os.getenv("DEEPSEEK_PRIVADO_API_KEY")
    if not api_key:
        print("❌ A variável DEEPSEEK_PRIVADO_API_KEY não foi encontrada no .env ou no ambiente.")
        exit(1)

    texto_teste = '''
Publicacao Processo: 5092956-64.2025.8.13.0024 Orgao: 3ª Unidade Jurisdicional da Fazenda Publica do Juizado Especial 35º JD Belo Horizonte Data de disponibilizacao: 13/05/2025 Tipo de comunicacao: Intimacao Meio: Diario de Justica Eletronico Nacional Inteiro teor: https://pje.tjmg.jus.br:443/pje/Processo/ConsultaDocumento/listView.seam?x=25051210415004000010443411472 Parte: EMANUEL THAELYSON GOMES DANTAS Advogado: JULIO MARQUES DA SILVA NETO - OAB RN-20531 Conteudo: PODER JUDICIARIO DO ESTADO DE MINAS GERAIS Justica de Primeira Instancia Comarca de Belo Horizonte / 3ª Unidade Jurisdicional da Fazenda Publica do Juizado Especial 35º JD Belo Horizonte Avenida Francisco Sales, 1446, Santa Efigenia, Belo Horizonte - MG - CEP: 30150-224 PROCESSO Nº: 5092956-64.2025.8.13.0024 CLASSE: [CIVEL] PROCEDIMENTO DO JUIZADO ESPECIAL DA FAZENDA PUBLICA (14695) REQUERENTE: EMANUEL THAELYSON GOMES DANTAS CPF: 017.458.584-58 REQUERIDO(A): ESTADO DE MINAS GERAIS CPF: 18.715.615/0001-60 REQUERIDO(A): FUNDACAO GETULIO VARGAS CPF: 33.641.663/0001-44 CERTIDAO Fica a parte re, acima qualificada, CITADA para todos termos da acao judicial contra ela proposta pela parte promovente, conforme peticao inicial, advertindo-se o requerido de que devera apresentar contestacao ate a data da audiencia designada. Ficam as partes INTIMADAS, para ciencia da decisao retro e para ACESSAREM A AUDIENCIA VIRTUAL DE CONCILIACAO a ser realizada por VIDEOCONFERENCIA por meio da plataforma CNJ WEBEX.COM, designada conforme abaixo: Tipo: Conciliacao (12740) Sala: https://x.gd/nSiHp (REUNIAO:23432680925)M/LARAN-24 Data/Hora: 20/07/26 09:00. Senha para acesso: 1234. O nao comparecimento ou a recusa da parte de participar da audiencia de conciliacao virtual podera ensejar a aplicacao de contumacia ou revelia, conforme o caso. As partes e seus advogados deverao se identificar na audiencia de conciliacao com exibicao de documento oficial de identidade com foto. O acesso a sala de audiencia virtual pela parte autora e pela parte re e OBRIGATORIO, devendo as partes e seus procuradores participar da audiencia de conciliacao virtual, em data e horario supramencionados. Os procuradores ficam encarregados de dar ciencia aos seus respectivos clientes encaminhando o link da audiencia. Belo Horizonte, 12 de maio de 2025. DENISE MENDES NOGUEIRA Servidor(a) e Retificador(a) |comunicacao_id: 268952877|
'''

    classificador = DeepSeekPrivadoLegalClassifier(api_key)
    resultado = classificador.classify_text(texto_teste)

    print("\n🔍 Resultado da Classificação:")
    print(f"🏷️ Classificação: {resultado.classification}")
    print(f"🧾 Justificativa: {resultado.justification}")
    print(f"⚙️ Método: {resultado.method}")
    print(f"📈 Confiança: {resultado.confidence}")
    print(f"📡 Status: {resultado.status}")
