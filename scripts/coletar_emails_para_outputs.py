# scripts/coletar_emails_para_outputs.py (VERSÃO COMPLETA ATUALIZADA)

import os, shutil, sys, time, unicodedata, json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Set
import win32com.client

# ATUALIZE O IMPORT:
try:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    from app.styles.highlighter import highlight_html_with_metadata  # ✅ Nova função
    from app.rules.archival_rules import sjur_rules, SjurRulesManager
    import regex as re
    from bs4 import BeautifulSoup
    import win32com.client

    HAS_BS4 = HAS_WIN32COM = True
except ImportError as e:
    print(f"ERRO CRÍTICO: Falha ao importar módulos: {e}")
    sys.exit(1)


# --- Funções Utilitárias Essenciais ---

def html_to_text(html: str) -> str:
    """Converte uma string HTML para texto plano, usando o parser lxml."""
    if not html or not HAS_BS4:
        return ""
    return BeautifulSoup(html, "lxml").get_text("\n", strip=True)


def split_html_into_publications(html_content: str) -> List[str]:
    """
    Divide o HTML de um recorte em uma lista de publicações individuais.
    Esta é a heurística que encontra as tabelas baseadas no marcador 'Publicação:'.
    """
    if not html_content or not HAS_BS4:
        return [html_content]

    soup = BeautifulSoup(html_content, "lxml")

    # Encontra todos os marcadores de publicação
    publication_tags = soup.find_all("strong", string=re.compile(r"Publicação:"))
    if not publication_tags:
        publication_tags = soup.find_all("td", string=re.compile(r"Publicação:"))

    if not publication_tags:
        # Se não há marcadores, retorna o corpo inteiro como uma única publicação
        return [soup.body.decode_contents() if soup.body else html_content]

    publications = []
    for tag in publication_tags:
        parent_table = tag.find_parent('table')
        if parent_table:
            table_str = str(parent_table)
            # Evita adicionar a mesma tabela duas vezes
            if not publications or publications[-1] != table_str:
                publications.append(table_str)

    if not publications:
        return [soup.body.decode_contents() if soup.body else html_content]

    return publications


def safe_filename(s: str, maxlen: int = 140) -> str:
    if not s: return "sem_assunto"
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen].rstrip() if len(s) > maxlen else s


def resolve_store_by_displayname(display_name: str):
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    for store in namespace.Stores:
        if store.DisplayName == display_name: return store
    raise RuntimeError(f"Conta '{display_name}' não encontrada.")


def get_folder(store, folder_arg: str):
    if folder_arg.lower() in ["inbox", "caixa de entrada"]: return store.GetDefaultFolder(6)
    node = store.GetRootFolder()
    for part in [p for p in folder_arg.split("/") if p.strip()]:
        norm_part = unicodedata.normalize("NFKD", part.lower())
        found = next((f for f in node.Folders if unicodedata.normalize("NFKD", f.Name.lower()) == norm_part), None)
        if not found: raise RuntimeError(f"Pasta '{part}' não encontrada em '{node.FolderPath}'.")
        node = found
    return node


def ensure_outputs(base="outputs"):
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base, "html"), exist_ok=True)
    os.makedirs(os.path.join(base, "json"), exist_ok=True)


def reset_outputs(base="outputs"):
    if os.path.isdir(base): shutil.rmtree(base, ignore_errors=True)
    ensure_outputs(base)


# --- Funções de Estatísticas e Processamento ---

def calculate_email_statistics(processed_publications: List[Dict]) -> Dict:
    """
    Calcula estatísticas consolidadas para todas as publicações de um e-mail.
    """
    archival_threshold = 0.6  # Limiar para considerar como candidato a arquivamento

    total_publications = len(processed_publications)
    archival_candidates = 0
    archival_processes = set()
    non_archival_processes = set()

    for pub in processed_publications:
        if pub.get("score", 0) >= archival_threshold:
            archival_candidates += 1
            # Adiciona CNJs desta publicação à lista de processos para arquivamento
            cnjs = pub.get("metadata", {}).get("cnjs", [])
            archival_processes.update(cnjs)
        else:
            # Para publicações não candidatas, adiciona CNJs à lista de não-arquivamento
            cnjs = pub.get("metadata", {}).get("cnjs", [])
            non_archival_processes.update(cnjs)

    return {
        "total_publications": total_publications,
        "total_archival_candidates": archival_candidates,
        "total_non_archival": total_publications - archival_candidates,
        "archival_processes": sorted(list(archival_processes)),
        "non_archival_processes": sorted(list(non_archival_processes)),
        "archival_threshold": archival_threshold
    }


