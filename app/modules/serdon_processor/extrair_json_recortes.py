# extrair_json_recortes.py

import os
import re
import json
from typing import Optional
from bs4 import BeautifulSoup
from pathlib import Path


def extract_processos(publicacao: str) -> list[str]:
    processo_pattern = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{4}\b")
    encontrados = processo_pattern.findall(publicacao)
    return list(set(encontrados))


def parse_email_html(html: str) -> tuple[dict, list[dict], str]:
    soup = BeautifulSoup(html, 'html.parser')
    tabelas = soup.find_all('table')

    campos = {
        "escritorio": ["Escritório", "Escritorio"],
        "codigo": ["Código", "Codigo"],
        "area": ["Área", "Area"],
        "jornal": ["Jornal", "Jornais"],
        "data_disponibilizacao": ["Data de Disponibilização", "Data"]
    }
    dados_escritorio = {key: None for key in campos.keys()}

    for tabela in tabelas:
        linhas = tabela.find_all("tr")
        for row in linhas:
            cols = row.find_all("td")
            if len(cols) >= 2:
                chave_raw = cols[0].get_text(separator=" ", strip=True).replace(":", "")
                valor = cols[1].get_text(separator=" ", strip=True)
                for campo, alternativas in campos.items():
                    if any(chave_raw.lower() == alt.lower() for alt in alternativas):
                        dados_escritorio[campo] = valor

    pesquisas = []
    tabelas_pesquisa = [t for t in tabelas if t.find("td") and "nome pesquisado" in t.find("td").get_text(strip=True).lower()]
    texto_total_extraido = ""

    for tabela in tabelas_pesquisa:
        pesquisa = {
            "nome_pesquisado": "",
            "tribunal": "",
            "secretaria": "",
            "data_publicacao": "",
            "publicacao": "",
            "processos": []
        }
        texto_publicacao = ""

        linhas = tabela.find_all("tr")
        for row in linhas:
            cols = row.find_all("td")
            if len(cols) >= 2:
                chave = cols[0].get_text(strip=True).lower()
                valor = cols[1].get_text(separator=" ", strip=True)
                if "nome pesquisado" in chave:
                    pesquisa["nome_pesquisado"] = valor
                elif "tribunal" in chave:
                    pesquisa["tribunal"] = valor
                elif "secretaria" in chave:
                    pesquisa["secretaria"] = valor
                elif "data de publica" in chave:
                    pesquisa["data_publicacao"] = valor
                elif "publicacao" in chave or "publicação" in chave:
                    texto_publicacao += valor + "\n"
            elif len(cols) == 1:
                celula = cols[0].get_text(separator=" ", strip=True)
                if celula.strip():
                    texto_publicacao += celula + "\n"

        pesquisa["publicacao"] = texto_publicacao.strip()
        pesquisa["processos"] = extract_processos(texto_publicacao)
        pesquisas.append(pesquisa)
        texto_total_extraido += texto_publicacao + "\n"

    return dados_escritorio, pesquisas, texto_total_extraido.strip()


def gerar_json_do_email(email_obj, pasta_html: Path, pasta_json: Path) -> Optional[Path]:
    data_email = email_obj.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S")
    message_id = email_obj.EntryID
    subject = email_obj.Subject or "(sem assunto)"
    remetente = email_obj.SenderEmailAddress

    try:
        html_body = email_obj.HTMLBody
    except Exception:
        html_body = email_obj.Body

    pasta_html.mkdir(parents=True, exist_ok=True)
    pasta_json.mkdir(parents=True, exist_ok=True)

    data_email_formatado = data_email.replace(":", "").replace(" ", "_")
    nome_arquivo_safe = re.sub(r"[^\w\-]", "_", subject)[:50]
    nome_base = f"{data_email_formatado}_{nome_arquivo_safe}"

    caminho_html = pasta_html / f"{nome_base}.html"
    with open(caminho_html, "w", encoding="utf-8") as f:
        f.write(html_body)

    dados_escritorio, pesquisas, texto_extraido = parse_email_html(html_body)

    caminho_txt = pasta_html / f"{nome_base}.txt"
    with open(caminho_txt, "w", encoding="utf-8") as f:
        f.write(texto_extraido)

    if pesquisas:
        email_info = {
            "data_recebimento": data_email,
            "assunto": subject,
            "remetente": remetente,
            "message_id": message_id,
            "dados_escritorio": dados_escritorio,
            "pesquisas": pesquisas
        }

        caminho_json = pasta_json / f"{message_id}.json"
        with open(caminho_json, "w", encoding="utf-8") as json_file:
            json.dump(email_info, json_file, ensure_ascii=False, indent=4)
        return caminho_json

    return None
