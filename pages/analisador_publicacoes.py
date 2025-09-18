# pages/analisador_publicacoes_sincronizado.py - VERSÃO COM SINCRONIZAÇÃO

import streamlit as st
from pathlib import Path
import sys
import json
import os
import pandas as pd
from datetime import datetime
import re
from io import BytesIO

# Importa módulo de configuração compartilhada
try:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    from shared.shared_config import (shared_config, get_output_folder, set_output_folder, get_data_paths,
                                      check_data_availability)
except ImportError:
    st.error(
        "**Erro:** Módulo `shared_config.py` não encontrado. Certifique-se de que está no diretório raiz do projeto.")
    st.stop()

# Configuração da página
st.set_page_config(page_title="Analisador de Publicações SJUR", layout="wide")
st.title("📊 Analisador de Publicações e Estatísticas SJUR (Sincronizado)")

try:
    from app.rules.archival_rules import sjur_rules
    from app.styles.analytical_highlighter import highlight_html_analytical
except ImportError as e:
    st.error(f"**Erro Crítico de Importação:** `{e}`")
    st.stop()

# Inicialização do estado da sessão
if 'dashboard_data' not in st.session_state:
    st.session_state.dashboard_data = None
if 'selected_email_index' not in st.session_state:
    st.session_state.selected_email_index = 0
if 'selected_publication_index' not in st.session_state:
    st.session_state.selected_publication_index = 0
if 'html_files_map' not in st.session_state:
    st.session_state.html_files_map = {}
if 'filter_positive_scores' not in st.session_state:
    st.session_state.filter_positive_scores = True
if 'current_data_folder' not in st.session_state:
    st.session_state.current_data_folder = get_output_folder()


# --- Interface de Configuração de Pasta ---
def render_folder_configuration():
    """Renderiza interface para configuração da pasta de dados"""
    st.subheader("📂 Configuração de Pasta de Dados (Sincronizada)")

    # Informações da configuração atual
    config_info = shared_config.get_config_info()
    data_availability = check_data_availability()

    col1, col2 = st.columns(2)

    with col1:
        st.info(f"**Pasta Configurada:** `{config_info['output_folder']}`")
        st.info(f"**Última Atualização:** {config_info['last_updated'][:19]}")
        st.info(f"**Atualizado Por:** {config_info['updated_by']}")

    with col2:
        # Status dos dados
        if data_availability['dashboard_data'] and data_availability['emails_data']:
            st.success("✅ **Dados Disponíveis**")
            st.success(f"✅ Dashboard: {data_availability['dashboard_data']}")
            st.success(f"✅ E-mails: {data_availability['emails_data']}")
        else:
            st.error("❌ **Dados Não Encontrados**")
            st.error(f"❌ Dashboard: {data_availability['dashboard_data']}")
            st.error(f"❌ E-mails: {data_availability['emails_data']}")

    # Botões de ação
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Atualizar Dados"):
            st.session_state.dashboard_data = None
            st.session_state.emails_data = None
            st.session_state.html_files_map = {}
            st.session_state.current_data_folder = get_output_folder()
            st.rerun()

    with col2:
        if st.button("🔍 Detectar Automaticamente"):
            detected = shared_config.auto_detect_data_folder()
            if detected:
                if set_output_folder(detected, "analisador"):
                    st.session_state.current_data_folder = detected
                    st.success(f"✅ Pasta detectada e configurada: {detected}")
                    st.rerun()
                else:
                    st.error("❌ Erro ao configurar pasta detectada")
            else:
                st.warning("⚠️ Nenhuma pasta com dados encontrada")

    with col3:
        # Seletor manual de pasta
        available_folders = shared_config.find_available_data_folders()
        if available_folders:
            selected_folder = st.selectbox(
                "Selecionar pasta:",
                options=available_folders,
                index=0 if config_info['output_folder'] not in available_folders else available_folders.index(
                    config_info['output_folder']),
                key="folder_selector"
            )

            if st.button("✅ Usar Pasta Selecionada"):
                if set_output_folder(selected_folder, "analisador"):
                    st.session_state.current_data_folder = selected_folder
                    st.success(f"✅ Pasta configurada: {selected_folder}")
                    st.rerun()
                else:
                    st.error("❌ Erro ao configurar pasta")


# --- Funções Auxiliares Atualizadas ---
def load_dashboard_data():
    """Carrega os dados do dashboard JSON usando configuração compartilhada"""
    data_paths = get_data_paths()
    json_path = data_paths['dashboard_data']

    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
    return None