def generate_dashboard_data(emails_data: List[Dict]) -> Dict:
    """
    Gera dados consolidados para o dashboard Streamlit.
    """
    total_emails = len(emails_data)
    total_publications = sum(email["total_publications"] for email in emails_data)
    total_archival_candidates = sum(email["statistics"]["total_archival_candidates"] for email in emails_data)

    # Contagem de processos únicos
    all_archival_processes = set()
    all_non_archival_processes = set()

    for email in emails_data:
        all_archival_processes.update(email["statistics"]["archival_processes"])
        all_non_archival_processes.update(email["statistics"]["non_archival_processes"])

    return {
        "total_emails": total_emails,
        "total_publications": total_publications,
        "total_archival_candidate_publications": total_archival_candidates,
        "unique_archival_processes": sorted(list(all_archival_processes)),
        "unique_non_archival_processes": sorted(list(all_non_archival_processes)),
        "emails": emails_data  # Dados detalhados por e-mail
    }


# --- Lógica de Processamento ---

# scripts/coletar_emails_para_outputs.py (CORREÇÃO PARA NOVO FORMATO)

# ... (imports existentes) ...

# ... (funções utilitárias mantidas) ...

def process_publication_with_new_architecture(pub_html: str, pub_index: int) -> Dict[str, Any]:
    """
    Processa uma única publicação usando a nova arquitetura de regras de 3 camadas.
    """
    if not pub_html:
        return {
            "score": 0.0, "level": "N/A", "analysis_status": "EMPTY_CONTENT",
            "hits": {}, "metadata": {}, "context_hits": [], "html_enriched": "",
            "html_content": pub_html, "id": f"pub_{pub_index}"
        }

    # Garante que as regras mais recentes estejam carregadas
    sjur_rules.load_all_rules()

    # Prepara o texto para análise
    text_for_analysis = html_to_text(pub_html)

    # CAMADA 1: REGRAS MANDATÓRIAS
    passes_mandatory = sjur_rules.check_mandatory_rules(text_for_analysis)

    # ✅ NOVA ABORDAGEM: Usa highlight_html_with_metadata
    highlight_result = highlight_html_with_metadata(pub_html)
    html_enriched = highlight_result["html"]  # ✅ Agora é um dict, não string
    extracted_cnjs = highlight_result["cnjs"]
    extracted_metadata = highlight_result["metadata"]

    if not passes_mandatory:
        # Se não passar nas regras mandatórias
        context_data = sjur_rules.extract_context_data(text_for_analysis)

        # Combina metadados extraídos do destaque com os das regras de contexto
        merged_metadata = {**extracted_metadata, **context_data.get("metadata", {})}

        # Adiciona CNJs encontrados durante o destaque
        if extracted_cnjs:
            if 'cnjs' not in merged_metadata:
                merged_metadata['cnjs'] = []
            merged_metadata['cnjs'].extend(extracted_cnjs)
            merged_metadata['cnjs'] = list(set(merged_metadata['cnjs']))

        return {
            "score": 0.0,
            "level": "Rejeitado",
            "analysis_status": "REJECTED_MANDATORY_RULE",
            "hits": {},
            "metadata": merged_metadata,
            "context_hits": context_data.get("context_hits", []),
            "html_enriched": html_enriched,  # ✅ Agora é string do dict
            "html_content": pub_html,
            "id": f"pub_{pub_index}"
        }

    # CAMADA 2: REGRAS DETERMINANTES (CÁLCULO DE SCORE)
    score_data = sjur_rules.calculate_score(text_for_analysis)
    score = score_data.get("score", 0.0)
    hits = score_data.get("hits", {})

    # Define o nível com base nos limiares
    level = "Forte" if score >= 0.9 else "Provável" if score >= 0.6 else "Fraco"

    # CAMADA 3: REGRAS DE CONTEXTO E METADADOS
    context_data = sjur_rules.extract_context_data(text_for_analysis)

    # ✅ COMBINA TODOS OS METADADOS: destaque + regras de contexto
    merged_metadata = {**extracted_metadata, **context_data.get("metadata", {})}

    # ✅ GARANTE QUE CNJs ENCONTRADOS NO DESTAQUE SEJAM INCLUÍDOS
    if extracted_cnjs:
        if 'cnjs' not in merged_metadata:
            merged_metadata['cnjs'] = []
        merged_metadata['cnjs'].extend(extracted_cnjs)
        merged_metadata['cnjs'] = list(set(merged_metadata['cnjs']))

    return {
        "score": score,
        "level": level,
        "analysis_status": "PROCESSED_SUCCESSFULLY",
        "hits": hits,
        "metadata": merged_metadata,
        "context_hits": context_data.get("context_hits", []),
        "html_enriched": html_enriched,  # ✅ Agora é string do dict
        "html_content": pub_html,
        "id": f"pub_{pub_index}"
    }


