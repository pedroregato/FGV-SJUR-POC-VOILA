import requests
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("F:\FGV-SJUR\sjur-poc-voila\.env"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Classifique este texto juridicamente: 'MANDADO DE SEGURANÇA...'"}]
}
response = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)
print(response.json())