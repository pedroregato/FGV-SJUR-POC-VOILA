# pages/analisador_publicacoes.py (VERSÃO COMPLETA ATUALIZADA)

import streamlit as st
from pathlib import Path
import sys
import json
import os
import pandas as pd
from datetime import datetime
import re
from io import BytesIO

# Configuração da página
st.set_page_config(page_title="Analisador de Publicações SJUR", layout="wide")
st.title("📊 Analisador de Publicações e Estatísticas SJUR")

try:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
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


# --- Funções Auxiliares ---
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
    """
    Gera a visualização analítica completa usando o módulo dedicado.
    """
    if not html_content:
        return ""

    try:
        return highlight_html_analytical(html_content)
    except Exception as e:
        st.error(f"Erro ao gerar visualização analítica: {e}")
        return f"<pre>{html_content}</pre>"


# pages/analisador_publicacoes.py (CORREÇÃO)

def analyze_determinant_rules(hits_data: dict) -> list:
    """
    Analisa apenas as regras determinantes (score) que deram match.
    CORREÇÃO: Usa score fixo das regras, não peso.
    """
    sjur_rules.load_all_rules()

    determinant_rules = []

    for rule_id, hit_details in hits_data.items():
        # Verifica se é uma regra determinante
        if rule_id in sjur_rules.determinant_rules:
            rule_data = sjur_rules.determinant_rules[rule_id]
            description = rule_data.get("description", "Sem descrição")
            score_value = rule_data.get("score", 0)  # ✅ Score fixo da regra

            determinant_rules.append({
                "id": rule_id,
                "description": description,
                "score": score_value,  # ✅ Score fixo (0.5, 0.8, etc.)
                "details": hit_details,
                "contribution": score_value  # ✅ Contribuição = score fixo
            })

    # Ordena por contribuição (maior primeiro)
    determinant_rules.sort(key=lambda x: x["contribution"], reverse=True)

    return determinant_rules


# --- Carregamento dos Dados ---
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

