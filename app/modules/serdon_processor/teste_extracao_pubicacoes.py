from bs4 import BeautifulSoup
import re

# Carrega o HTML de um arquivo para teste isolado
caminho_html = "F:\\FGV-SJUR\\coletaInfoJur\\emails_html\\~tmEDAE.html"

with open(caminho_html, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
tabelas = soup.find_all("table")

# Encontrar todas as tabelas de publicacoes
publicacoes = []

for tabela in tabelas:
    linhas = tabela.find_all("tr")
    if not linhas:
        continue

    primeira_celula = linhas[0].find("td")
    if not primeira_celula:
        continue

    if "nome pesquisado" in primeira_celula.get_text(strip=True).lower():
        publicacao = {
            "nome_pesquisado": "",
            "tribunal": "",
            "secretaria": "",
            "data_publicacao": "",
            "publicacao": ""
        }
        texto_publicacao = ""

        for row in linhas:
            cols = row.find_all("td")
            if len(cols) == 2:
                chave = cols[0].get_text(strip=True).lower()
                valor = cols[1].get_text(separator=" ", strip=True)

                if "nome pesquisado" in chave:
                    publicacao["nome_pesquisado"] = valor
                elif "tribunal" in chave:
                    publicacao["tribunal"] = valor
                elif "secretaria" in chave:
                    publicacao["secretaria"] = valor
                elif "data de publica" in chave:
                    publicacao["data_publicacao"] = valor
                elif "publicação" in chave or "publicacao" in chave:
                    texto_publicacao += valor + "\n"
            elif len(cols) == 1:
                texto_publicacao += cols[0].get_text(separator=" ", strip=True) + "\n"

        publicacao["publicacao"] = texto_publicacao.strip()
        publicacoes.append(publicacao)

# Exibir resultado
for i, pub in enumerate(publicacoes):
    print(f"\n[Publicacao {i+1}]:")
    for chave, valor in pub.items():
        print(f"  {chave}: {valor}")
