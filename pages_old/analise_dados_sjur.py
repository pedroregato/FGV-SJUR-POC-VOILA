# pages/analisador_publicacoes.py (VERSÃO FINAL CORRIGIDA)

import streamlit as st
from pathlib import Path
import sys
import json
import os
import pandas as pd
from datetime import datetime
import re

# Configuração da página
st.set_page_config(page_title="Analisador de Publicações SJUR", layout="wide")
st.title("📊 Analisador de Publicações e Estatísticas SJUR")

# --- IMPORTS E INICIALIZAÇÃO ---
try:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    from app.rules.archival_rules import sjur_rules
    from app.styles.analytical_highlighter import highlight_html_analytical

    # Carrega as regras imediatamente
    sjur_rules.load_all_rules()

except ImportError as e:
    st.error(f"**Erro Crítico de Importação:** `{e}`")
    st.stop()


# --- FUNÇÃO GET_DETERMINANT_RULES_NAMES DEFINIDA GLOBALMENTE ---
def get_determinant_rules_names(hits_data: dict) -> str:
    """Retorna os nomes das regras determinantes separados por ponto e vírgula"""
    if not hits_data:
        return ""

    rule_names = []

    for rule_id in hits_data.keys():
        if rule_id in sjur_rules.determinant_rules:
            rule_data = sjur_rules.determinant_rules[rule_id]
            description = rule_data.get("description", rule_id)
            rule_names.append(description)

    return "; ".join(rule_names)


# --- FUNÇÕES AUXILIARES ---
def load_dashboard_data():
    """Carrega os dados do dashboard JSON"""
    json_path = "outputs/json/dashboard_data.json"
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
    return None


def load_emails_data():
    """Carrega os dados completos dos e-mails"""
    json_path = "outputs/json/emails_data.json"
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar dados dos e-mails: {e}")
    return None


def get_html_files_map():
    """Mapeia os arquivos HTML para os e-mails"""
    html_folder = "outputs/html"
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
    """Gera a visualização analítica completa usando o módulo dedicado."""
    if not html_content:
        return ""

    try:
        return highlight_html_analytical(html_content)
    except Exception as e:
        st.error(f"Erro ao gerar visualização analítica: {e}")
        return f"<pre>{html_content}</pre>"


def analyze_determinant_rules(hits_data: dict) -> list:
    """Analisa apenas as regras determinantes (score) que deram match."""
    determinant_rules = []

    for rule_id, hit_details in hits_data.items():
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

    determinant_rules.sort(key=lambda x: x["contribution"], reverse=True)
    return determinant_rules


# --- INICIALIZAÇÃO DO ESTADO ---
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

# --- CARREGAMENTO DOS DADOS ---
if st.button("🔄 Atualizar Dados"):
    st.session_state.dashboard_data = load_dashboard_data()
    st.session_state.emails_data = load_emails_data()
    st.session_state.html_files_map = get_html_files_map()

if st.session_state.dashboard_data is None:
    st.session_state.dashboard_data = load_dashboard_data()
if 'emails_data' not in st.session_state:
    st.session_state.emails_data = load_emails_data()
if not st.session_state.html_files_map:
    st.session_state.html_files_map = get_html_files_map()

# --- VERIFICAÇÃO DE DADOS ---
if not st.session_state.dashboard_data or not st.session_state.emails_data:
    st.warning("Dados não encontrados! Execute o coletor primeiro.")
    st.stop()


# --- CÓDIGO PRINCIPAL ---
def main():
    data = st.session_state.dashboard_data

    # Dashboard Principal
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

    # ... (resto do código mantido igual) ...

    # --- EXPORTAÇÃO DE DADOS ---
    with st.expander("💾 Exportação de Dados", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Exportar Resumo para CSV"):
                export_data = []
                for email in st.session_state.emails_data:
                    html_filename = find_html_filename(email)
                    for i, pub in enumerate(email['publications']):
                        export_data.append({
                            'Arquivo_HTML': html_filename,
                            'Email_Assunto': email['subject'],
                            'Email_Data': email['received'],
                            'Publicacao_Index': i + 1,
                            'Publicacao_Score': pub['score'],
                            'Publicacao_Nivel': pub['level'],
                            'Publicacao_Status': pub['analysis_status'],
                            'CNJs': ', '.join(pub['metadata'].get('cnjs', [])),
                            'Tribunal': pub['metadata'].get('tribunal', ''),
                            'Secretaria': pub['metadata'].get('secretaria', ''),
                            'Data_Publicacao': pub['metadata'].get('data_publicacao', '')
                        })

                df = pd.DataFrame(export_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Baixar CSV Completo",
                    data=csv,
                    file_name=f"analise_publicacoes_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

        with col2:
            if st.button("✅ Exportar Apenas com Indícios", type="primary"):

                # ✅ FUNÇÃO INLINE DENTRO DO BOTÃO
                def get_determinant_rules_names_inline(hits_data):
                    """Versão inline da função para evitar problemas de escopo"""
                    if not hits_data:
                        return ""

                    rule_names = []

                    for rule_id in hits_data.keys():
                        if rule_id in sjur_rules.determinant_rules:
                            rule_data = sjur_rules.determinant_rules[rule_id]
                            description = rule_data.get("description", rule_id)
                            rule_names.append(description)

                    return "; ".join(rule_names)

                export_data = []
                for email in st.session_state.emails_data:
                    html_filename = find_html_filename(email)
                    for i, pub in enumerate(email['publications']):
                        if pub.get('score', 0) > 0:
                            processos = pub['metadata'].get('cnjs', [])
                            processos_str = "; ".join(processos) if processos else "Nenhum"

                            # ✅ USA A FUNÇÃO INLINE
                            regras_determinantes = get_determinant_rules_names_inline(pub.get('hits', {}))

                            export_data.append({
                                'Arquivo_HTML': html_filename,
                                'Email_Assunto': email['subject'],
                                'Email_Data': email['received'],
                                'Publicacao_Index': i + 1,
                                'Score_Total': pub['score'],
                                'Nivel': pub['level'],
                                'Processos_Encontrados': processos_str,
                                'Regras_Determinantes': regras_determinantes,
                                'Tribunal': pub['metadata'].get('tribunal', ''),
                                'Secretaria': pub['metadata'].get('secretaria', ''),
                                'Data_Publicacao': pub['metadata'].get('data_publicacao', ''),
                                'Status_Analise': pub['analysis_status'],
                                'Total_Processos': len(processos),
                                'Total_Regras': len(pub.get('hits', {}))
                            })

                if export_data:
                    df = pd.DataFrame(export_data)
                    csv = df.to_csv(index=False, sep=';')
                    st.download_button(
                        label="⬇️ Baixar CSV com Indícios",
                        data=csv,
                        file_name=f"publicacoes_com_indicios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

                    st.success(f"✅ Exportadas {len(export_data)} publicações com indícios de arquivamento")
                    st.info(f"📊 Score médio: {df['Score_Total'].mean():.2f}")

                else:
                    st.warning("⚠️ Nenhuma publicação com indícios de arquivamento encontrada")


# EXECUTA A FUNÇÃO PRINCIPAL
if __name__ == "__main__":
    main()