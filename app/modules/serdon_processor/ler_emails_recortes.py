import win32com.client
import os
import json
import re
from bs4 import BeautifulSoup  # Para processar HTML corretamente

# Conectar ao Outlook
outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

# Nome da conta e pasta correta
conta_outlook = "SJUR Coleta Serdon"
account_folder = outlook.Folders[conta_outlook]
inbox = account_folder.Folders["Inbox"]  # Acessa a Inbox

# Obter os e-mails
messages = inbox.Items
messages.Sort("[ReceivedTime]", True)  # Ordena do mais recente para o mais antigo

print(f"Total de e-mails encontrados: {messages.Count}")

# Definir a pasta de destino para o JSON
pasta_json = "F:\\FGV-SJUR\\coletaInfoJur\\emails_json"
os.makedirs(pasta_json, exist_ok=True)

# Expressões regulares para extração de dados
processo_pattern = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}")
tribunal_pattern = re.compile(r"Tribunal:\s*(.*?)\s*(?:\n|$)")
secretaria_pattern = re.compile(r"Secretaria:\s*(.*?)\s*(?:\n|$)")
data_publicacao_pattern = re.compile(r"Data de Publicação:\s*(\d{2}/\d{2}/\d{4})")
advogados_pattern = re.compile(r"Advogado:\s*(.+?)-\s*OAB")
nome_pesquisado_pattern = re.compile(r"Nome Pesquisado:\s*(.*?)\s*(?:\n|$)")
publicacao_pattern = re.compile(r"Publicação:\s*(.*?)\s*(?=(Nome Pesquisado:|$))", re.DOTALL)

# Lista para consolidar os dados no JSON
emails_data = []


def extrair_texto_html(html):
    """Remove tags HTML e retorna texto puro."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ").strip()


def extrair_dados_escritorio(texto):
    """Extrai os dados do escritório, que aparecem uma única vez por e-mail."""
    escritorio_match = re.search(r"Escritório:\s*(.*?)\s*(?:\n|$)", texto)
    codigo_match = re.search(r"Código:\s*(\d+)", texto)
    area_match = re.search(r"Área:\s*(\d+)", texto)
    jornal_match = re.search(r"Jornal:\s*(.*?)\s*(?:\n|$)", texto)
    data_disponibilizacao_match = re.search(r"Data de Disponibilização:\s*(\d{2}/\d{2}/\d{4})", texto)

    return {
        "escritorio": escritorio_match.group(1).strip() if escritorio_match else "",
        "codigo": codigo_match.group(1).strip() if codigo_match else "",
        "area": area_match.group(1).strip() if area_match else "",
        "jornal": jornal_match.group(1).strip() if jornal_match else "",
        "data_disponibilizacao": data_disponibilizacao_match.group(1).strip() if data_disponibilizacao_match else ""
    }


def extrair_publicacoes(texto):
    """Extrai todas as publicações dentro do e-mail."""
    publicacoes = []

    # Separar as publicações pelo marcador "Resultado da Pesquisa"
    partes = texto.split("Resultado da Pesquisa")[1:] if "Resultado da Pesquisa" in texto else []

    for parte in partes:
        nome_pesquisado = nome_pesquisado_pattern.search(parte)
        tribunal = tribunal_pattern.search(parte)
        secretaria = secretaria_pattern.search(parte)
        data_publicacao = data_publicacao_pattern.search(parte)
        processos = list(set(processo_pattern.findall(parte)))  # Remove duplicatas
        advogados = list(set(advogados_pattern.findall(parte)))  # Remove duplicatas
        publicacao_conteudo = publicacao_pattern.search(parte)

        publicacoes.append({
            "nome_pesquisado": nome_pesquisado.group(1).strip() if nome_pesquisado else "",
            "tribunal": tribunal.group(1).strip() if tribunal else "",
            "secretaria": secretaria.group(1).strip() if secretaria else "",
            "data_publicacao": data_publicacao.group(1).strip() if data_publicacao else "",
            "processos": processos,
            "advogados": advogados,
            "conteudo": publicacao_conteudo.group(1).strip() if publicacao_conteudo else parte.strip()
        })

    return publicacoes


# Processar os e-mails e salvar como JSON
for message in messages:
    try:
        # Criar identificadores básicos
        data_email = message.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S")

        # Capturar o corpo do e-mail e remover HTML
        try:
            body = message.Body
            body_html = message.HTMLBody
            body_final = extrair_texto_html(body_html) if len(body_html) > len(body) else body
        except Exception:
            body_final = message.Body  # Se falhar, pega apenas o texto puro

        # Extrair dados estruturados
        dados_escritorio = extrair_dados_escritorio(body_final)
        publicacoes = extrair_publicacoes(body_final)

        # Criar estrutura do JSON
        email_info = {
            "data_recebimento": data_email,
            "assunto": message.Subject,
            "remetente": message.SenderEmailAddress,
            "dados_escritorio": dados_escritorio,
            "publicacoes": publicacoes
        }

        emails_data.append(email_info)
        print(f"Processado: {message.Subject}")

    except Exception as e:
        print(f"Erro ao processar e-mail: {e}")

# Salvar o JSON consolidado
caminho_json = os.path.join(pasta_json, "emails_recortes.json")
with open(caminho_json, "w", encoding="utf-8") as json_file:
    json.dump(emails_data, json_file, ensure_ascii=False, indent=4)

print(f"Processo concluído! JSON salvo em {caminho_json}.")
