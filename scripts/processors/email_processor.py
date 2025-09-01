# scripts/processors/email_processor.py

import re
from datetime import datetime
import time
from typing import Dict, List
from bs4 import BeautifulSoup
from app.modules.classifiers.archival_heuristic_classifier import ArchivalHeuristicClassifier


def html_to_text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)


def extract_pub_metadata(pub_text: str) -> Dict[str, str]:
    """Extrai metadados (Tribunal, Secretaria, Data) do texto de uma publicação."""
    metadata = {"tribunal": "", "secretaria": "", "data_publicacao": ""}
    # As regex para extração permanecem as mesmas
    tribunal_match = re.search(r"Tribunal:\s*(.*)", pub_text, re.IGNORECASE)
    if tribunal_match: metadata["tribunal"] = tribunal_match.group(1).strip()
    secretaria_match = re.search(r"Secretaria:\s*(.*)", pub_text, re.IGNORECASE)
    if secretaria_match: metadata["secretaria"] = secretaria_match.group(1).strip()
    data_match = re.search(r"(\d{2}/\d{2}/\d{4})", pub_text)
    if data_match: metadata["data_publicacao"] = data_match.group(1).strip()
    return metadata


def find_publication_tables(soup: BeautifulSoup) -> List:
    """Encontra as tabelas que representam publicações no HTML."""
    tags = soup.find_all("strong", string=re.compile(r"Publicação:"))
    if not tags: tags = soup.find_all("td", string=re.compile("Publicação:"))
    return list({tag.find_parent('table'): True for tag in tags if tag.find_parent('table')}.keys())


def process_email(mail_item: any, classifier: ArchivalHeuristicClassifier) -> Dict:
    """
    Processa um único item de e-mail e retorna um dicionário estruturado com os resultados.
    """
    html_original = getattr(mail_item, "HTMLBody", "") or ""
    if not html_original: return {}

    soup = BeautifulSoup(html_original, 'html.parser')
    publication_tables = find_publication_tables(soup)

    processed_pubs = []
    if not publication_tables:
        # ... (a lógica para e-mails sem tabelas de publicação pode ser simplificada ou mantida) ...
        # Para consistência, vamos aplicar a mesma lógica rica aqui.
        pub_html = soup.body.decode_contents() if soup.body else html_original
        pub_text = html_to_text(pub_html)
        cnjs = set(classifier.cnj_re.findall(pub_text))
        result = classifier.classify(pub_text) if cnjs else classifier._empty_result()
        metadata = extract_pub_metadata(pub_text)

        # ======================================================================
        # NOVA LÓGICA RICA: Captura a descrição E o texto correspondente
        # ======================================================================
        friendly_hits = []
        for match in result.get('matches', []):
            # Limpa o texto capturado de quebras de linha e espaços extras
            captured_text = re.sub(r'\s+', ' ', match['match'].group(0)).strip()
            friendly_hits.append(f"{match['description']} (texto: \"{captured_text}\")")
        result['friendly_hits'] = "; ".join(friendly_hits)
        # ======================================================================

        processed_pubs.append({**result, **metadata, "cnjs": sorted(list(cnjs)), "html_content": pub_html})
    else:
        for i, table in enumerate(publication_tables):
            table['id'] = f"pub_{i}"
            pub_html = str(table)
            pub_text = html_to_text(pub_html)
            cnjs = set(classifier.cnj_re.findall(pub_text))
            result = classifier.classify(pub_text) if cnjs else classifier._empty_result()
            metadata = extract_pub_metadata(pub_text)

            # ======================================================================
            # NOVA LÓGICA RICA: Captura a descrição E o texto correspondente
            # ======================================================================
            friendly_hits = []
            for match in result.get('matches', []):
                captured_text = re.sub(r'\s+', ' ', match['match'].group(0)).strip()
                friendly_hits.append(f"{match['description']} (texto: \"{captured_text}\")")
            result['friendly_hits'] = "; ".join(friendly_hits)
            # ======================================================================

            processed_pubs.append({**result, **metadata, "cnjs": sorted(list(cnjs)), "html_content": pub_html})

    return {
        "entry_id": mail_item.EntryID,
        "received": datetime.fromtimestamp(time.mktime(mail_item.ReceivedTime.timetuple())).strftime("%Y-%m-%d_%H%M%S"),
        "subject": mail_item.Subject or "",
        "total_score": round(sum(p['score'] for p in processed_pubs), 2),
        "html_enriched": str(soup),
        "processed_publications": processed_pubs
    }

