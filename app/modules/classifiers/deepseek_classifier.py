import re
import os
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


class DeepSeekAPIClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("❌ Chave da API DeepSeek não fornecida ou inválida.")

        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
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
    def __init__(self, api_key: str):
        self.api_client = DeepSeekAPIClient(api_key)
        self.classifier_type = "deepseek"
        self.system_prompt = carregar_prompt_custom()

    def classify_text(self, text: str) -> ClassificationResult:
        if not text.strip():
            return ClassificationResult("não previsto", "erro: texto vazio", "fallback_local")

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.0,
            "max_tokens": 20
        }

        api_response, error = self.api_client.make_request(payload, timeout=30)
        if error:
            return ClassificationResult("não previsto", f"erro: {error}", "fallback_local")

        try:
            result = api_response['choices'][0]['message']['content'].strip().lower()
            if result in ("citação", "intimação", "não previsto"):
                return ClassificationResult(result, "sucesso", "ia_deepseek")
            return ClassificationResult("não previsto", "erro: resposta inválida", "fallback_local")
        except KeyError:
            return ClassificationResult("não previsto", "erro: formato inesperado", "fallback_local")


def classificar_publicacao(texto_publicacao: str) -> ClassificationResult:
    """
    Versão simplificada do classificador para fallback heurístico.
    """
    texto = texto_publicacao.lower()
    if "fundação getúlio vargas" in texto or "fgv" in texto:
        if "citação" in texto or "réu" in texto or "autor" in texto:
            return ClassificationResult("citação", "heurística", "fallback_local", confidence=0.9)
    return ClassificationResult("não previsto", "heurística", "fallback_local", confidence=0.7)


# Teste manual
if __name__ == "__main__":
    # Lê chave da API do ambiente
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ A variável DEEPSEEK_API_KEY não foi encontrada no .env ou no ambiente.")
        exit(1)

    texto_teste = "Este texto não é de natureza jurídica e não apresenta número de processo."

    classificador = DeepSeekLegalClassifier(api_key)
    resultado = classificador.classify_text(texto_teste)

    print("🔍 Resultado da Classificação:")
    print(f"📄 Texto: {texto_teste}")
    print(f"🏷️ Classificação: {resultado.classification}")
    print(f"⚙️ Método: {resultado.method}")
    print(f"📈 Confiança: {resultado.confidence}")
    print(f"📡 Status: {resultado.status}")
