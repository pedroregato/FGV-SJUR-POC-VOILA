import json
import os
import re
import requests
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
from dotenv import load_dotenv

from app.modules.prompts.prompt_definitions import carregar_prompt_custom

# Carrega .env apenas uma vez no topo
load_dotenv()

ClassificationLabel = Literal["citação", "intimação", "não previsto"]

@dataclass
class ClassificationResult:
    classification: ClassificationLabel
    status: str
    method: Literal["ia_deepseek", "fallback_local"]
    confidence: float = 1.0
    justification: Optional[str] = None

class DeepSeekAPIClient:
    def __init__(self, api_key: str = None):
        if not api_key:
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            if not self.api_key:
                print("❌ A variável DEEPSEEK_API_KEY não foi encontrada no .env ou no ambiente.")
                exit(1)
        else: self.api_key = api_key

        self.api_url = "https://api.deepseek.com/v1/chat/completions"
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

class DeepSeekLegalClassifier:
    def __init__(self, api_key: str = None):
        self.api_client = DeepSeekAPIClient(api_key)
        self.classifier_type = "deepseek"
        self.system_prompt = carregar_prompt_custom()
        self.cnj_regex = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

    def _validate_classification(self, classification: str, justification: str) -> bool:
        """Valida apenas se a resposta está no formato esperado."""
        if classification not in ("citação", "intimação", "não previsto"):
            return False
        if not justification or len(justification.split()) > 30:
            return False
        return True

    def _parse_api_response(self, response: dict, original_text: str) -> ClassificationResult:
        """Processa a resposta da API e valida a classificação"""
        try:
            resposta_bruta = response['choices'][0]['message']['content']
            print(f"🧠 DeepSeek resposta bruta:\n{resposta_bruta}")

            # Remove blocos markdown
            resposta_bruta = resposta_bruta.strip()
            if resposta_bruta.startswith("```json"):
                resposta_bruta = resposta_bruta[7:-3].strip()
            elif resposta_bruta.startswith("```"):
                resposta_bruta = resposta_bruta[3:-3].strip()

            resposta_json = json.loads(resposta_bruta)
            classificacao = resposta_json.get("classificacao", "").strip().lower()
            justificativa = resposta_json.get("justificativa", "").strip()

            if not self._validate_classification(classificacao, justificativa):
                print("⚠️ Classificação não atende aos critérios formais")
                return ClassificationResult("não previsto", "erro: regras não atendidas", "fallback_local")

            return ClassificationResult(
                classificacao,
                "sucesso",
                "ia_deepseek",
                justification=justificativa
            )

        except json.JSONDecodeError as e:
            print(f"❌ Erro ao decodificar JSON: {e}\nResposta: {resposta_bruta}")
            return ClassificationResult("não previsto", "erro: json inválido", "fallback_local")
        except KeyError as e:
            print(f"❌ Erro de chave na resposta: {e}")
            return ClassificationResult("não previsto", "erro: formato inesperado", "fallback_local")

    def classify_text(self, text: str) -> ClassificationResult:
        """Classifica o texto jurídico com validação rigorosa"""
        if not text.strip():
            return ClassificationResult("não previsto", "erro: texto vazio", "fallback_local")

        payload = {
            "model": "deepseek-chat",
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
    # Lê chave da API do ambiente
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ A variável DEEPSEEK_API_KEY não foi encontrada no .env ou no ambiente.")
        exit(1)

    texto_teste = '''
Publicacao Processo: 5092956-64.2025.8.13.0024 Orgao: 3ª Unidade Jurisdicional da Fazenda Publica do Juizado Especial 35º JD Belo Horizonte Data de disponibilizacao: 13/05/2025 Tipo de comunicacao: Intimacao Meio: Diario de Justica Eletronico Nacional Inteiro teor: https://pje.tjmg.jus.br:443/pje/Processo/ConsultaDocumento/listView.seam?x=25051210415004000010443411472 Parte: EMANUEL THAELYSON GOMES DANTAS Advogado: JULIO MARQUES DA SILVA NETO - OAB RN-20531 Conteudo: PODER JUDICIARIO DO ESTADO DE MINAS GERAIS Justica de Primeira Instancia Comarca de Belo Horizonte / 3ª Unidade Jurisdicional da Fazenda Publica do Juizado Especial 35º JD Belo Horizonte Avenida Francisco Sales, 1446, Santa Efigenia, Belo Horizonte - MG - CEP: 30150-224 PROCESSO Nº: 5092956-64.2025.8.13.0024 CLASSE: [CIVEL] PROCEDIMENTO DO JUIZADO ESPECIAL DA FAZENDA PUBLICA (14695) REQUERENTE: EMANUEL THAELYSON GOMES DANTAS CPF: 017.458.584-58 REQUERIDO(A): ESTADO DE MINAS GERAIS CPF: 18.715.615/0001-60 REQUERIDO(A): FUNDACAO GETULIO VARGAS CPF: 33.641.663/0001-44 CERTIDAO Fica a parte re, acima qualificada, CITADA para todos termos da acao judicial contra ela proposta pela parte promovente, conforme peticao inicial, advertindo-se o requerido de que devera apresentar contestacao ate a data da audiencia designada. Ficam as partes INTIMADAS, para ciencia da decisao retro e para ACESSAREM A AUDIENCIA VIRTUAL DE CONCILIACAO a ser realizada por VIDEOCONFERENCIA por meio da plataforma CNJ WEBEX.COM, designada conforme abaixo: Tipo: Conciliacao (12740) Sala: https://x.gd/nSiHp (REUNIAO:23432680925)M/LARAN-24 Data/Hora: 20/07/26 09:00. Senha para acesso: 1234. O nao comparecimento ou a recusa da parte de participar da audiencia de conciliacao virtual podera ensejar a aplicacao de contumacia ou revelia, conforme o caso. As partes e seus advogados deverao se identificar na audiencia de conciliacao com exibicao de documento oficial de identidade com foto. O acesso a sala de audiencia virtual pela parte autora e pela parte re e OBRIGATORIO, devendo as partes e seus procuradores participar da audiencia de conciliacao virtual, em data e horario supramencionados. Os procuradores ficam encarregados de dar ciencia aos seus respectivos clientes encaminhando o link da audiencia. Belo Horizonte, 12 de maio de 2025. DENISE MENDES NOGUEIRA Servidor(a) e Retificador(a) |comunicacao_id: 268952877|
'''


    classificador = DeepSeekLegalClassifier(api_key)
    resultado = classificador.classify_text(texto_teste)

    print("\n🔍 Resultado da Classificação:")
    print(f"🏷️ Classificação: {resultado.classification}")
    print(f"🧾 Justificativa: {resultado.justification}")
    print(f"⚙️ Método: {resultado.method}")
    print(f"📈 Confiança: {resultado.confidence}")
    print(f"📡 Status: {resultado.status}")