def load_emails_data():
    """Carrega os dados completos dos e-mails usando configuração compartilhada"""
    data_paths = get_data_paths()
    json_path = data_paths['emails_data']

    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar dados dos e-mails: {e}")
    return None


def get_html_files_map():
    """Mapeia os arquivos HTML para os e-mails usando configuração compartilhada"""
    data_paths = get_data_paths()
    html_folder = data_paths['html']
    html_files_map = {}

    if os.path.exists(html_folder):
        for filename in os.listdir(html_folder):
            if filename.endswith('.html'):
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{6})', filename)
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    html_files_map[timestamp] = filename
    return html_files_map


def find_html_filename(email_data):
    """Encontra o nome do arquivo HTML correspondente ao e-mail"""
    email_timestamp = email_data['received']
    return st.session_state.html_files_map.get(email_timestamp, "Arquivo não encontrado")


def filter_publications_by_score(publications, filter_positive=True):
    """Filtra publicações por score (apenas scores > 0 se filter_positive=True)"""
    if not filter_positive:
        return publications
    return [pub for pub in publications if pub.get('score', 0) > 0]


def generate_analytical_view(html_content: str) -> str:
    """Gera a visualização analítica completa usando o módulo dedicado"""
    if not html_content:
        return ""

    try:
        return highlight_html_analytical(html_content)
    except Exception as e:
        st.error(f"Erro ao gerar visualização analítica: {e}")
        return f"<pre>{html_content}</pre>"


def analyze_determinant_rules(hits_data: dict) -> list:
    """Analisa apenas as regras determinantes (score) que deram match"""
    sjur_rules.load_all_rules()

    determinant_rules = []

    for rule_id, hit_details in hits_data.items():
        # Verifica se é uma regra determinante
        if rule_id in sjur_rules.determinant_rules:
            rule_data = sjur_rules.determinant_rules[rule_id]
            description = rule_data.get("description", "Sem descrição")
            score_value = rule_data.get("score", 0)

            determinant_rules.append({
                "id": rule_id,
                "description": description,
                "score": score_value,
                "details": hit_details,
                "contribution": score_value
            })

    # Ordena por contribuição (maior primeiro)
    determinant_rules.sort(key=lambda x: x["contribution"], reverse=True)

    return determinant_rules


# --- Interface de Configuração ---
render_folder_configuration()

# --- Carregamento dos Dados ---
if st.session_state.dashboard_data is None:
    st.session_state.dashboard_data = load_dashboard_data()
if 'emails_data' not in st.session_state:
    st.session_state.emails_data = load_emails_data()
if not st.session_state.html_files_map:
    st.session_state.html_files_map = get_html_files_map()

# --- Verificação de Dados ---
if not st.session_state.dashboard_data or not st.session_state.emails_data:
    st.warning(f"""
    **Dados não encontrados na pasta configurada!**

    **Pasta atual:** `{get_output_folder()}`

    **Para resolver:**
    1. Execute o coletor de e-mails para gerar os dados
    2. Use "🔍 Detectar Automaticamente" para encontrar dados existentes
    3. Selecione manualmente uma pasta com dados válidos
    4. Clique em "🔄 Atualizar Dados" após configurar

    **Arquivos necessários:**
    - `{get_data_paths()['dashboard_data']}`
    - `{get_data_paths()['emails_data']}`
    """)
    st.stop()

data = st.session_state.dashboard_data

# --- Dashboard Principal ---
with st.expander("📈 Visão Geral da Coleta", expanded=False):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de E-mails", data["total_emails"])
    col2.metric("Total de Publicações", data["total_publications"])
    col3.metric("Para Arquivar", data["total_archival_candidate_publications"],
                f"{data['total_archival_candidate_publications'] / data['total_publications'] * 100:.1f}%")
    col4.metric("Processos Únicos", len(data["unique_archival_processes"]))

    if data["total_publications"] > 0:
        chart_data = pd.DataFrame({
            'Categoria': ['Para Arquivar', 'Não Arquivar'],
            'Quantidade': [
                data["total_archival_candidate_publications"],
                data["total_publications"] - data["total_archival_candidate_publications"]
            ]
        })
        st.bar_chart(chart_data.set_index('Categoria'))

