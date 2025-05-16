'''
🛠️ Código para Identificar as Citações e Salvar em JSON
Este código:

Carrega os e-mails do JSON original
Filtra apenas os trechos onde "Fundação Getulio Vargas" ou "Carlos Ivan Simonsen Leal" são citados
Salva um novo JSON estruturado com as informações relevantes
'''

import json
import re
import os

# Caminho do JSON original
json_file_path = "F:\\FGV-SJUR\\coletaInfoJur\\emails_json\\emails_recortes.json"

# Caminho do novo JSON com as citações e números de processo
json_output_path = "F:\\FGV-SJUR\\coletaInfoJur\\emails_json\\citações_fgvcarlos.json"

# Palavras-chave a serem buscadas
keywords = ["Fundação Getulio Vargas", "Carlos Ivan Simonsen Leal"]

# Regex para identificar números de processo no padrão CNJ
processo_pattern = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}")

# Carregar os e-mails do JSON original
with open(json_file_path, "r", encoding="utf-8") as json_file:
    emails_data = json.load(json_file)

# Lista para armazenar as citações encontradas
citações = []

# Processar cada e-mail
for email in emails_data:
    corpo = email["Corpo"]

    # Procurar os números de processo no corpo do e-mail
    processos_encontrados = list(set(processo_pattern.findall(corpo)))  # Remove duplicatas

    # Procurar as palavras-chave no texto
    trechos_citados = []
    for keyword in keywords:
        matches = re.finditer(rf".{{0,100}}{re.escape(keyword)}.{{0,100}}", corpo, re.IGNORECASE)
        for match in matches:
            trechos_citados.append(match.group())

    # Se houver citações, adicionar ao JSON
    if trechos_citados:
        citações.append({
            "Data": email["Data"],
            "Assunto": email["Assunto"],
            "Remetente": email["Remetente"],
            "Citações": trechos_citados,
            "Processos": processos_encontrados if processos_encontrados else ["Nenhum encontrado"]
        })

# Salvar as citações no novo JSON
with open(json_output_path, "w", encoding="utf-8") as json_output:
    json.dump(citações, json_output, ensure_ascii=False, indent=4)

print(f"Processo concluído! Citações salvas em '{json_output_path}'")