# --- Verificação de Dados ---
if not st.session_state.dashboard_data or not st.session_state.emails_data:
    st.warning("""
    **Dados não encontrados!**

    Para usar esta ferramenta, primeiro execute o coletor de e-mails para gerar os arquivos:
    - `outputs/json/dashboard_data.json`
    - `outputs/json/emails_data.json`

    Execute o coletor e depois clique em **Atualizar Dados**.
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
    html_folder = "outputs/html"
    html_filepath = os.path.join(html_folder, html_filename)
    if os.path.exists(html_filepath):
        with open(html_filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()

        if st.button("📂 Abrir HTML Original Completo", key="open_html_btn"):
            st.components.v1.html(html_content, height=800, scrolling=True)
    else:
        st.warning(f"Arquivo HTML não encontrado: {html_filename}")

# --- Análise de Publicações (FORA DO EXPANDER DE E-MAILS) ---
st.header("📄 Análise de Publicações")

if selected_email_data['total_publications'] > 0:
    # ✅ FILTRO PARA SCORES MAIORES QUE ZERO
    st.subheader("🔍 Filtros de Análise")
    col1, col2 = st.columns(2)

    with col1:
        filter_positive = st.checkbox(
            "Mostrar apenas publicações com indícios de arquivamento (score > 0)",
            value=st.session_state.filter_positive_scores,
            key="filter_positive_checkbox"
        )
        st.session_state.filter_positive_scores = filter_positive

    # pages/analisador_publicacoes.py (TRECHO REFATORADO)

    # ... (código anterior mantido) ...

    with col2:
        if st.button("✅ Exportar Apenas com Indícios", type="primary"):

            def get_determinant_rules_names_inline(hits_data):
                """Versão inline da função para evitar problemas de escopo"""
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
                """Remove caracteres especiais problemáticos"""
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

                # ✅ CRIA ARQUIVO EXCEL (XLSX) - MUDA AQUI!
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Publicações com Indícios')

                    # ✅ FORMATAÇÃO ADICIONAL PARA MELHOR VISUALIZAÇÃO
                    workbook = writer.book
                    worksheet = writer.sheets['Publicações com Indícios']

                    # Ajusta largura das colunas automaticamente
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

                excel_data = excel_buffer.getvalue()

                st.download_button(
                    label="⬇️ Baixar Excel com Indícios",
                    data=excel_data,
                    file_name=f"publicacoes_com_indicios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.success(f"✅ Exportadas {len(export_data)} publicações com indícios de arquivamento")
                st.info(f"📊 Score médio: {df['Score_Total'].mean():.2f}")

                # ✅ MOSTRA PREVIEW (opcional)
                with st.expander("📋 Visualizar Preview dos Dados"):
                    st.dataframe(df.head())

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
        # Cria opções para o dropdown baseado nas publicações filtradas
        pub_options = []
        pub_mapping = []  # Mapeia índice filtrado para índice original

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

        # Converte índice filtrado para índice original
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
        col4.metric("CNJs Encontrados", cnjs_count, "✅" if cnjs_count > 0 else "❌")

        # ✅ METADADOS COM TRATAMENTO DE CARACTERES
        st.subheader("📋 Metadados da Publicação")
        metadata_container = st.container()


        def clean_text(text):
            """Remove caracteres especiais problemáticos"""
            if not text or not isinstance(text, str):
                return text
            try:
                return text.encode('latin-1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                return text


        with metadata_container:
            metadata_col1, metadata_col2 = st.columns(2)
            with metadata_col1:
                for key, value in publication['metadata'].items():
                    if value and key != 'cnjs':
                        cleaned_value = clean_text(value)
                        st.write(f"**{key}:** {cleaned_value}")
            with metadata_col2:
                if publication['metadata'].get('cnjs'):
                    st.write("**CNJs encontrados:**")
                    for cnj in publication['metadata']['cnjs']:
                        st.code(cnj)
                else:
                    st.info("Nenhum CNJ encontrado nesta publicação")

        # ✅ VISUALIZAÇÃO ANALÍTICA
        st.subheader("👀 Visualização Analítica da Publicação")
        analytical_html = generate_analytical_view(publication['html_content'])
        st.components.v1.html(analytical_html, height=600, scrolling=True)

        # Opção para ver o código fonte
        with st.expander("📄 Ver Código HTML Original"):
            st.code(publication['html_content'], language='html')

        # ✅ HITS DAS REGRAS - APENAS DETERMINANTES
        st.subheader("🎯 Regras Determinantes que Deram Match")

        if publication['hits']:
            # Analisa apenas as regras determinantes
            determinant_rules = analyze_determinant_rules(publication['hits'])

            if determinant_rules:
                # Estatísticas rápidas
                total_rules = len(determinant_rules)
                total_contribution = sum(rule["contribution"] for rule in determinant_rules)

                col1, col2, col3 = st.columns(3)
                col1.metric("📊 Regras com Match", total_rules)
                col2.metric("⭐ Contribuição Total", f"{total_contribution:.2f}")
                col3.metric("📈 Score Final", f"{publication['score']:.2f}")

                st.divider()

                # Tabela detalhada das regras
                st.subheader("📋 Detalhamento por Regra")

                # Prepara dados para tabela
                rule_data = []
                for rule in determinant_rules:
                    rule_data.append({
                        "Regra": clean_text(rule["description"]),  # ✅ LIMPEZA DE TEXTO
                        "Score": rule["score"],
                        "Match": rule["details"],
                        "Contribuição": f"{rule['contribution']:.2f}"
                    })

                # Exibe como tabela
                df_rules = pd.DataFrame(rule_data)
                st.dataframe(
                    df_rules,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Regra": st.column_config.TextColumn("Regra", width="large"),
                        "Score": st.column_config.NumberColumn("Score", format="%.2f"),
                        "Match": st.column_config.TextColumn("Detalhes do Match"),
                        "Contribuição": st.column_config.TextColumn("Contribuição")
                    }
                )

                # Gráfico de contribuição
                st.subheader("📊 Contribuição para o Score")

                chart_data = pd.DataFrame({
                    'Regra': [clean_text(rule["description"])[:30] + "..." for rule in determinant_rules],  # ✅ LIMPEZA
                    'Contribuição': [rule["contribution"] for rule in determinant_rules]
                })

                st.bar_chart(chart_data.set_index('Regra'))

            else:
                st.info("ℹ️ Nenhuma regra determinante aplicou match nesta publicação")

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

# --- Diagnóstico do Problema de CNJ ---
with st.expander("🔍 Diagnóstico de Extração de CNJ", expanded=False):
    if not data["unique_archival_processes"] and data["total_archival_candidate_publications"] > 0:
        st.error("""
        **PROBLEMA IDENTIFICADO:**

        Foram encontradas publicações candidatas a arquivamento (score ≥ 0.6), mas 
        **nenhum número de processo (CNJ) foi extraído**.

        **Possíveis causas:**
        1. Regex de CNJ não está funcionando corretamente
        2. Formato dos CNJs nas publicações é diferente do esperado
        3. As regras de contexto não estão sendo aplicadas
        """)

        st.info("""
        **Para diagnosticar:**
        1. Use a visualização analítica acima para ver se os CNJs estão sendo destacados
        2. Verifique a regex de CNJ em `app/rules/archival_rules.py`
        3. Teste com exemplos específicos no laboratorio de regex
        """)

# --- EXPORTAÇÃO DE DADOS ---
with st.expander("💾 Exportação de Dados", expanded=False):
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Exportar Resumo para CSV", key="btn_export_csv_full"):  # ✅ KEY ÚNICA
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
                mime="text/csv",
                key="btn_download_csv_full"  # ✅ KEY ÚNICA
            )

    with col2:
        if st.button("✅ Exportar Apenas com Indícios", type="primary", key="btn_export_excel_indicios"):  # ✅ KEY ÚNICA

            def get_determinant_rules_names_inline(hits_data):
                """Versão inline da função para evitar problemas de escopo"""
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
                """Remove caracteres especiais problemáticos"""
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

                # ✅ CRIA ARQUIVO EXCEL (XLSX)
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Publicações com Indícios')

                    # Formatação adicional para melhor visualização
                    workbook = writer.book
                    worksheet = writer.sheets['Publicações com Indícios']

                    # Ajusta largura das colunas automaticamente
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

                excel_data = excel_buffer.getvalue()

                st.download_button(
                    label="⬇️ Baixar Excel com Indícios",
                    data=excel_data,
                    file_name=f"publicacoes_com_indicios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_download_excel_indicios"  # ✅ KEY ÚNICA
                )

                st.success(f"✅ Exportadas {len(export_data)} publicações com indícios de arquivamento")
                st.info(f"📊 Score médio: {df['Score_Total'].mean():.2f}")

                # ✅ MOSTRA PREVIEW (opcional)
                with st.expander("📋 Visualizar Preview dos Dados"):
                    st.dataframe(df.head())

            else:
                st.warning("⚠️ Nenhuma publicação com indícios de arquivamento encontrada")

st.success("✅ Análise concluída! Use os controles acima para navegar pelos dados.")