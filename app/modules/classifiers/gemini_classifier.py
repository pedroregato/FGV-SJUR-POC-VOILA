import re
import requests
from dataclasses import dataclass
from typing import Optional, Tuple
from app.modules.prompts.prompt_definitions import carregar_prompt_custom

@dataclass
class ClassificationResult:
    classification: str  # "citação", "intimação" ou "não previsto"
    status: str          # "sucesso" ou mensagem de erro
    method: str          # "ia_gemini-flash"
    confidence: float = 1.0


class GeminiAPIClient:
    def __init__(self, api_key: str = None):

        if not api_key:
            self.api_key = os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                print("❌ A variável GOOGLE_API_KEY não foi encontrada no .env ou no ambiente.")
                exit(1)
        else: self.api_key = api_key

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
    def __init__(self, api_key: str=None):

        if not api_key:
            self.api_key = os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                print("❌ A variável GOOGLE_API_KEY não foi encontrada no .env ou no ambiente.")
                exit(1)
        else: self.api_key = api_key

        self.api_client = GeminiAPIClient(self.api_key)
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

    texto_teste = """
    Publicacao Processo: 5092956-64.2025.8.13.0024 Orgao: 3ª Unidade Jurisdicional da Fazenda Publica do Juizado Especial 35º JD Belo Horizonte Data de disponibilizacao: 13/05/2025 Tipo de comunicacao: Intimacao Meio: Diario de Justica Eletronico Nacional Inteiro teor: https://pje.tjmg.jus.br:443/pje/Processo/ConsultaDocumento/listView.seam?x=25051210415004000010443411472 Parte: EMANUEL THAELYSON GOMES DANTAS Advogado: JULIO MARQUES DA SILVA NETO - OAB RN-20531 Conteudo: PODER JUDICIARIO DO ESTADO DE MINAS GERAIS Justica de Primeira Instancia Comarca de Belo Horizonte / 3ª Unidade Jurisdicional da Fazenda Publica do Juizado Especial 35º JD Belo Horizonte Avenida Francisco Sales, 1446, Santa Efigenia, Belo Horizonte - MG - CEP: 30150-224 PROCESSO Nº: 5092956-64.2025.8.13.0024 CLASSE: [CIVEL] PROCEDIMENTO DO JUIZADO ESPECIAL DA FAZENDA PUBLICA (14695) REQUERENTE: EMANUEL THAELYSON GOMES DANTAS CPF: 017.458.584-58 REQUERIDO(A): ESTADO DE MINAS GERAIS CPF: 18.715.615/0001-60 REQUERIDO(A): FUNDACAO GETULIO VARGAS CPF: 33.641.663/0001-44 CERTIDAO Fica a parte re, acima qualificada, CITADA para todos termos da acao judicial contra ela proposta pela parte promovente, conforme peticao inicial, advertindo-se o requerido de que devera apresentar contestacao ate a data da audiencia designada. Ficam as partes INTIMADAS, para ciencia da decisao retro e para ACESSAREM A AUDIENCIA VIRTUAL DE CONCILIACAO a ser realizada por VIDEOCONFERENCIA por meio da plataforma CNJ WEBEX.COM, designada conforme abaixo: Tipo: Conciliacao (12740) Sala: https://x.gd/nSiHp (REUNIAO:23432680925)M/LARAN-24 Data/Hora: 20/07/26 09:00. Senha para acesso: 1234. O nao comparecimento ou a recusa da parte de participar da audiencia de conciliacao virtual podera ensejar a aplicacao de contumacia ou revelia, conforme o caso. As partes e seus advogados deverao se identificar na audiencia de conciliacao com exibicao de documento oficial de identidade com foto. O acesso a sala de audiencia virtual pela parte autora e pela parte re e OBRIGATORIO, devendo as partes e seus procuradores participar da audiencia de conciliacao virtual, em data e horario supramencionados. Os procuradores ficam encarregados de dar ciencia aos seus respectivos clientes encaminhando o link da audiencia. Belo Horizonte, 12 de maio de 2025. DENISE MENDES NOGUEIRA Servidor(a) e Retificador(a) |comunicacao_id: 268952877|
    """

    classificador = GeminiLegalClassifier(api_key)

    print("🚀 Enviando para Gemini...")
    resultado = classificador.classify_text(texto_teste)

    print("\n🔍 Resultado da Classificação:")
    print(f"📄 Texto: {texto_teste}")
    print(f"🏷️ Classificação: {resultado.classification}")
    print(f"⚙️ Método: {resultado.method}")
    print(f"📈 Confiança: {resultado.confidence}")
    print(f"📡 Status: {resultado.status}")
