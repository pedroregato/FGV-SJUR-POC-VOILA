# scripts/coletar_emails_para_outputs.py

# -*- coding: utf-8 -*-
"""
Coleta e-mails do Outlook, classifica cada publicação individualmente para
identificar indícios de arquivamento e grava os resultados em arquivos
HTML (enriquecidos com metadados), JSONL e dois CSVs (recortes e publicações).

Versão refatorada para usar um classificador heurístico centralizado e
gerar saídas para a arquitetura de UI de dois níveis.
"""

import argparse
import csv
import json
import logging
import os
import shutil
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Set

# Tenta importar regex para performance, senão usa o re padrão
try:
    import regex as re
except ImportError:
    import re

# =============================================================================
# Adiciona a raiz do projeto ao sys.path para resolver os imports
# =============================================================================
try:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    from app.modules.classifiers.archival_heuristic_classifier import ArchivalHeuristicClassifier
except ImportError as e:
    print(f"ERRO CRÍTICO: Falha ao ajustar o sys.path e importar o classificador: {e}")
    print(
        "Certifique-se de que a estrutura de diretórios 'app/modules/classifiers' existe a partir da raiz do projeto.")
    sys.exit(1)

# Dependências opcionais
try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("AVISO: BeautifulSoup não encontrado. Funcionalidade de parsing HTML limitada.")

try:
    import win32com.client

    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False
    print("AVISO: pywin32 não encontrado. Funcionalidade de coleta do Outlook não disponível.")


# =============================================================================
# UTILITÁRIOS
# =============================================================================
def safe_filename(s: str, maxlen: int = 140) -> str:
    if not s: return "sem_assunto"
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen].rstrip() if len(s) > maxlen else s


def html_to_text(html: str) -> str:
    if not html: return ""
    if HAS_BS4:
        return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    else:
        return re.sub(r'<[^>]+>', ' ', html)


def resolve_store_by_displayname(display_name: str):
    if not HAS_WIN32COM: raise RuntimeError("pywin32 não está disponível.")
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    for store in namespace.Stores:
        if store.DisplayName == display_name: return store
    raise RuntimeError(f"Conta '{display_name}' não encontrada.")


def get_folder(store, folder_arg: str):
    if folder_arg.lower() in ["inbox", "caixa de entrada"]:
        return store.GetDefaultFolder(6)
    node = store.GetRootFolder()
    for part in [p for p in folder_arg.split("/") if p.strip()]:
        norm_part = unicodedata.normalize("NFKD", part.lower())
        found = next((f for f in node.Folders if unicodedata.normalize("NFKD", f.Name.lower()) == norm_part), None)
        if not found: raise RuntimeError(f"Pasta '{part}' não encontrada em '{node.FolderPath}'.")
        node = found
    return node


# =============================================================================
# LÓGICA DE PROCESSAMENTO E CLASSIFICAÇÃO
# =============================================================================
def split_html_into_publications(html_content: str) -> List[str]:
    if not html_content or not HAS_BS4: return [html_content]
    soup = BeautifulSoup(html_content, "html.parser")
    publication_tags = soup.find_all("strong", string=re.compile(r"Publicação:"))
    if not publication_tags:
        publication_tags = soup.find_all("td", string=re.compile("Publicação:"))
    if not publication_tags: return [soup.body.decode_contents() if soup.body else html_content]

    publication_tables = []
    for tag in publication_tags:
        parent_table = tag.find_parent('table')
        if parent_table and parent_table not in publication_tables:
            publication_tables.append(parent_table)

    return [str(table) for table in publication_tables] if publication_tables else [
        soup.body.decode_contents() if soup.body else html_content]