def mailitem_to_record(mail) -> dict:
    """Processa um e-mail inteiro e retorna estrutura hierárquica completa."""
    html_original = getattr(mail, "HTMLBody", "") or ""

    # Divide o e-mail em publicações
    publications_html = split_html_into_publications(html_original)

    # Processa cada publicação
    processed_pubs = []
    for i, pub_html in enumerate(publications_html):
        processed_data = process_publication_with_new_architecture(pub_html, pub_index=i)
        processed_pubs.append(processed_data)

    # Calcula estatísticas consolidadas
    statistics = calculate_email_statistics(processed_pubs)

    # Formata data
    dt_str = datetime.fromtimestamp(time.mktime(mail.ReceivedTime.timetuple())).strftime("%Y-%m-%d_%H%M%S")

    # ✅ CORREÇÃO: Garante que html_enriched é string antes de juntar
    html_enriched_parts = []
    for pub in processed_pubs:
        html_enriched = pub.get("html_enriched", "")
        # Se for dicionário, pega a string HTML
        if isinstance(html_enriched, dict):
            html_enriched = html_enriched.get("html", "")
        html_enriched_parts.append(html_enriched)

    # Gera HTML enriquecido combinado
    final_enriched_html = "<hr style='border-top: 2px dashed #ccc; margin: 20px 0;'>".join(html_enriched_parts)

    return {
        "email_id": mail.EntryID,
        "subject": mail.Subject or "",
        "received": dt_str,
        "total_publications": len(processed_pubs),
        "publications": processed_pubs,
        "statistics": statistics,
        "html_original": html_original,
        "html_enriched": final_enriched_html
    }


# --- FUNÇÃO PARA A UI (STREAMLIT) ---

