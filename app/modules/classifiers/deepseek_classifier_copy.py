import re
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
from app.modules.prompts.prompt_definitions import carregar_prompt_custom
import requests

ClassificationLabel = Literal["citação", "intimação", "não previsto"]

@dataclass
class ClassificationResult:
    classification: ClassificationLabel
    status: str
    method: Literal["ia_deepseek", "fallback_local"]
    confidence: float = 1.0


class DeepSeekAPIClient:
    def __init__(self, api_key: str):
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

    # No método classify_text:
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
            "max_tokens": 20  # Aumentado
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


def classificar_publicacao(texto_publicacao: str) -> str:
    """
    Classifica a publicação como 'citação' ou outro tipo com base em heurística simples.
    Pode ser substituída por um modelo LLM ou heurísticas mais refinadas.
    """
    texto = texto_publicacao.lower()
    if "fundação getúlio vargas" in texto or "fgv" in texto:
        if "citação" in texto or "réu" in texto or "autor" in texto:
            return "citação"
    return "outro"


# Exemplo de uso direto (execução manual)
if __name__ == "__main__":
    # Substitua pela sua chave de API válida
    api_key = "sua_chave_aqui"

    # Texto a ser classificado
    texto_teste = "Este texto não é de natureza jurídica e não apresenta número de processo."

    # Inicializa o classificador
    classificador = DeepSeekLegalClassifier(api_key)

    # Executa a classificação
    resultado = classificador.classify_text(texto_teste)

    # Exibe o resultado
    print("🔍 Resultado da Classificação:")
    print(f"📄 Texto: {texto_teste}")
    print(f"🏷️ Classificação: {resultado.classification}")
    print(f"⚙️ Método: {resultado.method}")
    print(f"📈 Confiança: {resultado.confidence}")
    print(f"📡 Status: {resultado.status}")