def process_and_enrich_publication(pub_html: str, pub_index: int, classifier: ArchivalHeuristicClassifier) -> Dict[
    str, Any]:
    pub_text = html_to_text(pub_html)
    cnjs_found = set(classifier.cnj_re.findall(pub_text))

    if not cnjs_found:
        classification_result = classifier._empty_result()
    else:
        classification_result = classifier.classify(pub_text)

    # Enriquecimento do HTML com metadados
    if HAS_BS4:
        soup = BeautifulSoup(pub_html, "html.parser")
        table_tag = soup.find("table")
        if table_tag:
            score = classification_result.get("score", 0)
            table_tag['data-has-indication'] = "true" if score > 0 else "false"
            table_tag['id'] = f"pub_{pub_index}"

            # Badge de score
            badge_color = "#6c757d"
            if score >= classifier.rules.get("thresholds", {}).get("forte", 0.9):
                badge_color = "#28a745"
            elif score >= classifier.rules.get("thresholds", {}).get("provavel", 0.6):
                badge_color = "#ffc107"

            score_badge_html = f"""<div style="position: absolute; top: 5px; right: 10px; padding: 4px 8px; background-color: {badge_color}; color: white; border-radius: 12px; font-size: 12px; font-weight: bold; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">Score: {score:.2f}</div>"""
            table_style = table_tag.get('style', '')
            if 'position' not in table_style:
                table_tag['style'] = f"position: relative; {table_style}"
            table_tag.insert(0, BeautifulSoup(score_badge_html, "html.parser"))
            enriched_html = str(soup)
        else:
            enriched_html = pub_html
    else:
        enriched_html = pub_html

    return {
        "cnjs": sorted(list(cnjs_found)),
        "score": classification_result["score"],
        "level": classification_result["level"],
        "matches": classification_result["matches"],
        "html_enriched": enriched_html,
        "html_content": pub_html  # HTML original da publicação para a aplicação
    }


def mailitem_to_record(mail, classifier: ArchivalHeuristicClassifier) -> dict:
    html_original = getattr(mail, "HTMLBody", "") or ""
    publications_html = split_html_into_publications(html_original)

    processed_pubs = [process_and_enrich_publication(pub_html, i, classifier) for i, pub_html in
                      enumerate(publications_html)]

    final_enriched_html = "<hr style='border-top: 2px dashed #ccc; margin: 20px 0;'>".join(
        p["html_enriched"] for p in processed_pubs)
    total_score = sum(p['score'] for p in processed_pubs)
    dt_str = datetime.fromtimestamp(time.mktime(mail.ReceivedTime.timetuple())).strftime("%Y-%m-%d_%H%M%S")

    return {
        "entry_id": mail.EntryID,
        "received": dt_str,
        "subject": mail.Subject or "",
        "total_score": round(total_score, 2),
        "html_enriched": final_enriched_html,
        "processed_publications": processed_pubs
    }


# =============================================================================
# Funções de Coleta e Geração de Arquivos
# =============================================================================
def ensure_outputs(base="outputs"):
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base, "html"), exist_ok=True)
    os.makedirs(os.path.join(base, "json"), exist_ok=True)


def reset_outputs(base="outputs"):
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)
    ensure_outputs(base)