def run_collection_with_ui_feedback(account_name: str, folder_path: str, limit: int, out_base: str, log_callback,
                                    progress_callback, debug_callback, date_params: dict):
    log_callback("INFO: Conectando ao Outlook...")
    debug_callback("Conectando...")

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        store = resolve_store_by_displayname(account_name)
        folder = get_folder(store, folder_path)
    except Exception as e:
        log_callback(f"ERRO CRÍTICO: Falha ao conectar ao Outlook: {e}")
        return None

    # FASE 1: Coleta Bruta
    log_callback("INFO: FASE 1: Coletando e-mails brutos do Outlook...")
    restrict_clause = None
    filter_type = date_params.get("filter_type", "Hoje")
    today = datetime.now()

    if filter_type == "Hoje":
        restrict_clause = f"[ReceivedTime] >= '{today.replace(hour=0, minute=0).strftime('%m/%d/%Y %H:%M %p')}'"
    elif filter_type == "Últimos 7 dias":
        restrict_clause = f"[ReceivedTime] >= '{(today - timedelta(days=7)).strftime('%m/%d/%Y %H:%M %p')}'"
    elif filter_type == "Período Customizado":
        start_date = date_params.get("start_date", today)
        end_date = date_params.get("end_date", today)
        restrict_clause = f"[ReceivedTime] >= '{datetime.combine(start_date, datetime.min.time()).strftime('%m/%d/%Y %H:%M %p')}' AND [ReceivedTime] <= '{datetime.combine(end_date, datetime.max.time()).strftime('%m/%d/%Y %H:%M %p')}'"

    items = folder.Items
    items.Sort("[ReceivedTime]", True)
    if restrict_clause:
        debug_callback(f"Aplicando filtro: {restrict_clause}")
        items = items.Restrict(restrict_clause)

    raw_emails = []
    unlimited = (limit is None) or (limit <= 0)
    mail = items.GetFirst()

    while mail and (unlimited or len(raw_emails) < limit):
        try:
            raw_emails.append(mail)
            debug_callback(f"Coletado: {mail.Subject}")
        except Exception as e:
            debug_callback(f"Erro ao ler e-mail, pulando: {e}")
        mail = items.GetNext()

    log_callback(f"INFO: FASE 1 Concluída. {len(raw_emails)} e-mails coletados.")
    if not raw_emails:
        log_callback("INFO: Nenhum e-mail encontrado.")
        return None

    # FASE 2: Processamento e Gravação
    log_callback("INFO: FASE 2: Processando e gravando e-mails...")
    total_to_process = len(raw_emails)
    progress_callback(("total", total_to_process))

    emails_data = []  # Lista para armazenar dados estruturados

    for idx, mail_item in enumerate(raw_emails):
        try:
            debug_callback(f"Processando [{idx + 1}/{total_to_process}]: {mail_item.Subject[:70]}")

            # Processa o e-mail com a nova estrutura
            email_record = mailitem_to_record(mail_item)
            emails_data.append(email_record)

            # Gera arquivos individuais
            fn_base = f"{email_record['received']}__{safe_filename(email_record['subject'])}"
            html_filename = f"{fn_base}.html"

            with open(os.path.join(out_base, "html", html_filename), "w", encoding="utf-8") as f_html:
                f_html.write(email_record.get("html_enriched", ""))

            progress_callback(("current", idx + 1))

        except Exception as e:
            log_callback(f"ERRO ao processar e-mail '{mail_item.Subject}': {e}")

    # Gera dashboard data para o Streamlit
    dashboard_data = generate_dashboard_data(emails_data)

    # Salva dados consolidados em JSON
    with open(os.path.join(out_base, "json", "dashboard_data.json"), "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    # Salva também os dados completos por e-mail
    with open(os.path.join(out_base, "json", "emails_data.json"), "w", encoding="utf-8") as f:
        json.dump(emails_data, f, ensure_ascii=False, indent=2)

    log_callback("INFO: Processo finalizado com sucesso!")
    return dashboard_data


# --- PONTO DE ENTRADA PRINCIPAL (CMD) ---

def main():
    """
    Função principal para execução via linha de comando.
    """
    print("Coletor de E-mails SJUR - Versão Completa")
    print("=" * 50)

    # Configurações padrão
    account_name = "SERDON"
    folder_path = "Inbox"
    limit = 10
    out_base = "outputs"
    date_params = {"filter_type": "Hoje"}

    try:
        # Garante que o diretório de saída existe
        ensure_outputs(out_base)

        # Funções de callback para modo console
        def log_callback(message):
            print(f"[LOG] {message}")

        def progress_callback(data):
            if data[0] == "total":
                print(f"Total de e-mails a processar: {data[1]}")
            elif data[0] == "current":
                print(f"Processado: {data[1]}")

        def debug_callback(message):
            print(f"[DEBUG] {message}")

        # Executa a coleta
        dashboard_data = run_collection_with_ui_feedback(
            account_name, folder_path, limit, out_base,
            log_callback, progress_callback, debug_callback, date_params
        )

        if dashboard_data:
            print("\n" + "=" * 50)
            print("RESUMO DA COLETA:")
            print(f"Total de E-mails: {dashboard_data['total_emails']}")
            print(f"Total de Publicações: {dashboard_data['total_publications']}")
            print(f"Publicações para Arquivar: {dashboard_data['total_archival_candidate_publications']}")
            print(f"Processos Únicos para Arquivar: {len(dashboard_data['unique_archival_processes'])}")
            print(f"Dados salvos em: {out_base}/")

    except Exception as e:
        print(f"ERRO durante a execução: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()