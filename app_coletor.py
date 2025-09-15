# app_coletor.py (VERSÃO CORRIGIDA COM VALORES PADRÃO ORIGINAIS)

import streamlit as st
from pathlib import Path
import sys, time, threading, traceback, queue, pythoncom
from datetime import datetime, timedelta

st.set_page_config(page_title="Coletor de Recortes SJUR", layout="wide")

try:
    project_root = Path(__file__).resolve().parent
    if project_root.name == 'pages': project_root = project_root.parent
    sys.path.insert(0, str(project_root))
    from scripts.coletar_emails_para_outputs import run_collection_with_ui_feedback, reset_outputs, ensure_outputs
except ImportError as e:
    st.error(f"**Erro Crítico de Importação:** `{e}`")
    st.stop()

# --- Inicialização do Estado da Sessão ---
for key, default_value in {
    'is_running': False, 'progress': 0, 'log_messages': [], 'debug_messages': [],
    'processed_count': 0, 'error_count': 0, 'status_message': "Aguardando...",
    'total_items': 0, 'dashboard_data': None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# --- Função da Thread de Coleta ---
def collection_worker(q, account, folder, limit, output_dir, reset_out, date_params):
    pythoncom.CoInitialize()
    try:
        if reset_out:
            q.put(("log", "INFO: Limpando diretório de saídas..."))
            reset_outputs(output_dir)
        else:
            ensure_outputs(output_dir)

        # Chama a função atualizada que retorna dashboard_data
        dashboard_data = run_collection_with_ui_feedback(
            account_name=account,
            folder_path=folder,
            limit=limit,
            out_base=output_dir,
            log_callback=lambda msg: q.put(("log", msg)),
            progress_callback=lambda data: q.put(("progress", data)),
            debug_callback=lambda info: q.put(("debug", info)),
            date_params=date_params
        )

        if dashboard_data:
            q.put(("dashboard", dashboard_data))
            q.put(("log", f"INFO: Coleta concluída! {dashboard_data['total_emails']} e-mails processados"))

        q.put(("status", "✅ Coleta Concluída!"))
    except Exception as e:
        q.put(("log", f"ERRO CRÍTICO NA THREAD: {e}"))
        q.put(("debug", f"❌ Erro detalhado: {traceback.format_exc()}"))
        q.put(("status", "❌ Erro na Coleta!"))
    finally:
        pythoncom.CoUninitialize()
        q.put(("finished", True))


# --- Interface Gráfica (UI) ---
st.title("🤖 Coletor de Recortes Jurídicos")
st.markdown("Interface para iniciar, parametrizar e monitorar a coleta de e-mails do Outlook.")

with st.sidebar:
    st.header("Navegação")
    st.markdown("🔬 [Analisador de Destaques](teste_destaque)")
    st.divider()
    st.header("1. Parâmetros")
    account_name = st.text_input("📧 Conta", value="SJUR Coleta Serdon")  # VALOR ORIGINAL
    folder_name = st.text_input("📁 Pasta", value="Caixa de Entrada")  # VALOR ORIGINAL
    output_folder = st.text_input("💾 Saída", value="outputs")
    st.header("2. Filtros")
    filter_type = st.radio("Data", ["Hoje", "Últimos 7 dias", "Período Customizado", "Tudo"],
                           horizontal=True, key="filter_type")
    if filter_type == "Período Customizado":
        c1, c2 = st.columns(2)
        st.session_state.start_date_input = c1.date_input("Início", datetime.now() - timedelta(days=7))
        st.session_state.end_date_input = c2.date_input("Fim", datetime.now())
    limit_emails = st.number_input("Limite de e-mails (0=sem limite)", min_value=0, value=10, key="limit_emails")
    reset_out = st.checkbox("Limpar pasta de saída", value=True, key="reset_out")

# --- Botão de Ação ---
st.header("3. Execução e Monitoramento")
if st.button("🚀 Iniciar Coleta", type="primary", disabled=st.session_state.is_running):
    # Reseta o estado da UI para uma nova execução
    st.session_state.log_messages = []
    st.session_state.debug_messages = []
    st.session_state.progress = 0
    st.session_state.total_items = 0
    st.session_state.processed_count = 0
    st.session_state.error_count = 0
    st.session_state.dashboard_data = None

    st.session_state.is_running = True
    st.session_state.status_message = "🔄 Coleta em andamento..."

    # Prepara os parâmetros para a thread
    date_params = {"filter_type": st.session_state.filter_type}
    if st.session_state.filter_type == "Período Customizado":
        date_params.update({
            "start_date": st.session_state.start_date_input,
            "end_date": st.session_state.end_date_input
        })

    # Inicia a thread
    q = queue.Queue()
    thread = threading.Thread(
        target=collection_worker,
        args=(q, account_name, folder_name, limit_emails, output_folder, reset_out, date_params),
        daemon=True
    )
    thread.start()
    st.session_state.thread_queue = q
    st.rerun()

# --- Área de Monitoramento ---
st.info(st.session_state.status_message)
progress_value = (st.session_state.progress / st.session_state.total_items) if st.session_state.total_items > 0 else 0
progress_text = f"Processando... {st.session_state.progress}/{st.session_state.total_items}" if st.session_state.is_running else "Concluído"
st.progress(progress_value, text=progress_text)

c1, c2, c3 = st.columns(3)
c1.metric("E-mails Processados", st.session_state.processed_count)
c2.metric("Erros Encontrados", st.session_state.error_count)
c3.metric("Status", "Executando" if st.session_state.is_running else "Parado")

# --- Exibir Estatísticas se disponíveis ---
if st.session_state.dashboard_data:
    st.header("📊 Estatísticas da Coleta")
    data = st.session_state.dashboard_data
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de E-mails", data["total_emails"])
    col2.metric("Total de Publicações", data["total_publications"])
    col3.metric("Para Arquivar", data["total_archival_candidate_publications"])
    col4.metric("Processos Únicos", len(data["unique_archival_processes"]))

log_tab, debug_tab = st.tabs(["Console de Log", "Log de Debug"])
with log_tab:
    log_container = st.container(height=300)
    for msg in reversed(st.session_state.log_messages):
        if "ERRO" in msg:
            log_container.error(msg)
        elif "INFO" in msg:
            log_container.info(msg)
        else:
            log_container.text(msg)
with debug_tab:
    debug_container = st.container(height=300)
    for msg in reversed(st.session_state.debug_messages):
        debug_container.text(msg)

# --- Processamento da Fila e Auto-refresh ---
if st.session_state.is_running:
    try:
        while not st.session_state.thread_queue.empty():
            item_type, data = st.session_state.thread_queue.get_nowait()
            timestamp = f"[{datetime.now().strftime('%H:%M:%S')}]"

            if item_type == "log":
                st.session_state.log_messages.append(f"{timestamp} {data}")
                if "ERRO" in data:
                    st.session_state.error_count += 1
            elif item_type == "debug":
                st.session_state.debug_messages.append(f"{timestamp} {data}")
            elif item_type == "progress":
                p_type, p_value = data
                if p_type == "total":
                    st.session_state.total_items = p_value
                elif p_type == "current":
                    st.session_state.progress = p_value
                    st.session_state.processed_count = p_value
            elif item_type == "status":
                st.session_state.status_message = data
            elif item_type == "dashboard":
                st.session_state.dashboard_data = data
            elif item_type == "finished":
                st.session_state.is_running = False

        time.sleep(0.5)
        st.rerun()
    except queue.Empty:
        time.sleep(0.5)
        st.rerun()