def collect_from_folder(store, folder, limit, restrict_clause, out_base, jsonl_path, classifier):
    log = logging.getLogger(__name__)
    html_dir = os.path.join(out_base, "html")
    json_dir = os.path.join(out_base, "json")

    log.info(f"Conectado à conta: '{store.DisplayName}' | Pasta: '{folder.FolderPath}'")
    items = folder.Items
    items.Sort("[ReceivedTime]", True)

    if restrict_clause:
        log.info(f"Aplicando filtro de data: {restrict_clause}")
        items = items.Restrict(restrict_clause)

    unlimited = (limit is None) or (limit <= 0)
    denom = "∞" if unlimited else str(limit)
    count = 0
    selected_records = []

    log.info(f"Iniciando varredura de e-mails (limite: {denom})...")
    mail = items.GetFirst()
    while mail and (unlimited or count < limit):
        if hasattr(mail, "Class") and hasattr(mail, "Subject"):
            try:
                rec = mailitem_to_record(mail, classifier)
                selected_records.append(rec)
                count += 1
                log.info(f"[{count}/{denom}] Processado: {rec['subject'][:80]} | Score Agregado: {rec['total_score']}")
            except Exception as e:
                subject = getattr(mail, 'Subject', 'N/A')
                log.exception(f"Falha ao processar item com assunto '{subject}': {e}")
        mail = items.GetNext()

    log.info(f"Varredura concluída. {len(selected_records)} e-mail(s) selecionado(s).")
    if not selected_records:
        return

    log.info(f"Gravando saídas em '{out_base}'...")
    with open(jsonl_path, "w", encoding="utf-8") as jlw:
        for rec in selected_records:
            fn_base = f"{rec['received']}__{safe_filename(rec['subject'])}"
            rec['html_filename'] = f"{fn_base}.html"
            rec['json_filename'] = f"{fn_base}.json"

            try:
                with open(os.path.join(html_dir, rec['html_filename']), "w", encoding="utf-8") as f:
                    f.write(rec.get("html_enriched", ""))
                # Remove html_enriched antes de salvar o JSON para economizar espaço
                json_data = {k: v for k, v in rec.items() if k != 'html_enriched'}
                with open(os.path.join(json_dir, rec['json_filename']), "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                jlw.write(json.dumps(json_data, ensure_ascii=False) + "\n")
            except Exception as e:
                log.exception(f"Falha ao gravar arquivos para o e-mail '{rec['subject']}': {e}")


def extract_match_info(match) -> tuple[str, str]:
    """
    Extrai informações de um match de forma robusta, lidando com diferentes estruturas possíveis.
    Retorna (description, captured_text)
    """
    description = "Regra desconhecida"
    captured_text = ""

    try:
        if isinstance(match, dict):
            # Tenta diferentes chaves possíveis para a descrição
            if 'description' in match:
                description = match['description']
            elif 'rule' in match:
                description = match['rule']
            elif 'name' in match:
                description = match['name']
            elif 'id' in match:
                description = match['id']
            else:
                # Se não encontrar nenhuma chave conhecida, usa a primeira chave disponível
                if match:
                    first_key = next(iter(match.keys()))
                    description = f"{first_key}: {match[first_key]}"

            # Tenta extrair o texto capturado
            if 'match' in match:
                match_obj = match['match']
                if hasattr(match_obj, 'group'):
                    try:
                        captured_text = match_obj.group(0)
                    except:
                        captured_text = str(match_obj)
                elif isinstance(match_obj, str):
                    captured_text = match_obj
                else:
                    captured_text = str(match_obj)
            elif 'text' in match:
                captured_text = match['text']
            elif 'captured' in match:
                captured_text = match['captured']
        else:
            # Se match não for um dict, converte para string
            description = str(match)

    except Exception as e:
        # Em caso de qualquer erro, usa uma representação segura
        description = f"Erro ao processar match: {str(match)[:50]}"

    return description, captured_text


def generate_csvs_from_jsonl(jsonl_path: str, recortes_csv_path: str, publicacoes_csv_path: str):
    """
    VERSÃO CORRIGIDA: Gera os CSVs com a estrutura correta esperada pela aplicação Streamlit.
    Inclui tratamento robusto de erros para diferentes estruturas de dados.
    """
    log = logging.getLogger(__name__)
    if not os.path.exists(jsonl_path):
        log.error(f"Arquivo JSONL não encontrado: {jsonl_path}")
        return

    log.info(f"Gerando CSVs de Recortes e Publicações a partir de: {jsonl_path}")

    recortes_rows, publicacoes_rows = [], []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                email_data = json.loads(line)
                pubs_com_indicio, pubs_com_cnj = 0, 0
                all_cnjs_in_email: Set[str] = set()
                cnjs_with_indication: Set[str] = set()

                # Processa cada publicação
                for i, pub_data in enumerate(email_data.get("processed_publications", [])):
                    pub_cnjs = pub_data.get("cnjs", [])
                    if not pub_cnjs:
                        continue  # Pula publicações sem CNJ

                    all_cnjs_in_email.update(pub_cnjs)
                    pubs_com_cnj += 1

                    if pub_data.get("score", 0) > 0:
                        pubs_com_indicio += 1
                        cnjs_with_indication.update(pub_cnjs)

                    # Gera a string de hits com descrições amigáveis - VERSÃO ROBUSTA
                    friendly_hits = []
                    for match in pub_data.get("matches", []):
                        try:
                            description, captured_text = extract_match_info(match)

                            if captured_text:
                                friendly_hits.append(f"{description} (texto: \"{captured_text}\")")
                            else:
                                friendly_hits.append(description)

                        except Exception as e:
                            log.warning(f"Erro ao processar match na linha {line_num}: {e}")
                            friendly_hits.append(f"Match: {str(match)[:50]}")

                    publicacoes_rows.append({
                        "email_entry_id": email_data.get("entry_id"),
                        "publication_id": f"{email_data.get('entry_id')}_{i}",
                        "tribunal": "",  # TODO: Extrair do texto se necessário
                        "secretaria": "",  # TODO: Extrair do texto se necessário
                        "data_publicacao": "",  # TODO: Extrair do texto se necessário
                        "score": pub_data.get("score", 0),
                        "classification_level": pub_data.get("level", ""),
                        "hits": "; ".join(friendly_hits),  # CORREÇÃO: Usar ; como separador
                        "processos": ";".join(pub_cnjs),
                        "html_content": pub_data.get("html_content", ""),
                        "html_filename": email_data.get("html_filename", ""),
                    })

                # Gera a linha do recorte
                recortes_rows.append({
                    "received": email_data.get("received"),
                    "subject": email_data.get("subject"),
                    "total_score": email_data.get("total_score", 0),
                    "pubs_com_cnj": pubs_com_cnj,
                    "pubs_com_indicios": pubs_com_indicio,
                    "processos": ";".join(sorted(list(all_cnjs_in_email))),
                    "processos_com_indicios": ";".join(sorted(list(cnjs_with_indication))),
                    "entry_id": email_data.get("entry_id"),
                    "html_filename": email_data.get("html_filename", ""),
                })

            except Exception as e:
                log.exception(f"Erro ao processar linha {line_num} do JSONL: {e}")
                continue

    # Grava o CSV de recortes
    recortes_fieldnames = [
        "received", "subject", "total_score", "pubs_com_cnj", "pubs_com_indicios",
        "processos", "processos_com_indicios", "entry_id", "html_filename"
    ]
    with open(recortes_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=recortes_fieldnames, delimiter=";", extrasaction='ignore')
        writer.writeheader()
        writer.writerows(recortes_rows)

    # Grava o CSV de publicações
    publicacoes_fieldnames = [
        "email_entry_id", "publication_id", "tribunal", "secretaria", "data_publicacao",
        "score", "classification_level", "hits", "processos", "html_content", "html_filename"
    ]
    with open(publicacoes_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=publicacoes_fieldnames, delimiter=";", extrasaction='ignore')
        writer.writeheader()
        writer.writerows(publicacoes_rows)

    log.info(f"CSVs gerados com sucesso:")
    log.info(f"  - Recortes: {len(recortes_rows)} linhas em {recortes_csv_path}")
    log.info(f"  - Publicações: {len(publicacoes_rows)} linhas em {publicacoes_csv_path}")


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Coleta e-mails do Outlook e classifica publicações.")
    parser.add_argument("--account", required=True, help="Nome da conta do Outlook")
    parser.add_argument("--folder", default="Entrada", help="Nome da pasta (padrão: Entrada)")
    parser.add_argument("--days", type=int, help="Número de dias para coletar (a partir de hoje)")
    parser.add_argument("--limit", type=int, help="Limite de e-mails a processar")
    parser.add_argument("--out", default="outputs", help="Diretório de saída (padrão: outputs)")
    parser.add_argument("--reset-out", action="store_true", help="Limpa o diretório de saída antes de começar")
    parser.add_argument("--log", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Nível de log")

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log))

    # Caminhos dos arquivos de saída
    jsonl_path = os.path.join(args.out, "emails.jsonl")
    recortes_csv_path = os.path.join(args.out, "recortes.csv")
    publicacoes_csv_path = os.path.join(args.out, "publicacoes.csv")

    # Carrega o classificador
    try:
        rules_path = project_root / "app" / "modules" / "classifiers" / "archival_heuristic_rules.json"
        classifier = ArchivalHeuristicClassifier(rules_path=rules_path)
        log.info(f"Classificador carregado com sucesso de: {rules_path}")
    except Exception as e:
        log.error(f"Falha fatal ao carregar o classificador: {e}")
        sys.exit(1)

    # Conecta ao Outlook
    try:
        store = resolve_store_by_displayname(args.account)
        folder = get_folder(store, args.folder)
    except Exception as e:
        log.error(f"Falha ao conectar ao Outlook: {e}")
        sys.exit(1)

    # Prepara o diretório de saída
    if args.reset_out:
        log.info(f"Limpando diretório de saídas em '{args.out}'.")
        reset_outputs(args.out)
    else:
        ensure_outputs(args.out)

    # Prepara filtro de data
    restrict = None
    if args.days:
        start = datetime.now() - timedelta(days=args.days)
        restrict = f"[ReceivedTime] >= '{start.strftime('%m/%d/%Y %I:%M %p')}'"
        log.info(f"Coletando e-mails dos últimos {args.days} dias (desde {start.strftime('%Y-%m-%d %H:%M')})")

    # Executa a coleta
    collect_from_folder(store, folder, args.limit, restrict, args.out, jsonl_path, classifier)

    # Gera os CSVs
    generate_csvs_from_jsonl(jsonl_path, recortes_csv_path, publicacoes_csv_path)


if __name__ == "__main__":
    main()

