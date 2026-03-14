import requests
import json
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Recupera a chave da API
api_key = os.getenv("SERPER_API_KEY")

if not api_key:
    raise ValueError("A variável SERPER_API_KEY não foi encontrada no arquivo .env")

url = "https://google.serper.dev/search"

payload = json.dumps({
    "q": 'site:in.gov.br "Fundação Getúlio Vargas"',
    "tbs": "qdr:d",  # Filtro para as últimas 24 horas
    "gl": "br",  # Busca baseada no Brasil
    "hl": "pt-br"  # Idioma em Português
})

headers = {
    'X-API-KEY': api_key,
    'Content-Type': 'application/json'
}

try:
    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()  # Verifica se houve erro na requisição (ex: 403, 500)

    results = response.json()

    # Verifica se existem resultados orgânicos
    if 'organic' in results and results['organic']:
        print(f"--- Menções encontradas nas últimas 24h ---\n")
        for result in results.get('organic', []):
            print(f"Título: {result.get('title')}")
            print(f"Link: {result.get('link')}\n")
    else:
        print("Nenhuma menção nova encontrada no Diário Oficial nas últimas 24 horas.")

except requests.exceptions.RequestException as e:
    print(f"Erro ao conectar com a API: {e}")