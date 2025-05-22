import io
import re
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
from app.modules.prompts.prompt_definitions import carregar_prompt_custom
from llama_cpp import Llama

try:
    from llama_cpp import Llama
except ImportError:
    print("⚠️ Para a POC que estamos realizando vamos ignorar a utilização de llama_cpp no Dockerfile.")


ClassificationLabel = Literal["citação", "intimação", "não previsto"]

@dataclass
class ClassificationResult:
    classification: ClassificationLabel
    status: str
    method: Literal["ia_llama", "fallback_local"]
    confidence: float = 1.0


class LlamaLocalClassifier:
    def __init__(self, model_path: str, n_ctx: int = 2000, n_threads: int = 4):
        # Redireciona as mensagens para o vazio durante o carregamento
        fnull = io.StringIO()
        with redirect_stdout(fnull), redirect_stderr(fnull):
            self.llm = Llama(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads)


        self.system_prompt = carregar_prompt_custom()
        self.classifier_type = "llama"

    def classify_text(self, text: str) -> ClassificationResult:
        if not text.strip():
            return ClassificationResult("não previsto", "erro: texto vazio", "fallback_local")

        prompt = f"{self.system_prompt}\n\nUsuário: {text}\nResposta:"
        try:
            response = self.llm(prompt, max_tokens=20, temperature=0.0)
            result = response["choices"][0]["text"].strip().lower()
            if result in ("citação", "intimação", "não previsto"):
                return ClassificationResult(result, "sucesso", "ia_llama")
            return ClassificationResult("não previsto", "erro: resposta inválida", "fallback_local")
        except Exception as e:
            return ClassificationResult("não previsto", f"erro: {str(e)}", "fallback_local")

from dotenv import load_dotenv
import os
# Exemplo de uso direto (execução manual)
# Carregar variáveis do .env
load_dotenv()
if __name__ == "__main__":
    model_path = os.getenv("LLAMA_MODEL_PATH")
    print("📁 Caminho recebido:", model_path)
    print("✅ Arquivo existe?", os.path.isfile(model_path))

    texto_teste = """
    Publicacao Processo: 5092956-64.2025.8.13.0024 Orgao: 3ª Unidade Jurisdicional da Fazenda Publica do Juizado Especial 35º JD Belo Horizonte Data de disponibilizacao: 13/05/2025 Tipo de comunicacao: Intimacao Meio: Diario de Justica Eletronico Nacional Inteiro teor: https://pje.tjmg.jus.br:443/pje/Processo/ConsultaDocumento/listView.seam?x=25051210415004000010443411472 Parte: EMANUEL THAELYSON GOMES DANTAS Advogado: JULIO MARQUES DA SILVA NETO - OAB RN-20531 Conteudo: PODER JUDICIARIO DO ESTADO DE MINAS GERAIS Justica de Primeira Instancia Comarca de Belo Horizonte / 3ª Unidade Jurisdicional da Fazenda Publica do Juizado Especial 35º JD Belo Horizonte Avenida Francisco Sales, 1446, Santa Efigenia, Belo Horizonte - MG - CEP: 30150-224 PROCESSO Nº: 5092956-64.2025.8.13.0024 CLASSE: [CIVEL] PROCEDIMENTO DO JUIZADO ESPECIAL DA FAZENDA PUBLICA (14695) REQUERENTE: EMANUEL THAELYSON GOMES DANTAS CPF: 017.458.584-58 REQUERIDO(A): ESTADO DE MINAS GERAIS CPF: 18.715.615/0001-60 REQUERIDO(A): FUNDACAO GETULIO VARGAS CPF: 33.641.663/0001-44 CERTIDAO Fica a parte re, acima qualificada, CITADA para todos termos da acao judicial contra ela proposta pela parte promovente, conforme peticao inicial, advertindo-se o requerido de que devera apresentar contestacao ate a data da audiencia designada. Ficam as partes INTIMADAS, para ciencia da decisao retro e para ACESSAREM A AUDIENCIA VIRTUAL DE CONCILIACAO a ser realizada por VIDEOCONFERENCIA por meio da plataforma CNJ WEBEX.COM, designada conforme abaixo: Tipo: Conciliacao (12740) Sala: https://x.gd/nSiHp (REUNIAO:23432680925)M/LARAN-24 Data/Hora: 20/07/26 09:00. Senha para acesso: 1234. O nao comparecimento ou a recusa da parte de participar da audiencia de conciliacao virtual podera ensejar a aplicacao de contumacia ou revelia, conforme o caso. As partes e seus advogados deverao se identificar na audiencia de conciliacao com exibicao de documento oficial de identidade com foto. O acesso a sala de audiencia virtual pela parte autora e pela parte re e OBRIGATORIO, devendo as partes e seus procuradores participar da audiencia de conciliacao virtual, em data e horario supramencionados. Os procuradores ficam encarregados de dar ciencia aos seus respectivos clientes encaminhando o link da audiencia. Belo Horizonte, 12 de maio de 2025. DENISE MENDES NOGUEIRA Servidor(a) e Retificador(a) |comunicacao_id: 268952877|
    """

    classificador = LlamaLocalClassifier(model_path=model_path)
    resultado = classificador.classify_text(texto_teste)

    print("🔍 Resultado da Classificação:")
    print(f"📄 Texto: {texto_teste}")
    print(f"🏷️ Classificação: {resultado.classification}")
    print(f"⚙️ Método: {resultado.method}")
    print(f"📈 Confiança: {resultado.confidence}")
    print(f"📡 Status: {resultado.status}")
