# app_coletor_sincronizado.py - VERSÃO FINAL CORRIGIDA

# 1. STREAMLIT PRIMEIRO - SEM EXCEÇÕES
import streamlit as st

# 2. set_page_config() PRIMEIRO COMANDO - APENAS UMA VEZ!
st.set_page_config(
    page_title="Coletor de SERDON Recortes SJUR",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 3. DEMAIS IMPORTS APÓS O set_page_config()
from pathlib import Path
import sys
import time
import threading
import traceback
import queue
import pythoncom
import os
from datetime import datetime, timedelta
import json

# 4. IMPORTS PERSONALIZADOS
try:
    from shared.shared_config import shared_config, get_output_folder, set_output_folder, get_data_paths
except ImportError:
    st.error("**Erro:** Módulo `shared_config.py` não encontrado. Certifique-se de que está no mesmo diretório.")
    st.stop()

try:
    project_root = Path(__file__).resolve().parent
    if project_root.name == 'pages':
        project_root = project_root.parent
    sys.path.insert(0, str(project_root))
    from scripts.coletar_emails_para_outputs import run_collection_with_ui_feedback, reset_outputs, ensure_outputs
except ImportError as e:
    st.error(f"**Erro Crítico de Importação:** `{e}`")
    st.stop()

# --- Configurações e Constantes ---
RECENT_FOLDERS_FILE = "recent_folders.json"
DEFAULT_OUTPUT_FOLDER = "outputs"
MAX_RECENT_FOLDERS = 5

# Prevenir timeout
def prevent_streamlit_timeout():
    """Mantém a conexão ativa durante processos longos"""
    placeholder = st.empty()
    start_time = time.time()

    while st.session_state.is_running:
        elapsed = time.time() - start_time
        placeholder.info(f"🔄 Processando... {elapsed:.0f}s decorridos")
        time.sleep(5)  # Atualiza a cada 5 segundos

# --- Funções Auxiliares para Gerenciamento de Pastas ---
@st.cache_data
def get_system_folders():
    """Retorna pastas do sistema comumente usadas"""
    home = Path.home()
    folders = {
        "🏠 Pasta Pessoal": str(home),
        "🖥️ Desktop": str(home / "Desktop") if (home / "Desktop").exists() else str(home),
        "📁 Documentos": str(home / "Documents") if (home / "Documents").exists() else str(home),
        "📥 Downloads": str(home / "Downloads") if (home / "Downloads").exists() else str(home),
        "📂 Pasta Atual": str(Path.cwd()),
    }
    return {k: v for k, v in folders.items() if Path(v).exists()}

def load_recent_folders():
    """Carrega pastas recentemente usadas"""
    try:
        if Path(RECENT_FOLDERS_FILE).exists():
            with open(RECENT_FOLDERS_FILE, 'r', encoding='utf-8') as f:
                recent = json.load(f)
                # Filtra apenas pastas que ainda existem
                return [folder for folder in recent if Path(folder).exists()]
    except Exception:
        pass
    return []

def save_recent_folder(folder_path):
    """Salva pasta na lista de recentes"""
    try:
        recent = load_recent_folders()
        folder_path = str(Path(folder_path).resolve())

        # Remove se já existe e adiciona no início
        if folder_path in recent:
            recent.remove(folder_path)
        recent.insert(0, folder_path)

        # Mantém apenas os últimos MAX_RECENT_FOLDERS
        recent = recent[:MAX_RECENT_FOLDERS]

        with open(RECENT_FOLDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def validate_folder_path(path_str):
    """Valida e normaliza caminho da pasta"""
    try:
        path = Path(path_str).resolve()

        if not path_str.strip():
            return False, "❌ Caminho não pode estar vazio"

        if path.exists() and not path.is_dir():
            return False, "❌ Caminho existe mas não é uma pasta"

        if not path.exists():
            return "create", f"📁 Pasta será criada: {path}"

        if not os.access(path, os.W_OK):
            return False, "❌ Sem permissão de escrita na pasta"

        return True, f"✅ Pasta válida: {path}"

    except Exception as e:
        return False, f"❌ Caminho inválido: {str(e)}"

def create_folder_if_needed(path_str):
    """Cria pasta se necessário"""
    try:
        path = Path(path_str)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return True, f"✅ Pasta criada: {path}"
        return True, f"✅ Pasta já existe: {path}"
    except Exception as e:
        return False, f"❌ Erro ao criar pasta: {str(e)}"

# --- Interface de Seleção de Pasta Sincronizada ---
def render_folder_selector():
    """Renderiza o seletor de pasta com sincronização"""
    st.subheader("📂 Seleção de Pasta de Saída (Sincronizada)")

    # Inicializa o estado com a configuração compartilhada
    if 'selected_output_folder' not in st.session_state:
        st.session_state.selected_output_folder = get_output_folder()
    if 'folder_validation_status' not in st.session_state:
        st.session_state.folder_validation_status = None

    # Mostra informações de sincronização
    config_info = shared_config.get_config_info()
    with st.expander("ℹ️ Informações de Sincronização", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Pasta Atual:** `{config_info['output_folder']}`")
            st.info(f"**Última Atualização:** {config_info['last_updated'][:19]}")
        with col2:
            st.info(f"**Atualizado Por:** {config_info['updated_by']}")

            # Botão para detectar automaticamente
            if st.button("🔍 Detectar Pasta Automaticamente"):
                detected = shared_config.auto_detect_data_folder()
                if detected:
                    st.session_state.selected_output_folder = detected
                    st.session_state.folder_validation_status = None
                    st.success(f"✅ Pasta detectada: {detected}")
                    st.rerun()
                else:
                    st.warning("⚠️ Nenhuma pasta com dados encontrada")

    # Layout em colunas
    col1, col2 = st.columns([3, 1])

    with col1:
        # Campo principal de entrada
        folder_input = st.text_input(
            "Caminho da pasta de saída:",
            value=st.session_state.selected_output_folder,
            placeholder="Digite o caminho ou use os botões abaixo...",
            help="Pasta onde serão salvos os arquivos coletados (sincronizada com o analisador)"
        )

        # Atualiza o estado quando o input muda
        if folder_input != st.session_state.selected_output_folder:
            st.session_state.selected_output_folder = folder_input
            st.session_state.folder_validation_status = None

    with col2:
        # Botão de validação
        if st.button("🔍 Validar", help="Verificar se a pasta é válida"):
            is_valid, message = validate_folder_path(st.session_state.selected_output_folder)
            st.session_state.folder_validation_status = (is_valid, message)

    # Exibe status de validação
    if st.session_state.folder_validation_status:
        is_valid, message = st.session_state.folder_validation_status
        if is_valid == True:
            st.success(message)
        elif is_valid == "create":
            st.warning(message)
        else:
            st.error(message)

    # Seção de acesso rápido
    st.markdown("**🚀 Acesso Rápido:**")

    # Botões de pastas do sistema
    system_folders = get_system_folders()
    cols = st.columns(len(system_folders))

    for i, (name, path) in enumerate(system_folders.items()):
        with cols[i]:
            if st.button(name, key=f"sys_folder_{i}", help=f"Usar: {path}"):
                st.session_state.selected_output_folder = path
                st.session_state.folder_validation_status = None
                st.rerun()

    # Pastas recentes
    recent_folders = load_recent_folders()
    if recent_folders:
        st.markdown("**🕒 Pastas Recentes:**")

        # Cria colunas para as pastas recentes
        num_cols = min(3, len(recent_folders))
        cols = st.columns(num_cols)

        for i, folder in enumerate(recent_folders[:num_cols]):
            with cols[i % num_cols]:
                folder_name = Path(folder).name or "Raiz"
                if st.button(f"📁 {folder_name}", key=f"recent_{i}", help=folder):
                    st.session_state.selected_output_folder = folder
                    st.session_state.folder_validation_status = None
                    st.rerun()

    # Pastas com dados disponíveis
    available_folders = shared_config.find_available_data_folders()
    if available_folders and len(available_folders) > 1:
        st.markdown("**📊 Pastas com Dados Disponíveis:**")
        cols = st.columns(min(3, len(available_folders)))

        for i, folder in enumerate(available_folders[:3]):
            with cols[i]:
                folder_name = Path(folder).name or folder
                if st.button(f"📊 {folder_name}", key=f"data_folder_{i}", help=f"Pasta com dados: {folder}"):
                    st.session_state.selected_output_folder = folder
                    st.session_state.folder_validation_status = None
                    st.rerun()

    # Navegador de diretórios (expandível)
    with st.expander("🗂️ Navegador de Diretórios", expanded=False):
        render_directory_browser()

    return st.session_state.selected_output_folder

def render_directory_browser():
    """Renderiza um navegador de diretórios simples"""
    if 'browser_current_path' not in st.session_state:
        st.session_state.browser_current_path = str(Path.home())

    current_path = Path(st.session_state.browser_current_path)

    # Navegação para pasta pai
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("⬆️ Voltar", disabled=current_path == current_path.parent):
            st.session_state.browser_current_path = str(current_path.parent)
            st.rerun()

    with col2:
        st.text(f"📍 {current_path}")

    # Lista diretórios
    try:
        directories = [d for d in current_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        directories.sort(key=lambda x: x.name.lower())

        if directories:
            # Mostra até 10 diretórios por vez
            for directory in directories[:10]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"📁 {directory.name}")
                with col2:
                    if st.button("Entrar", key=f"enter_{directory.name}"):
                        st.session_state.browser_current_path = str(directory)
                        st.rerun()
                    if st.button("Usar", key=f"use_{directory.name}"):
                        st.session_state.selected_output_folder = str(directory)
                        st.session_state.folder_validation_status = None
                        st.rerun()
        else:
            st.info("Nenhuma pasta encontrada neste diretório")

    except PermissionError:
        st.error("❌ Sem permissão para acessar este diretório")
    except Exception as e:
        st.error(f"❌ Erro ao listar diretórios: {str(e)}")

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
    """
    Worker thread com checkpoints para processos extremamente longos.
    """
    pythoncom.CoInitialize()
    last_keepalive = time.time()
    keepalive_interval = 20
    checkpoint_interval = 10  # E-mails entre checkpoints

    try:
        q.put(("status", "🔄 Iniciando coleta..."))
        q.put(("log", "INFO: Iniciando processo de coleta de e-mails"))

        if reset_out:
            q.put(("log", "INFO: Limpando diretório de saídas..."))
            reset_outputs(output_dir)
        else:
            ensure_outputs(output_dir)

        # Keep-alive automático
        def send_keepalive_if_needed(context=""):
            nonlocal last_keepalive
            current_time = time.time()
            if current_time - last_keepalive >= keepalive_interval:
                q.put(("keepalive", f"Processo ativo - {context}"))
                last_keepalive = current_time
                return True
            return False

        # Callbacks personalizados
        def log_callback_enhanced(msg):
            send_keepalive_if_needed(f"Log: {msg[:30]}")
            q.put(("log", msg))

        def progress_callback_enhanced(data):
            if send_keepalive_if_needed(f"Progresso: {data}"):
                # Envia estatísticas periódicas
                if isinstance(data, tuple) and data[0] == "current":
                    q.put(("checkpoint", {
                        "processed": data[1],
                        "timestamp": time.time(),
                        "message": f"Checkpoint: {data[1]} e-mails processados"
                    }))
            q.put(("progress", data))

        def debug_callback_enhanced(info):
            send_keepalive_if_needed("Debug")
            q.put(("debug", info))

        # Keep-alive inicial
        q.put(("keepalive", "Thread de coleta iniciada - Pré-processamento"))

        # Executa a coleta
        dashboard_data = run_collection_with_ui_feedback(
            account_name=account,
            folder_path=folder,
            limit=limit,
            out_base=output_dir,
            log_callback=log_callback_enhanced,
            progress_callback=progress_callback_enhanced,
            debug_callback=debug_callback_enhanced,
            date_params=date_params
        )

        # Processa resultados finais
        if dashboard_data:
            q.put(("dashboard", dashboard_data))
            summary_msg = (
                f"INFO: RESUMO - {dashboard_data['total_emails']} e-mails, "
                f"{dashboard_data['total_publications']} publicações, "
                f"{dashboard_data['total_archival_candidate_publications']} para arquivamento"
            )
            q.put(("log", summary_msg))

        q.put(("status", "✅ Coleta Concluída!"))
        q.put(("log", "INFO: Processo finalizado com sucesso"))

    except Exception as e:
        error_msg = f"ERRO CRÍTICO: {str(e)}"
        q.put(("log", error_msg))
        q.put(("debug", f"Traceback: {traceback.format_exc()}"))
        q.put(("status", "❌ Falha na Coleta"))
        q.put(("error", error_msg))

    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

        q.put(("finished", True))
        q.put(("keepalive", "Processo finalizado"))  # Keep-alive final

# --- Interface Gráfica Principal ---
st.title("🤖 Coletor de Recortes Jurídicos (Sincronizado)")
st.markdown("Interface profissional com sincronização automática entre coletor e analisador.")

with st.sidebar:
    st.header("Navegação")
    st.markdown("🔬 [Analisador de Destaques](teste_destaque)")
    st.divider()

    st.header("1. Parâmetros Básicos")
    account_name = st.text_input("📧 Conta", value="SJUR Coleta Serdon")
    folder_name = st.text_input("📁 Pasta", value="Caixa de Entrada")

    st.header("2. Filtros de Data")
    filter_type = st.radio("Período", ["Hoje", "Últimos 7 dias", "Período Customizado", "Tudo"],
                           horizontal=True, key="filter_type")
    if filter_type == "Período Customizado":
        c1, c2 = st.columns(2)
        st.session_state.start_date_input = c1.date_input("Início", datetime.now() - timedelta(days=7))
        st.session_state.end_date_input = c2.date_input("Fim", datetime.now())

    limit_emails = st.number_input("Limite de e-mails (0=sem limite)", min_value=0, value=10, key="limit_emails")
    reset_out = st.checkbox("Limpar pasta de saída", value=True, key="reset_out")

# --- Seletor de Pasta Sincronizado ---
output_folder = render_folder_selector()

# --- Botão de Ação ---
st.header("🚀 Execução e Monitoramento")

# Validação antes de permitir execução
can_execute = True
execution_issues = []

# Verifica se a pasta de saída é válida
is_valid, validation_message = validate_folder_path(output_folder)
if is_valid == False:
    can_execute = False
    execution_issues.append(validation_message)
elif is_valid == "create":
    st.info(f"💡 {validation_message}")

if execution_issues:
    for issue in execution_issues:
        st.error(issue)

if st.button("🚀 Iniciar Coleta", type="primary", disabled=st.session_state.is_running or not can_execute):
    # Cria pasta se necessário
    if is_valid == "create":
        success, create_message = create_folder_if_needed(output_folder)
        if not success:
            st.error(create_message)
            st.stop()
        else:
            st.success(create_message)

    # ✅ SINCRONIZAÇÃO: Salva pasta na configuração compartilhada
    if set_output_folder(output_folder, "coletor"):
        st.success(f"🔄 Configuração sincronizada: {output_folder}")
    else:
        st.warning("⚠️ Erro ao sincronizar configuração, mas coleta continuará")

    # Salva pasta nos recentes
    save_recent_folder(output_folder)

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

# --- Logs ---
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