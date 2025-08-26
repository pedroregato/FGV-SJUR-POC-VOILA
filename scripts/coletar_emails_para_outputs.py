# -*- coding: utf-8 -*-
"""
Coleta N e-mails do Outlook e grava HTML/JSON/JSONL/CSV em outputs/.
(Versão Refatorada para Análise por Publicação Individual)

Modos:
  - all      : varre todos os e-mails e reinicia as saídas
  - range    : varre por período (--date-from/--date-to em YYYY-MM-DD)
  - today    : apenas e-mails de hoje
  - csv-only : só (re)gera o CSV a partir do JSON(L) existente
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
from typing import List, Dict, Set

try:
    import regex as re
except Exception:
    import re

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

try:
    import win32com.client
    import pythoncom

    HAS_PYWIN32 = True
except Exception:
    HAS_PYWIN32 = False

# ======================
# Config / Léxico / Regex
# ======================
LEXICON_ARQ_WEIGHTS: Dict[str, int] = {
    "arquivamento": 3, "arquivado": 3, "arquivar": 3, "baixa": 2,
    "baixado": 2, "trânsito em julgado": 3, "transito em julgado": 3,
    "tjulg": 2, "extinção do processo": 2, "extinto o processo": 2,
    "extinção": 1, "preclusão": 1, "encerramento": 1, "desarquivamento": -2,
}

CNJ_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
POSITIVE_LEXICON_TERMS = {term for term, weight in LEXICON_ARQ_WEIGHTS.items() if weight > 0}


# ======================
# Utils
# ======================
def setup_logging(level: str):
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        format="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")


def normalize_simple(s: str) -> str:
    if s is None: return ""
    return unicodedata.normalize("NFKD", str(s)).encode("ASCII", "ignore").decode("ASCII").lower()


def html_to_text(html: str) -> str:
    if not html: return ""
    if HAS_BS4:
        return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    return re.sub(r"<[^>]+>", " ", html).strip()


def safe_filename(s: str, maxlen: int = 140) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "_", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return (s[:maxlen].rstrip() if len(s) > maxlen else s) or "sem_assunto"


# ======================
# Outlook helpers
# ======================
OL_FOLDER_INBOX = 6


def get_namespace():
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")


def resolve_store_by_displayname(account_name: str):
    mapi = get_namespace()
    target_norm = normalize_simple(account_name)
    for store in mapi.Stores:
        if normalize_simple(store.DisplayName) == target_norm: return store
    for store in mapi.Stores:
        if target_norm in normalize_simple(store.DisplayName): return store
    raise RuntimeError(f"Conta '{account_name}' não encontrada. Disponíveis: {[s.DisplayName for s in mapi.Stores]}")


def get_folder(store, folder_arg: str):
    if not folder_arg or normalize_simple(folder_arg) in ("inbox", "caixa de entrada", "entrada"):
        return store.GetDefaultFolder(OL_FOLDER_INBOX)
    node = store.GetRootFolder()
    for part in [p for p in folder_arg.split("/") if p.strip()]:
        node = next((f for f in node.Folders if normalize_simple(f.Name) == normalize_simple(part)), None)
        if not node: raise RuntimeError(f"Pasta '{folder_arg}' não encontrada.")
    return node


# =============================================================================
# LÓGICA DE PROCESSAMENTO CORRIGIDA
# =============================================================================
def split_html_into_publications(html_content: str) -> List[str]:
    """
    Divide o HTML de um recorte em uma lista de publicações individuais.
    A heurística aprimorada busca por tabelas que contenham o campo 'Publicação:'.
    """
    if not html_content or not HAS_BS4:
        return [html_content]

    soup = BeautifulSoup(html_content, "html.parser")

    # NOVA HEURÍSTICA: Encontra todas as tags <strong> com o texto "Publicação:"
    # e retorna a tabela (<table>) que as contém.
    publication_tags = soup.find_all("strong", string=re.compile(r"Publicação:"))

    if not publication_tags:
        # Fallback se a primeira heurística falhar
        publication_tags = soup.find_all("td", string=re.compile("Publicação:"))

    if not publication_tags:
        logging.debug(
            "Nenhum delimitador de publicação ('Publicação:') encontrado. Analisando o HTML como um bloco único.")
        body_content = soup.body.decode_contents() if soup.body else html_content
        return [body_content]

    # Usamos um set para evitar duplicatas se uma tabela tiver múltiplos marcadores
    publication_tables = set()
    for tag in publication_tags:
        # .find_parent('table') sobe na árvore DOM até encontrar a tabela que contém a tag
        parent_table = tag.find_parent('table')
        if parent_table:
            publication_tables.add(parent_table)

    if not publication_tables:
        logging.debug("Encontrado o texto 'Publicação:', mas não dentro de uma tabela. Analisando como bloco único.")
        return [soup.body.decode_contents() if soup.body else html_content]

    return [str(table) for table in publication_tables]


def process_publication(pub_html: str) -> Dict:
    """
    Processa uma única publicação (HTML) e retorna seus dados analisados.
    """
    pub_text = html_to_text(pub_html)
    pub_text_norm = normalize_simple(pub_text)

    cnjs_found: Set[str] = set(CNJ_RE.findall(pub_text))
    hits_found: Set[str] = {term for term in LEXICON_ARQ_WEIGHTS if term in pub_text_norm}
    score = sum(LEXICON_ARQ_WEIGHTS[term] for term in hits_found)

    has_positive_indication = any(p_term in pub_text_norm for p_term in POSITIVE_LEXICON_TERMS)

    cnjs_with_indication: Set[str] = cnjs_found if has_positive_indication and score > 0 else set()

    return {
        "cnjs": sorted(list(cnjs_found)),
        "cnjs_with_indication": sorted(list(cnjs_with_indication)),
        "score": score,
        "hits": sorted(list(hits_found))
    }


# Dentro de coletar_emails_para_outputs.py

def mailitem_to_record(mail) -> dict:
    """
    Processa um e-mail (recorte), analisando cada publicação individualmente
    e agregando os resultados.
    """
    # ... (código existente para extrair subject, sender, etc.)
    html = getattr(mail, "HTMLBody", "") or ""

    # 1. Divide o recorte em publicações
    publications_html = split_html_into_publications(html)

    # 2. Processa cada publicação
    processed_pubs = []
    for pub_html in publications_html:
        # A função process_publication já retorna um dict com score, hits, etc.
        pub_data = process_publication(pub_html)
        pub_data['html'] = pub_html  # Adiciona o HTML da publicação ao seu dict
        processed_pubs.append(pub_data)

    # 3. Agrega os resultados (lógica existente)
    total_score = 0
    all_cnjs = set()
    all_cnjs_with_indication = set()
    all_hits = set()

    for pub_data in processed_pubs:
        total_score += pub_data["score"]
        all_cnjs.update(pub_data["cnjs"])
        all_cnjs_with_indication.update(pub_data["cnjs_with_indication"])
        all_hits.update(pub_data["hits"])

    hits_str = ",".join(f"{LEXICON_ARQ_WEIGHTS[term]:+d}:{term}" for term in sorted(list(all_hits)))
    dt_str = datetime.fromtimestamp(time.mktime(mail.ReceivedTime.timetuple())).strftime("%Y-%m-%d_%H%M%S")
    fn_base = f"{dt_str}__{safe_filename(mail.Subject or '')}"

    return {
        "entry_id": mail.EntryID,
        "received": dt_str,
        "subject": mail.Subject or "",
        "sender": getattr(getattr(mail, "Sender", None), "Address", None) or getattr(mail, "SenderEmailAddress", ""),
        "processos": sorted(list(all_cnjs)),
        "indicios": sorted(list(all_cnjs_with_indication)),
        "html_original": html,
        "score": int(total_score),
        "hits": hits_str,
        "html_filename": fn_base + ".html",
        # <--- ALTERAÇÃO: Adicionar a lista de publicações processadas
        "processed_publications": processed_pubs
    }

# =============================================================================
# Funções de Coleta e Geração de Arquivos
# =============================================================================
def ensure_outputs(base="outputs", out_name: str = "recortes_amostra.jsonl"):
    html_dir = os.path.join(base, "html")
    os.makedirs(html_dir, exist_ok=True)
    return html_dir, os.path.join(base, out_name)


def reset_outputs(base="outputs", out_name: str = "recortes_amostra.jsonl"):
    if os.path.isdir(base): shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base, exist_ok=True)
    html_dir = os.path.join(base, "html")
    os.makedirs(html_dir, exist_ok=True)
    jsonl_path = os.path.join(base, out_name)
    if os.path.exists(jsonl_path): os.remove(jsonl_path)
    return html_dir, jsonl_path


def format_dt_for_outlook(dt: datetime) -> str:
    return dt.strftime("%m/%d/%Y %I:%M %p")


def collect_from_folder(store, folder, limit, restrict_clause, out_base, out_name):
    log = logging.getLogger(__name__)
    html_dir, jsonl_path = ensure_outputs(out_base, out_name)

    log.info("Conta: %s | Pasta: %s", store.DisplayName, folder.FolderPath)
    items = folder.Items
    items.Sort("[ReceivedTime]", True)

    if restrict_clause:
        log.info("Restrict: %s", restrict_clause)
        items = items.Restrict(restrict_clause)

    unlimited = (limit is None) or (limit <= 0)
    denom = "∞" if unlimited else str(limit)
    count = 0
    selected = []

    log.info("Iniciando varredura…")
    mail = items.GetFirst()
    while mail and (unlimited or count < limit):
        if hasattr(mail, "Class") and hasattr(mail, "Subject"):
            try:
                rec = mailitem_to_record(mail)
                selected.append(rec)
                count += 1
                log.info(f"[{count}/{denom}] {rec['subject'][:80]} | {rec['received']}")
            except Exception as e:
                log.exception("Falha ao ler item: %s", e)
        mail = items.GetNext()

    log.info("Varredura concluída: %d e-mail(s) selecionado(s).", len(selected))

    with open(jsonl_path, "a", encoding="utf-8") as jlw:
        for rec in selected:
            html_path = os.path.join(html_dir, rec["html_filename"])
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(rec["html_original"] or "")
                jlw.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception as e:
                log.exception("Falha ao gravar saídas para %s: %s", rec['entry_id'], e)

    log.info("Saídas gravadas em: %s e %s", html_dir, jsonl_path)


def is_arquivamento_from_score(score: int) -> int:
    return 1 if score >= 3 else 0


def generate_csv_from_jsonl(jsonl_path: str, csv_path: str):
    logging.info("Gerando CSV a partir de: %s (com reprocessamento)", jsonl_path)
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"Arquivo JSONL não encontrado: {jsonl_path}")

    out_rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                o = json.loads(line.strip())
                html_content = o.get("html_original", "")

                publications_html = split_html_into_publications(html_content)
                processed_pubs = [process_publication(pub_html) for pub_html in publications_html]

                total_score = 0
                all_cnjs: Set[str] = set()
                all_cnjs_with_indication: Set[str] = set()
                all_hits: Set[str] = set()

                for pub_data in processed_pubs:
                    total_score += pub_data["score"]
                    all_cnjs.update(pub_data["cnjs"])
                    all_cnjs_with_indication.update(pub_data["cnjs_with_indication"])
                    all_hits.update(pub_data["hits"])

                hits_str = ",".join(f"{LEXICON_ARQ_WEIGHTS[term]:+d}:{term}" for term in sorted(list(all_hits)))

                out_rows.append({
                    "received": o.get("received", ""),
                    "score": int(total_score),
                    "is_arquivamento": is_arquivamento_from_score(int(total_score)),
                    "hits": hits_str,
                    "subject": o.get("subject", ""),
                    "processos": "; ".join(sorted(list(all_cnjs))),
                    "indicios": "; ".join(sorted(list(all_cnjs_with_indication))),
                    "entry_id": o.get("entry_id", ""),
                    "html_file": os.path.join("html", o.get("html_filename", "")),
                    "html_filename": o.get("html_filename", ""),
                })
            except (json.JSONDecodeError, KeyError) as e:
                logging.warning(f"Linha JSON inválida ou com dados faltantes ignorada (linha {i + 1}): {e}")
                continue

    out_rows.sort(key=lambda r: (r["score"], r["received"]), reverse=True)

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fieldnames = ["received", "score", "is_arquivamento", "hits", "subject",
                  "processos", "indicios", "entry_id", "html_file", "html_filename"]
    with open(csv_path, "w", encoding="utf-8", newline="") as w:
        writer = csv.DictWriter(w, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(out_rows)

    logging.info("CSV gerado em: %s (linhas: %d)", csv_path, len(out_rows))


def main():
    p = argparse.ArgumentParser(description="Coletor de e-mails do Outlook para análise de arquivamento.")
    p.add_argument("--mode", choices=["all", "range", "today", "csv-only"], required=True)
    p.add_argument("--account", help="Nome da conta do Outlook. Obrigatório exceto para csv-only.")
    p.add_argument("--folder", default="inbox", help="Pasta-alvo (ex: 'Entrada/Subpasta').")
    p.add_argument("--date-from", help="(range) Data inicial em YYYY-MM-DD")
    p.add_argument("--date-to", help="(range) Data final em YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=-1, help="Limite de e-mails a processar (-1 para todos).")
    p.add_argument("--out", default="outputs", help="Diretório base de saída.")
    p.add_argument("--out-name", default="recortes_full.jsonl", help="Nome do arquivo JSONL.")
    p.add_argument("--csv-name", default="arquivamento.csv", help="Nome do arquivo CSV.")
    p.add_argument("--log", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = p.parse_args()

    setup_logging(args.log)

    if not HAS_BS4:
        logging.warning(
            "BeautifulSoup4 não encontrado (`pip install beautifulsoup4`). A extração de texto será menos precisa.")

    csv_path = os.path.join(args.out, args.csv_name)
    jsonl_path = os.path.join(args.out, args.out_name)

    if args.mode == "csv-only":
        generate_csv_from_jsonl(jsonl_path, csv_path)
        return

    if not HAS_PYWIN32:
        sys.exit("pywin32 não instalado. Use: pip install pywin32")
    if not args.account:
        sys.exit("--account é obrigatório para este modo.")

    store = resolve_store_by_displayname(args.account)
    folder = get_folder(store, args.folder)

    restrict = None
    if args.mode == "all":
        reset_outputs(args.out, args.out_name)
    elif args.mode == "today":
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        restrict = f"[ReceivedTime] >= '{format_dt_for_outlook(start)}'"
    elif args.mode == "range":
        if not args.date_from: sys.exit("--date-from é obrigatório para mode=range")
        dt_from = datetime.strptime(args.date_from, "%Y-%m-%d")
        dt_to = datetime.strptime(args.date_to, "%Y-%m-%d") + timedelta(
            days=1) if args.date_to else datetime.now() + timedelta(days=1)
        restrict = f"[ReceivedTime] >= '{format_dt_for_outlook(dt_from)}' AND [ReceivedTime] < '{format_dt_for_outlook(dt_to)}'"

    collect_from_folder(store, folder, args.limit, restrict, args.out, args.out_name)
    generate_csv_from_jsonl(jsonl_path, csv_path)


if __name__ == "__main__":
    main()
