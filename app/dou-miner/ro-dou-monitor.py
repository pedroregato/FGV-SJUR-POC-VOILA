import requests
import json
from datetime import datetime


def minerar_dou_resolutivo(termo):
    print(f"--- Minerando DOU (Dados Abertos/API) ---")
    hoje = datetime.now().strftime('%d/%m/%Y')

    # URL da API de busca que o portal consome via JavaScript
    url = "https://www.in.gov.br/consulta/-/google_search/search"

    params = {
        'q': f'"{termo}"',
        'date': hoje,
        'exactPhrase': termo,
        'sort': 'date:D:L:d1'
    }

    # Headers para simular que somos o sistema interno do portal
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://www.in.gov.br/consulta'
    }

    try:
        response = requests.get(url, params=params, headers=headers)

        # Se o portal retornar HTML, o 'requests' pode não capturar os dados dinâmicos.
        # Caso a busca retorne resultados, o título da página ou os links estarão no texto.

        # A lógica definitiva: procurar o padrão de link de matérias reais no texto retornado
        import re
        links_materias = re.findall(r'href="(https://www\.in\.gov\.br/web/dou/-/.*?)"', response.text)

        # Remove duplicatas
        links_materias = list(set(links_materias))

        if links_materias:
            print(f"[SUCESSO] Encontradas {len(links_materias)} matérias para '{termo}'!")
            for i, link in enumerate(links_materias, 1):
                print(f"  {i}. {link}")
        else:
            print(f"[AVISO] Termo '{termo}' não localizado nas matérias de hoje ({hoje}).")

    except Exception as e:
        print(f"[ERRO] Falha: {e}")


# Execução
minerar_dou_resolutivo("educação infantil")