# -*- coding: utf-8 -*-
"""
Coleta N e-mails do Outlook e grava HTML/JSON/JSONL/CSV em outputs/.

Modos:
  - all      : varre todos os e-mails e reinicia as saídas
  - range    : varre por período (--date-from/--date-to em YYYY-MM-DD)
  - today    : apenas e-mails de hoje
  - csv-only : só (re)gera o CSV a partir do JSON(L) existente

Exemplos:

python scripts/coletar_5_emails_para_outputs.py ^
  --mode all ^
  --account "SJUR Coleta Serdon" ^
  --folder Entrada ^
  --out outputs ^
  --out-name recortes_full.jsonl ^
  --log INFO
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

# Para busca robusta em texto (Unicode). Se não tiver 'regex', use 're'
try:
    import regex as re
except Exception:
    import re

# ===== BeautifulSoup (opcional para melhor HTML->texto)
try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

# ===== pywin32 (apenas quando não for csv-only)
try:
    import win32com.client  # pywin32
    import pythoncom

    HAS_PYWIN32 = True
except Exception:
    HAS_PYWIN32 = False

# ======================
# Config / Léxico / Regex
# ======================
DEFAULT_NEAR_WINDOW = int(os.getenv("SJUR_NEAR_WINDOW", "3000"))  # janela CNJ↔indício

# Léxico com pesos (positivo = indício; negativo = anti-indício)
LEXICON_ARQ_WEIGHTS: dict[str, int] = {
    # positivos
    "arquivamento": 3,
    "arquivado": 3,
    "arquivar": 3,
    "baixa": 2,
    "baixado": 2,
    "trânsito em julgado": 3,
    "transito em julgado": 3,
    "tjulg": 2,
    "extinção do processo": 2,
    "extinto o processo": 2,
    "extinção": 1,
    "preclusão": 1,
    "encerramento": 1,
    # negativos
    "desarquivamento": -2,
}

# Regex do CNJ
CNJ_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")


# ======================
# Utils
# ======================
def setup_logging(level: str):
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S"
    )


def normalize_simple(s: str) -> str:
    """lower + remove acentos; vazio para None."""
    if s is None:
        return ""
    return unicodedata.normalize("NFKD", str(s)).encode("ASCII", "ignore").decode("ASCII").lower()


def normalize_match(s: str) -> str:
    """normalização 'leve' (preserva comprimento) para casar keywords/casefold."""
    if s is None:
        return ""
    return unicodedata.normalize("NFKC", str(s)).casefold()


def html_to_text(html: str) -> str:
    if not html:
        return ""
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text("\n", strip=True)
    # fallback simples
    return re.sub(r"<[^>]+>", " ", html).strip()


def safe_filename(s: str, maxlen: int = 140) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "_", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > maxlen:
        s = s[:maxlen].rstrip()
    return s or "sem_assunto"


def now_local_date():
    t = datetime.now()
    return datetime(t.year, t.month, t.day, 0, 0, 0)


# ======================
# Outlook helpers
# ======================
OL_FOLDER_INBOX = 6  # olFolderInbox


def get_namespace():
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")


def list_accounts():
    mapi = get_namespace()
    names = [store.DisplayName for store in mapi.Stores]
    return names


def resolve_store_by_displayname(account_name: str):
    mapi = get_namespace()
    target_norm = normalize_simple(account_name)
    candidates = []
    for store in mapi.Stores:
        dn = store.DisplayName
        if normalize_simple(dn) == target_norm:
            return store
        candidates.append(dn)
    # match parcial
    for store in mapi.Stores:
        dn = store.DisplayName
        if target_norm in normalize_simple(dn):
            return store
    raise RuntimeError(
        f"Conta '{account_name}' não encontrada. Contas disponíveis: {candidates}"
    )


def get_folder(store, folder_arg: str):
    """
    Obtém pasta a partir do argumento:
    - 'inbox' / 'caixa de entrada' / 'entrada' => Inbox da store
    - caminho com '/' (ex.: 'Entrada/Subpasta')
    - vazio/None => Inbox
    """
    if not folder_arg:
        return store.GetDefaultFolder(OL_FOLDER_INBOX)

    fname = normalize_simple(folder_arg)
    if fname in ("inbox", "caixa de entrada", "caixa de entrada/", "entrada", "entrada/"):
        return store.GetDefaultFolder(OL_FOLDER_INBOX)

    node = store.GetRootFolder()
    parts = [p for p in folder_arg.split("/") if p.strip()]
    for part in parts:
        found = None
        for f in node.Folders:
            if normalize_simple(f.Name) == normalize_simple(part):
                found = f
                break
        if not found:
            raise RuntimeError(
                f"Pasta '{folder_arg}' não encontrada sob '{node.FolderPath}'."
            )
        node = found
    return node


# ======================
# Scoring / CNJ associação
# ======================
def compute_hits_and_score(text: str) -> tuple[int, list[str], str]:
    """
    Retorna: (score_total, lista_de_termos_encontrados, hits_string_com_pesos)
    hits_string_ex.: '+3:arquivamento,+2:baixa,-2:desarquivamento'
    """
    if not text:
        return 0, [], ""

    tnorm = normalize_match(text)
    score = 0
    found_terms = []
    parts = []
    for term, weight in LEXICON_ARQ_WEIGHTS.items():
        term_norm = normalize_match(term)
        if not term_norm:
            continue
        if term_norm in tnorm:
            found_terms.append(term)
            parts.append(f"{weight:+d}:{term}")
            score += weight
    hits_str = ",".join(parts)
    return score, found_terms, hits_str


def cnjs_with_indicios(text: str, lexicon_terms: list[str], window_chars: int) -> list[str]:
    """CNJs cujo contexto ±window_chars contém ao menos 1 termo do léxico."""
    if not text:
        return []
    cnj_matches = list(CNJ_RE.finditer(text))
    if not cnj_matches:
        return []

    tnorm = normalize_match(text)
    kw_positions = []
    for kw in lexicon_terms:
        kw_norm = normalize_match(kw)
        if not kw_norm:
            continue
        for m in re.finditer(re.escape(kw_norm), tnorm):
            kw_positions.append(m.start())
    if not kw_positions:
        return []

    kept = []
    for m in cnj_matches:
        start = m.start()
        if any(abs(p - start) <= window_chars for p in kw_positions):
            kept.append(m.group())

    # dedup preservando ordem
    seen = set()
    result = []
    for x in kept:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


def cnjs_com_indicios_positivos(text: str, lexicon_terms: list[str], window_chars: int) -> list[str]:
    """CNJs cujo contexto ±window_chars contém ao menos 1 termo POSITIVO do léxico."""
    if not text:
        return []

    cnj_matches = list(CNJ_RE.finditer(text))
    if not cnj_matches:
        return []

    tnorm = normalize_match(text)

    # FILTRAR apenas termos POSITIVOS (peso > 0)
    positive_terms = [term for term, weight in LEXICON_ARQ_WEIGHTS.items() if weight > 0]
    positive_terms_norm = [normalize_match(term) for term in positive_terms]

    kw_positions = []
    for kw_norm in positive_terms_norm:
        if not kw_norm:
            continue
        for m in re.finditer(re.escape(kw_norm), tnorm):
            kw_positions.append(m.start())

    if not kw_positions:
        return []

    kept = []
    for m in cnj_matches:
        start = m.start()
        if any(abs(p - start) <= window_chars for p in kw_positions):
            kept.append(m.group())

    # dedup preservando ordem
    seen = set()
    result = []
    for x in kept:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


# ======================
# Saídas (pastas e arquivos)
# ======================
def ensure_outputs(base="outputs", out_name: str = "recortes_amostra.jsonl"):
    html_dir = os.path.join(base, "html")
    json_dir = os.path.join(base, "json")
    os.makedirs(html_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    return html_dir, json_dir, os.path.join(base, out_name)


def reset_outputs(base="outputs", out_name: str = "recortes_amostra.jsonl"):
    if os.path.isdir(base):
        logging.info("Recriando diretório de saída: %s", base)
    os.makedirs(base, exist_ok=True)
    html_dir = os.path.join(base, "html")
    json_dir = os.path.join(base, "json")
    for d in (html_dir, json_dir):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
    jsonl_path = os.path.join(base, out_name)
    if os.path.exists(jsonl_path):
        os.remove(jsonl_path)
    return html_dir, json_dir, jsonl_path


def format_dt_for_outlook(dt: datetime) -> str:
    # Outlook Restrict requer en-US: MM/DD/YYYY HH:MM AM/PM
    return dt.strftime("%m/%d/%Y %I:%M %p")


def mailitem_to_record(mail, near_window_chars: int):
    subject = mail.Subject or ""
    sender = getattr(getattr(mail, "Sender", None), "Address", None) or getattr(mail, "SenderEmailAddress", "")
    received_time = mail.ReceivedTime  # COM datetime
    entry_id = mail.EntryID
    internet_msg_id = getattr(mail, "InternetMessageID", None)
    html = getattr(mail, "HTMLBody", "") or ""
    text = html_to_text(html)

    # score / hits
    score, found_terms, hits_str = compute_hits_and_score(subject + "\n" + text)

    # processos (com janela larga) - TODOS os CNJs
    processos_list = cnjs_with_indicios(text, found_terms, near_window_chars)

    # NOVO: processos apenas com indícios POSITIVOS
    indicios_list = cnjs_com_indicios_positivos(text, found_terms, near_window_chars)

    dt_str = datetime.fromtimestamp(time.mktime(received_time.timetuple())).strftime("%Y-%m-%d_%H%M%S")
    fn_base = f"{dt_str}__{safe_filename(subject)}"

    return {
        "message_id": internet_msg_id,
        "entry_id": entry_id,
        "received": dt_str,
        "subject": subject,
        "sender": sender,
        "processo": None,
        "processos": processos_list,
        "indicios": indicios_list,
        "orgao": None,
        "data_disponibilizacao": None,
        "tipo_comunicacao": None,
        "link_inteiro_teor": None,
        "texto_bruto": text,
        "html_original": html,
        "score": int(score),
        "hits": hits_str,
        "html_file_basename": fn_base + ".html",
        "html_filename": fn_base + ".html",
    }


def collect_from_folder(store, folder, limit, restrict_clause, out_base, out_name, near_window_chars: int):
    log = logging.getLogger(__name__)
    html_dir, json_dir, jsonl_path = ensure_outputs(out_base, out_name)

    log.info("Conta: %s | Pasta: %s", store.DisplayName, folder.FolderPath)
    items = folder.Items
    items.Sort("[ReceivedTime]", True)  # mais recentes primeiro

    if restrict_clause:
        t0 = time.time()
        items = items.Restrict(restrict_clause)
        log.info("Restrict: %s", restrict_clause)
        log.info("Restrict aplicado em %.2fs", time.time() - t0)

    unlimited = (limit is None) or (limit <= 0)
    denom = "∞" if unlimited else str(limit)

    count = 0
    inspected = 0
    selected = []

    log.info("Iniciando varredura…")
    mail = items.GetFirst()
    while mail and (unlimited or count < limit):
        inspected += 1
        is_mail = hasattr(mail, "Class") and hasattr(mail, "Subject") and hasattr(mail, "ReceivedTime")
        if not is_mail:
            mail = items.GetNext()
            continue
        try:
            rec = mailitem_to_record(mail, near_window_chars)
            selected.append((mail, rec))
            count += 1
            log.info("[{}/{}] {} | {}".format(
                count, denom,
                (rec["subject"][:80] + ("…" if len(rec["subject"]) > 80 else "")),
                rec["received"]
            ))
        except Exception as e:
            log.exception("Falha ao ler item: %s", e)

        mail = items.GetNext()

    log.info("Varredura concluída: %d selecionado(s), %d item(ns) inspecionado(s)",
             len(selected), inspected)

    # grava
    written = 0
    t_all0 = time.time()
    with open(jsonl_path, "a", encoding="utf-8") as jlw:
        for _, rec in selected:
            dt = rec["received"]
            fn_base = rec["html_file_basename"].rsplit(".html", 1)[0]
            html_path = os.path.join(html_dir, f"{fn_base}.html")
            json_path = os.path.join(json_dir, f"{fn_base}.json")

            # HTML
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(rec["html_original"] or "")
            except Exception as e:
                log.exception("Falha ao gravar HTML: %s", e)

            # JSON
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(rec, f, ensure_ascii=False, indent=2)
            except Exception as e:
                log.exception("Falha ao gravar JSON: %s", e)

            # JSONL (linha)
            try:
                jlw.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception as e:
                log.exception("Falha ao gravar JSONL: %s", e)

            written += 1

    log.info("Saídas:")
    log.info("• HTML: %s", html_dir)
    log.info("• JSON: %s", json_dir)
    log.info("• JSONL: %s", jsonl_path)
    log.info("✅ Total processado: %d e-mail(s) em %.2fs", written, time.time() - t_all0)


def verify_data_consistency(csv_path: str, html_dir: str):
    """Verifica se todos os arquivos HTML referenciados no CSV existem"""
    import pandas as pd
    from pathlib import Path

    df = pd.read_csv(csv_path, sep=";")
    missing_files = []

    for idx, row in df.iterrows():
        html_file = row.get("html_file", "")
        if html_file and isinstance(html_file, str):
            # Se o caminho for relativo (apenas nome do arquivo)
            if "/" not in html_file and "\\" not in html_file:
                html_path = Path(html_dir) / html_file
            else:
                html_path = Path(html_file)

            if not html_path.exists():
                missing_files.append({
                    "index": idx,
                    "expected": html_file,
                    "subject": str(row.get("subject", ""))[:50],
                    "received": str(row.get("received", ""))
                })

    return missing_files


# ======================
# CSV (compatível com Streamlit)
# ======================
def is_arquivamento_from_score(score: int) -> int:
    # limiar simples; ajuste se desejar
    return 1 if score >= 3 else 0


def generate_csv_from_jsonl(jsonl_path: str, csv_path: str, out_base: str, near_window_chars: int):
    """
    Lê JSONL, recalcula score/hits se necessário, popula 'processos' (janela larga),
    e gera 'arquivamento.csv' compatível com o app Streamlit.
    """
    logging.info("Gerando CSV a partir de: %s", jsonl_path)
    rows = []
    if not os.path.exists(jsonl_path):
        logging.warning("JSONL não encontrado. Tentando 'json/' individuais…")
        json_dir = os.path.join(out_base, "json")
        if not os.path.isdir(json_dir):
            raise FileNotFoundError("Nem JSONL nem diretório JSON encontrados.")
        files = sorted(os.listdir(json_dir))
        for fn in files:
            if not fn.lower().endswith(".json"):
                continue
            p = os.path.join(json_dir, fn)
            try:
                o = json.load(open(p, "r", encoding="utf-8"))
            except Exception:
                continue
            rows.append(o)
    else:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                    rows.append(o)
                except Exception:
                    continue

    # Monta registros CSV
    out_rows = []
    for o in rows:
        subject = o.get("subject", "")
        html = o.get("html_original", "") or ""
        text = o.get("texto_bruto", "") or html_to_text(html)
        score = int(o.get("score", 0))
        hits = o.get("hits")
        if not hits:
            score, found_terms, hits = compute_hits_and_score(subject + "\n" + text)
        else:
            # também precisamos dos termos em lista para CNJ↔indício
            found_terms = [h.split(":", 1)[-1] for h in hits.split(",") if ":" in h]

        processos = o.get("processos") or []
        indicios = o.get("indicios") or []

        if not processos:
            processos = cnjs_with_indicios(text, found_terms, near_window_chars)
        if not indicios:
            indicios = cnjs_com_indicios_positivos(text, found_terms, near_window_chars)

        entry_id = o.get("entry_id") or ""
        received = o.get("received") or ""
        html_base = o.get("html_file_basename") or f"{received}__{safe_filename(subject)}.html"

        html_file = os.path.join("html", html_base)  # Caminho relativo

        out_rows.append({
            "received": received,
            "score": int(score),
            "is_arquivamento": is_arquivamento_from_score(int(score)),
            "hits": hits or "",
            "subject": subject,
            "processos": "; ".join(processos) if isinstance(processos, list) else str(processos),
            "indicios": "; ".join(indicios) if isinstance(indicios, list) else str(indicios),
            "entry_id": entry_id,
            "html_file": html_file,
            "html_filename": html_base,
        })

    # Ordena por score desc + received desc (string já vem com padrão YYYY-MM-DD_HHMMSS)
    out_rows.sort(key=lambda r: (r["score"], r["received"]), reverse=True)

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as w:
        writer = csv.DictWriter(w, fieldnames=[
            "received", "score", "is_arquivamento", "hits", "subject",
            "processos", "indicios", "entry_id", "html_file", "html_filename"
        ], delimiter=";")
        writer.writeheader()
        writer.writerows(out_rows)

    logging.info("CSV gerado em: %s (linhas: %d)", csv_path, len(out_rows))

    return out_rows


# ======================
# CLI
# ======================
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["all", "range", "today", "csv-only"], required=True)
    p.add_argument("--account", help="DisplayName parcial/exato da conta (store). Obrigatório exceto csv-only.")
    p.add_argument("--folder", default="inbox",
                   help="Pasta-alvo. Use 'inbox'/'Caixa de Entrada'/'Entrada' ou caminho com '/', ex.: 'Entrada/Subpasta'.")
    p.add_argument("--date-from", help="(range) Data inicial em YYYY-MM-DD")
    p.add_argument("--date-to", help="(range) Data final em YYYY-MM-DD (inclusiva)")
    p.add_argument("--limit", type=int, default=-1, help="Limite de e-mails; use -1/0 para TODOS (default).")
    p.add_argument("--out", default="outputs", help="Diretório base para salvar os arquivos.")
    p.add_argument("--out-name", type=str, default="recortes_full.jsonl",
                   help="Nome do JSONL agregado dentro de --out (default: recortes_full.jsonl)")
    p.add_argument("--csv-name", type=str, default="arquivamento.csv",
                   help="Nome do CSV dentro de --out (default: arquivamento.csv)")
    p.add_argument("--log", default="INFO", help="Nível de log: DEBUG/INFO/WARNING/ERROR.")
    p.add_argument("--near-window", type=int, default=DEFAULT_NEAR_WINDOW,
                   help=f"Janela (±) de caracteres para associar CNJ a indícios (default: {DEFAULT_NEAR_WINDOW}).")
    args = p.parse_args()

    setup_logging(args.log)

    csv_path = os.path.join(args.out, args.csv_name)
    jsonl_path = os.path.join(args.out, args.out_name)

    # ----- CSV-ONLY
    if args.mode == "csv-only":
        generate_csv_from_jsonl(jsonl_path, csv_path, args.out, args.near_window)

        # Verificação de consistência após gerar CSV
        html_dir_path = os.path.join(args.out, "html")
        missing_files = verify_data_consistency(csv_path, html_dir_path)
        if missing_files:
            logging.warning(f"⚠️  Encontrados {len(missing_files)} arquivos HTML faltantes:")
            for m in missing_files[:10]:
                logging.warning(f"  - {m['received']}: {m['subject']} -> {m['expected']}")
        else:
            logging.info("✅ Todos os arquivos HTML estão consistentes com o CSV")
        return

    # Valida pywin32
    if not HAS_PYWIN32:
        print("pywin32 não instalado. Instale com: pip install pywin32")
        sys.exit(3)

    # Resolve store/pasta
    logging.info("Conectando ao Outlook…")
    store = resolve_store_by_displayname(args.account)
    logging.info("✓ Store selecionada: %s", store.DisplayName)

    try:
        folder = get_folder(store, args.folder)
    except Exception as e:
        logging.error("Falha ao resolver pasta '%s': %s", args.folder, e)
        sys.exit(2)

    # Define Restrict conforme modo
    restrict = None
    limit = args.limit

    if args.mode == "all":
        # recria saídas e JSONL
        reset_outputs(args.out, args.out_name)
        restrict = None  # sem filtro
        # limit mantém (se -1/0 => todos)
    elif args.mode == "today":
        html_dir, json_dir, jsonl_path = ensure_outputs(args.out, args.out_name)
        start = now_local_date()
        restrict = f"[ReceivedTime] >= '{format_dt_for_outlook(start)}'"
    elif args.mode == "range":
        html_dir, json_dir, jsonl_path = ensure_outputs(args.out, args.out_name)
        if not args.date_from:
            logging.error("--date-from é obrigatório para mode=range")
            sys.exit(2)
        try:
            dt_from = datetime.strptime(args.date_from, "%Y-%m-%d")
        except Exception:
            logging.error("--date-from inválido; use YYYY-MM-DD")
            sys.exit(2)
        if args.date_to:
            try:
                dt_to = datetime.strptime(args.date_to, "%Y-%m-%d") + timedelta(days=1)  # inclusivo
            except Exception:
                logging.error("--date-to inválido; use YYYY-MM-DD")
                sys.exit(2)
        else:
            dt_to = datetime.now() + timedelta(days=1)
        restrict = (f"[ReceivedTime] >= '{format_dt_for_outlook(dt_from)}' "
                    f"AND [ReceivedTime] < '{format_dt_for_outlook(dt_to)}'")
    else:
        logging.error("Modo inválido.")
        sys.exit(2)

    # Coleta
    t0 = time.time()
    collect_from_folder(
        store=store,
        folder=folder,
        limit=limit,
        restrict_clause=restrict,
        out_base=args.out,
        out_name=args.out_name,
        near_window_chars=args.near_window,
    )
    # CSV após coleta
    generate_csv_from_jsonl(jsonl_path, csv_path, args.out, args.near_window)

    # Verificação de consistência após gerar CSV
    html_dir_path = os.path.join(args.out, "html")
    missing_files = verify_data_consistency(csv_path, html_dir_path)
    if missing_files:
        logging.warning(f"⚠️  Encontrados {len(missing_files)} arquivos HTML faltantes:")
        for m in missing_files[:10]:
            logging.warning(f"  - {m['received']}: {m['subject']} -> {m['expected']}")
    else:
        logging.info("✅ Todos os arquivos HTML estão consistentes com o CSV")

    logging.info("(Concluído em %.2fs)", time.time() - t0)


if __name__ == "__main__":
    main()