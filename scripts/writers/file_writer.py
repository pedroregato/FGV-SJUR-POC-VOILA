# scripts/writers/file_writer.py

import os
import json
import csv
import re
from typing import List, Dict, Set


def safe_filename(s: str, maxlen: int = 140) -> str:
    """
    Limpa e trunca uma string para que ela possa ser usada como um nome de arquivo seguro.
    Remove caracteres inválidos e substitui espaços múltiplos.
    """
    # Remove caracteres que são inválidos em nomes de arquivo na maioria dos sistemas
    s = re.sub(r'[\\/:*?"<>|]', "_", s or "")
    # Substitui múltiplos espaços, tabulações ou quebras de linha por um único espaço
    s = re.sub(r"\s+", " ", s).strip()
    # Trunca o nome do arquivo para o comprimento máximo, se necessário
    if len(s) > maxlen:
        return s[:maxlen].rstrip()
    # Retorna um nome padrão se a string resultante for vazia
    return s or "sem_assunto"


def write_outputs(processed_records: List[Dict], output_dir: str):
    """Grava todos os arquivos de saída: HTML, JSON e os dois CSVs."""
    html_path = os.path.join(output_dir, "html")
    json_path = os.path.join(output_dir, "json")
    os.makedirs(html_path, exist_ok=True)
    os.makedirs(json_path, exist_ok=True)

    # 1. Grava arquivos HTML e JSON individuais
    for record in processed_records:
        fn_base = f"{record['received']}__{safe_filename(record['subject'])}"
        record['html_filename'] = f"{fn_base}.html"

        with open(os.path.join(html_path, record['html_filename']), "w", encoding="utf-8") as f:
            f.write(record.get("html_enriched", ""))

        record_to_save = {k: v for k, v in record.items() if k != 'html_enriched'}
        with open(os.path.join(json_path, f"{fn_base}.json"), "w", encoding="utf-8") as f:
            json.dump(record_to_save, f, ensure_ascii=False, indent=2)

    # 2. Gera e grava os CSVs
    recortes_rows, publicacoes_rows = [], []
    for record in processed_records:
        pubs_com_indicio, pubs_com_cnj = 0, 0
        all_cnjs_in_email: Set[str] = set()
        cnjs_with_indication: Set[str] = set()

        for i, pub_data in enumerate(record.get("processed_publications", [])):
            pub_cnjs = pub_data.get("cnjs", [])
            if not pub_cnjs: continue

            all_cnjs_in_email.update(pub_cnjs)
            pubs_com_cnj += 1

            if pub_data.get("score", 0) > 0:
                pubs_com_indicio += 1
                cnjs_with_indication.update(pub_cnjs)

            publicacoes_rows.append({
                "email_entry_id": record.get("entry_id"), "publication_id": f"{record.get('entry_id')}_{i}",
                "tribunal": pub_data.get("tribunal"), "secretaria": pub_data.get("secretaria"),
                "data_publicacao": pub_data.get("data_publicacao"), "score": pub_data.get("score"),
                "classification_level": pub_data.get("level"),
                "hits": ",".join(m["rule"] for m in pub_data.get("matches", [])),
                "processos": ";".join(pub_data.get("cnjs", [])),
                "html_content": pub_data.get("html_content", ""),
                "html_filename": record.get("html_filename"),
            })

        recortes_rows.append({
            "received": record.get("received"), "subject": record.get("subject"),
            "total_score": record.get("total_score"), "pubs_com_cnj": pubs_com_cnj,
            "pubs_com_indicios": pubs_com_indicio,
            "processos": ";".join(sorted(list(all_cnjs_in_email))),
            "processos_com_indicios": ";".join(sorted(list(cnjs_with_indication))),
            "entry_id": record.get("entry_id"), "html_filename": record.get("html_filename"),
        })

    # Escreve recortes.csv
    recortes_csv_path = os.path.join(output_dir, "recortes.csv")
    recortes_fieldnames = ["received", "subject", "total_score", "pubs_com_cnj", "pubs_com_indicios", "processos",
                           "processos_com_indicios", "entry_id", "html_filename"]
    with open(recortes_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=recortes_fieldnames, delimiter=";", extrasaction='ignore')
        writer.writeheader()
        writer.writerows(recortes_rows)

    # Escreve publicacoes.csv
    publicacoes_csv_path = os.path.join(output_dir, "publicacoes.csv")
    publicacoes_fieldnames = ["email_entry_id", "publication_id", "tribunal", "secretaria", "data_publicacao", "score",
                              "classification_level", "hits", "processos", "html_content", "html_filename"]
    with open(publicacoes_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=publicacoes_fieldnames, delimiter=";", extrasaction='ignore')
        writer.writeheader()
        writer.writerows(publicacoes_rows)
