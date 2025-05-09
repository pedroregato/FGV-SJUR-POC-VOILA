import re
import requests
from dataclasses import dataclass
from typing import Optional, Tuple
from ..prompts.prompt_definitions import carregar_prompt_custom

@dataclass
class ClassificationResult:
    classification: str  # "citação", "intimação" ou "não previsto"
    status: str          # "sucesso" ou mensagem de erro
    method: str          # "ia_gemini-flash"
    confidence: float = 1.0


class GeminiAPIClient:
    def __init__(self, api_key: str):
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        self.headers = {
            "Content-Type": "application/json"
        }

    def make_request(self, prompt: str, timeout: int = 10) -> Tuple[Optional[dict], Optional[str]]:
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }
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


class GeminiLegalClassifier:
    def __init__(self, api_key: str):
        self.api_client = GeminiAPIClient(api_key)
        self.classifier_type = "gemini-2.0-flash"
        self.system_prompt = carregar_prompt_custom()

    def classify_text(self, text: str) -> ClassificationResult:
        full_prompt = f"{self.system_prompt}\n\nTexto:\n{text}"

        print("🟦 Enviando prompt para Gemini:")
        print("=" * 60)
        print(full_prompt)
        print("=" * 60)

        api_response, error = self.api_client.make_request(full_prompt)

        if error:
            print("❌ Erro na chamada da API Gemini:")
            print(error)
            return ClassificationResult("não previsto", f"erro: {error}", "fallback_local")

        print("🟩 Resposta bruta recebida da API Gemini:")
        print("=" * 60)
        import json
        print(json.dumps(api_response, indent=2, ensure_ascii=False))
        print("=" * 60)

        try:
            candidates = api_response.get("candidates")
            if not candidates or "content" not in candidates[0]:
                raise ValueError("Estrutura 'candidates[0].content' ausente")

            parts = candidates[0]["content"].get("parts")
            if not parts or "text" not in parts[0]:
                raise ValueError("Estrutura 'parts[0].text' ausente")

            result = parts[0]["text"].strip().lower()
            print(f"🔎 Resultado interpretado da LLM: '{result}'")

            if result in ("citação", "intimação", "não previsto"):
                return ClassificationResult(result, "sucesso", "ia_gemini-flash")
            else:
                return ClassificationResult("não previsto", f"erro: resposta inesperada ('{result}')", "fallback_local")

        except Exception as e:
            print("❗ Erro ao interpretar a resposta da LLM Gemini:")
            print(str(e))
            return ClassificationResult("não previsto", f"erro: parsing ({str(e)})", "fallback_local")


# Exemplo de uso direto (execução manual)
# Exemplo de uso direto (execução manual)
if __name__ == "__main__":
    import os
    import json
    from dotenv import load_dotenv

    # Carrega as variáveis do .env
    load_dotenv()

    # Recupera a chave da API
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("❌ GOOGLE_API_KEY não encontrada no arquivo .env!")
        exit(1)

    texto_teste = "Este texto não é de natureza jurídica e não apresenta número de processo."

    classificador = GeminiLegalClassifier(api_key)

    print("🚀 Enviando para Gemini...")
    resultado = classificador.classify_text(texto_teste)

    print("\n🔍 Resultado da Classificação:")
    print(f"📄 Texto: {texto_teste}")
    print(f"🏷️ Classificação: {resultado.classification}")
    print(f"⚙️ Método: {resultado.method}")
    print(f"📈 Confiança: {resultado.confidence}")
    print(f"📡 Status: {resultado.status}")