# --- Navegação por E-mails ---
with st.expander("📧 Navegação por E-mails", expanded=False):
    # Seleção de e-mail com identificação por arquivo HTML
    email_options = []
    for i, email in enumerate(data["emails"]):
        html_filename = find_html_filename(email)
        short_subject = email['subject'][:40] + "..." if len(email['subject']) > 40 else email['subject']
        email_options.append(
            f"{i + 1}. {html_filename} - {short_subject} ({email['total_publications']} pubs)"
        )

    selected_email = st.selectbox(
        "Selecione um e-mail para analisar:",
        options=range(len(data["emails"])),
        format_func=lambda x: email_options[x],
        index=st.session_state.selected_email_index
    )

    st.session_state.selected_email_index = selected_email
    selected_email_data = data["emails"][selected_email]
    html_filename = find_html_filename(selected_email_data)

    # Estatísticas do e-mail selecionado
    st.subheader(f"📋 E-mail: {selected_email_data['subject']}")
    st.caption(f"📁 Arquivo HTML: `{html_filename}`")
    st.caption(f"⏰ Recebido em: {selected_email_data['received']}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Publicações", selected_email_data['total_publications'])
    col2.metric("Para Arquivar", selected_email_data['statistics']['total_archival_candidates'])
    col3.metric("Processos Arquivar", len(selected_email_data['statistics']['archival_processes']))
    col4.metric("Processos Não Arquivar", len(selected_email_data['statistics']['non_archival_processes']))

    # Botão para abrir o arquivo HTML
    data_paths = get_data_paths()
    html_filepath = os.path.join(data_paths['html'], html_filename)

    if os.path.exists(html_filepath):
        with open(html_filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()

        if st.button("📂 Abrir HTML Original Completo", key="open_html_btn"):
            st.components.v1.html(html_content, height=800, scrolling=True)
    else:
        st.warning(f"Arquivo HTML não encontrado: {html_filename}")

# --- Análise de Publicações ---
st.header("📄 Análise de Publicações")

if selected_email_data['total_publications'] > 0:
    # Filtro para scores maiores que zero
    st.subheader("🔍 Filtros de Análise")
    col1, col2 = st.columns(2)

    with col1:
        filter_positive = st.checkbox(
            "Mostrar apenas publicações com indícios de arquivamento (score > 0)",
            value=st.session_state.filter_positive_scores,
            key="filter_positive_checkbox"
        )
        st.session_state.filter_positive_scores = filter_positive

    with col2:
        if st.button("✅ Exportar Apenas com Indícios", type="primary"):
            # Função de exportação (mantida igual ao original)
            def get_determinant_rules_names_inline(hits_data):
                if not hits_data:
                    return ""

                rule_names = []
                for rule_id, hit_details in hits_data.items():
                    if rule_id in sjur_rules.determinant_rules:
                        rule_data = sjur_rules.determinant_rules[rule_id]
                        description = rule_data.get("description", rule_id)
                        rule_names.append(f"{description} (match: {hit_details})")
                    else:
                        rule_names.append(f"{rule_id} (match: {hit_details})")
                return "; ".join(rule_names)


            def clean_text(text):
                if not text or not isinstance(text, str):
                    return text
                try:
                    return text.encode('latin-1').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    return text


            export_data = []
            for email in st.session_state.emails_data:
                html_filename = find_html_filename(email)
                html_filename_clean = clean_text(html_filename)
                email_subject_clean = clean_text(email['subject'])

                for i, pub in enumerate(email['publications']):
                    if pub.get('score', 0) > 0:
                        processos = pub['metadata'].get('cnjs', [])
                        processos_str = "; ".join(processos) if processos else "Nenhum"

                        tribunal = clean_text(pub['metadata'].get('tribunal', ''))
                        secretaria = clean_text(pub['metadata'].get('secretaria', ''))
                        data_publicacao = clean_text(pub['metadata'].get('data_publicacao', ''))

                        regras_determinantes = get_determinant_rules_names_inline(pub.get('hits', {}))

                        export_data.append({
                            'Arquivo_HTML': html_filename_clean,
                            'Email_Assunto': email_subject_clean,
                            'Email_Data': email['received'],
                            'Publicacao_Index': i + 1,
                            'Score_Total': pub['score'],
                            'Nivel': clean_text(pub['level']),
                            'Processos_Encontrados': processos_str,
                            'Regras_Determinantes': regras_determinantes,
                            'Tribunal': tribunal,
                            'Secretaria': secretaria,
                            'Data_Publicacao': data_publicacao,
                            'Status_Analise': clean_text(pub['analysis_status']),
                            'Total_Processos': len(processos),
                            'Total_Regras': len(pub.get('hits', {}))
                        })

            if export_data:
                df = pd.DataFrame(export_data)
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Publicações com Indícios')

                excel_data = excel_buffer.getvalue()
                st.download_button(
                    label="⬇️ Baixar Excel com Indícios",
                    data=excel_data,
                    file_name=f"publicacoes_com_indicios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success(f"✅ Exportadas {len(export_data)} publicações com indícios de arquivamento")
            else:
                st.warning("⚠️ Nenhuma publicação com indícios de arquivamento encontrada")

    # Filtra as publicações conforme o filtro
    publications_to_show = filter_publications_by_score(
        st.session_state.emails_data[selected_email]['publications'],
        filter_positive
    )

    if not publications_to_show:
        st.warning("Nenhuma publicação encontrada com os critérios de filtro selecionados.")
        if filter_positive:
            st.info(
                "Tente desativar o filtro 'Mostrar apenas publicações com indícios de arquivamento' para ver todas as publicações.")
    else:
        # Resto da interface de análise de publicações (mantida igual ao original)
        pub_options = []
        pub_mapping = []

        for i, pub in enumerate(publications_to_show):
            original_index = st.session_state.emails_data[selected_email]['publications'].index(pub)
            pub_options.append(f"Pub {original_index + 1} - Score: {pub['score']:.2f} - {pub['level']}")
            pub_mapping.append(original_index)

        selected_pub_filtered = st.selectbox(
            "Selecione uma publicação para análise detalhada:",
            options=range(len(publications_to_show)),
            format_func=lambda x: pub_options[x],
            index=min(st.session_state.selected_publication_index, len(publications_to_show) - 1)
        )

        selected_pub_original = pub_mapping[selected_pub_filtered]
        publication = publications_to_show[selected_pub_filtered]
        st.session_state.selected_publication_index = selected_pub_original

        # Detalhes da publicação
        st.subheader(f"📋 Publicação {selected_pub_original + 1}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Score", f"{publication['score']:.2f}")
        col2.metric("Nível", publication['level'])
        col3.metric("Status", publication['analysis_status'])
        cnjs_count = len(publication['metadata'].get('cnjs', []))
        col4.metric("CNJs Encontrados", cnjs_count)

        # Visualização analítica
        if html_filename != "Arquivo não encontrado":
            data_paths = get_data_paths()
            html_filepath = os.path.join(data_paths['html'], html_filename)

            if os.path.exists(html_filepath):
                with open(html_filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                if st.button("🔬 Visualização Analítica", key="analytical_view_btn"):
                    analytical_html = generate_analytical_view(html_content)
                    st.components.v1.html(analytical_html, height=800, scrolling=True)

        # Análise de regras determinantes
        if publication.get('hits'):
            determinant_rules = analyze_determinant_rules(publication['hits'])
            if determinant_rules:
                st.subheader("🎯 Regras Determinantes (Score)")
                for rule in determinant_rules:
                    with st.expander(f"⚖️ {rule['description']} (Score: {rule['score']:.2f})"):
                        st.write(f"**ID da Regra:** `{rule['id']}`")
                        st.write(f"**Contribuição:** {rule['contribution']:.2f}")
                        st.write(f"**Detalhes do Match:** {rule['details']}")
            else:
                st.info("📭 Nenhuma regra de score encontrou match nesta publicação")

else:
    st.info("Este e-mail não contém publicações.")

# --- Lista de Processos ---
with st.expander("📋 Lista de Processos por Categoria", expanded=False):
    if selected_email_data['statistics']['archival_processes'] or selected_email_data['statistics'][
        'non_archival_processes']:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("✅ Processos para Arquivar")
            if selected_email_data['statistics']['archival_processes']:
                for cnj in selected_email_data['statistics']['archival_processes']:
                    st.code(cnj)
            else:
                st.info("Nenhum processo para arquivar")

        with col2:
            st.subheader("❌ Processos Não Arquivar")
            if selected_email_data['statistics']['non_archival_processes']:
                for cnj in selected_email_data['statistics']['non_archival_processes']:
                    st.code(cnj)
            else:
                st.info("Nenhum processo não arquivado")
    else:
        st.warning("⚠️ Nenhum processo CNJ foi extraído das publicações!")

st.success("✅ Análise concluída! Use os controles acima para navegar pelos dados.")
