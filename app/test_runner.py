
import os
from dotenv import load_dotenv
from datetime import datetime
from modules.classifiers.gemini_classifier import GeminiLegalClassifier
from modules.classifiers.gpt35_classifier import GPT35LegalClassifier
from modules.classifiers.deepseek_classifier import DeepSeekLegalClassifier

load_dotenv()

texto_teste = """MANDADO DE SEGURANÇA. A candidata foi excluída de concurso público por não comparecer à etapa de heteroidentificação. Ela argumenta que foi impedida por coincidência de datas e já foi reconhecida como negra anteriormente. Pede reintegração à lista de ampla concorrência e continuidade no certame."""

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

classificadores = []

if GOOGLE_API_KEY:
    classificadores.append(("Gemini", GeminiLegalClassifier(GOOGLE_API_KEY)))
else:
    print("⚠️ GOOGLE_API_KEY não encontrada no .env")

if OPENAI_API_KEY:
    classificadores.append(("GPT-3.5", GPT35LegalClassifier(OPENAI_API_KEY)))
else:
    print("⚠️ OPENAI_API_KEY não encontrada no .env")

if DEEPSEEK_API_KEY:
    classificadores.append(("DeepSeek", DeepSeekLegalClassifier(DEEPSEEK_API_KEY)))
else:
    print("⚠️ DEEPSEEK_API_KEY não encontrada no .env")

print(f"\n📄 Texto a ser classificado:\n{texto_teste}\n")

for nome, classificador in classificadores:
    print(f"🧠 [{nome}] Executando em {datetime.now().isoformat(timespec='seconds')}")
    try:
        resultado = classificador.classify_text(texto_teste)
        print(f"🏷️ Classificação: {resultado.classification}")
        print(f"⚙️ Método: {resultado.method}")
        print(f"📡 Status: {resultado.status}")
        print(f"📈 Confiança: {resultado.confidence}")
    except Exception as e:
        print(f"❌ Erro inesperado em {nome}: {str(e)}")
    print("-" * 60)
