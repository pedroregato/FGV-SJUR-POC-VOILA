# -*- coding: utf-8 -*-
"""
Lê um JSONL de e-mails (gerado pelo coletor) e marca indícios de arquivamento.
Cria um CSV com score, termos encontrados e link para o HTML salvo.

Exemplo:
python scripts/scan_arquivamento.py \
  --in outputs/recortes_amostra.jsonl \
  --out outputs/arquivamento.csv \
  --html-dir outputs/html \
  --threshold 3 \
  --log INFO
"""

import argparse
import csv
import json
import logging
import os
import re
import unicodedata

def setup_logging(level: str):
    import logging
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S"
    )

def normalize(s: str) -> str:
    if s is None:
        return ""
    return unicodedata.normalize("NFKD", str(s)).encode("ASCII","ignore").decode("ASCII").lower()

# Termos/weights (acento-insensível; buscamos em subject+body)
POS_TERMS = [
    ("arquivament", 3),
    ("arquivado", 3),
    ("arquivar", 2),
    ("baixa nos autos", 2),
    ("baixa do processo", 2),
    ("baixa", 2),
    ("transito em julgado", 3),
    ("certidao de transito em julgado", 3),
    ("extincao do processo", 2),
    ("extinto o processo", 2),
    ("encerramento", 1),
    ("arquivamento definitivo", 3),
    ("arquivamento provisorio", 2),
    ("arquivado definitivamente", 3),
    ("arquivado provisoriamente", 2),
    ("preclusao", 1),
    ("sem mais atos processuais", 1),
]

# Penalizadores para reduzir falso positivo
NEG_TERMS = [
    ("nao arquivament", -3),
    ("indeferido o pedido de arquivament", -3),
    ("indeferido pedido de arquivament", -3),
    ("desarquiv", -2),
]

def score_text(text_norm: str):
    score = 0
    hits = []

    for term, w in POS_TERMS:
        if term in text_norm:
            score += w
            hits.append(f"+{w}:{term}")

    for term, w in NEG_TERMS:
        if term in text_norm:
            score += w
            hits.append(f"{w}:{term}")

    return score, hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Caminho do JSONL gerado pelo coletor.")
    ap.add_argument("--out", dest="out_csv", required=True, help="CSV de saída com os resultados.")
    ap.add_argument("--html-dir", default="outputs/html", help="Pasta onde os HTMLs foram salvos (para montar links).")
    ap.add_argument("--threshold", type=int, default=3, help="Score mínimo para marcar is_arquivamento=True.")
    ap.add_argument("--log", default="INFO", help="Nível de log.")
    args = ap.parse_args()

    setup_logging(args.log)
    log = logging.getLogger(__name__)

    if not os.path.exists(args.in_path):
        log.error("Arquivo JSONL não encontrado: %s", args.in_path)
        raise SystemExit(2)

    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)

    total = 0
    marcados = 0

    with open(args.in_path, "r", encoding="utf-8") as fin, \
         open(args.out_csv, "w", newline="", encoding="utf-8") as fout:

        writer = csv.writer(fout, delimiter=";")
        writer.writerow([
            "received", "subject", "sender", "score", "is_arquivamento",
            "hits", "html_path", "message_id", "entry_id"
        ])

        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            total += 1
            subj = rec.get("subject","")
            body = rec.get("texto_bruto","") or rec.get("html_original","") or ""
            text_norm = normalize(subj + "\n" + body)

            score, hits = score_text(text_norm)
            is_arquiv = score >= args.threshold
            if is_arquiv:
                marcados += 1

            # tenta recompor o nome do HTML salvo pelo coletor:
            # received__<subject>.html (subject saneado). Aqui não reconstituímos 100%,
            # então preferimos deixar vazio; quem quiser pode preencher depois.
            html_path = ""  # opcional: pode-se varrer a pasta e tentar casar por received/subject

            writer.writerow([
                rec.get("received",""),
                subj.replace("\n"," ").replace("\r"," "),
                rec.get("sender",""),
                score,
                "1" if is_arquiv else "0",
                ",".join(hits),
                html_path,
                rec.get("message_id",""),
                rec.get("entry_id",""),
            ])

    log.info("✅ Processado: %d registro(s). Marcados como arquivamento: %d (threshold=%d).",
             total, marcados, args.threshold)
    log.info("CSV salvo em: %s", args.out_csv)

if __name__ == "__main__":
    main()
