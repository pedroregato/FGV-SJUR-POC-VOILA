# app_arquivamento_streamlit.py
# (Versão com lógica de visualização corrigida)
from __future__ import annotations
from pathlib import Path
import json
import re
import urllib.parse
import html
import logging as _logging
import ast
from io import BytesIO

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import matplotlib.pyplot as plt

try:
    from bs4 import BeautifulSoup, NavigableString

    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

# -----------------------------------------------------------------------------
# Configurações gerais
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Scanner de Arquivamento (SJUR)", layout="wide")
st.title("📄 Scanner de Indícios de Arquivamento — SJUR")
_logging.getLogger("streamlit.runtime.caching.hashing").setLevel(_logging.ERROR)

# -----------------------------------------------------------------------------
# Sidebar - Carregamento de Arquivos
# -----------------------------------------------------------------------------
st.sidebar.title("Fonte de Dados")
default_csv = st.sidebar.text_input("Caminho do CSV", value="outputs/arquivamento.csv")
html_dir = st.sidebar.text_input("Pasta de HTML", value="outputs/html")
uploaded = st.sidebar.file_uploader("...ou carregue um CSV (separador ';')", type=["csv"])


# -----------------------------------------------------------------------------
# Query params helpers
# -----------------------------------------------------------------------------
def _get_query_param(key: str, default=None):
    return st.query_params.get(key, default)


def _set_query_params(**kwargs):
    st.query_params.update(kwargs)


# -----------------------------------------------------------------------------
# Carregamento e Preparação do DataFrame
# -----------------------------------------------------------------------------
@st.cache_data
def load_df_from_source(source):
    df_ = pd.read_csv(source, sep=";")
    df_["score"] = pd.to_numeric(df_["score"], errors="coerce").fillna(0).astype(int)
    df_["is_arquivamento_flag"] = (df_["is_arquivamento"].astype(str).str.strip() == "1").astype(int)
    df_["received_dt"] = pd.to_datetime(df_["received"], format="%Y-%m-%d_%H%M%S", errors="coerce")

    if "hits" in df_.columns:
        df_["hits_norm"] = df_["hits"].fillna("").apply(
            lambda x: [h.split(":", 1)[-1] for h in x.split(",") if ":" in h])
    else:
        df_["hits_norm"] = [[] for _ in range(len(df_))]

    if "processed_publications" in df_.columns:
        def safe_literal_eval(val):
            try:
                return ast.literal_eval(val)
            except (ValueError, SyntaxError, TypeError):
                return []

        df_["processed_publications"] = df_["processed_publications"].fillna("[]").apply(safe_literal_eval)

    return df_


# -----------------------------------------------------------------------------
# Destaque de HTML
# -----------------------------------------------------------------------------
def highlight_keywords_in_html(html_content: str, hits_seq, processos_seq, indicios_seq):
    if not HAS_BS4:
        return f"<p>Instale BeautifulSoup4 para visualizar o HTML: <code>pip install beautifulsoup4</code></p>"

    soup = BeautifulSoup(html_content, "html.parser")

    style = """
    <style>
      mark.sjur-hit { background: #ffeb3b !important; padding: 0 .2em !important; border-radius: 3px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important; color: #000 !important; font-weight: bold !important; border: 1px solid #ffc107 !important; }
      mark.sjur-cnj { background: #e3f2fd !important; padding: 0 .2em !important; border-radius: 3px !important; border: 1px solid #90caf9 !important; }
      mark.sjur-indicio { background: #ff4444 !important; color: white !important; padding: 0 .2em !important; border-radius: 3px !important; font-weight: bold !important; border: 1px solid #cc0000 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important; }
      mark.sjur-fgv { background: #4caf50 !important; color: white !important; padding: 0 .2em !important; border-radius: 3px !important; font-weight: bold !important; border: 1px solid #388e3c !important; }
      mark.sjur-prazo { background: #1565c0 !important; color: white !important; padding: 0 .2em !important; border-radius: 3px !important; font-weight: bold !important; border: 1px solid #0d47a1 !important; }
      body, div, p, span, td, tr, table, li, ul, ol { background: white !important; color: #333 !important; }
    </style>
    """
    if soup.head:
        soup.head.insert(0, BeautifulSoup(style, "html.parser"))
    else:
        soup.insert(0, BeautifulSoup(style, "html.parser"))

    re_hits = re.compile(r'(' + '|'.join(re.escape(term) for term in hits_seq if term) + r')',
                         re.IGNORECASE) if hits_seq else None
    re_cnjs = re.compile(
        r'(' + '|'.join(re.escape(cnj) for cnj in processos_seq if cnj) + r')') if processos_seq else None
    re_indicios = re.compile(
        r'(' + '|'.join(re.escape(cnj) for cnj in indicios_seq if cnj) + r')') if indicios_seq else None
    re_fgv = re.compile(r'\b(funda[cç][aã]o getulio vargas|fgv)\b', re.IGNORECASE)
    re_prazo = re.compile(r'\b(prazo|termo|dilig[êe]ncia|intima[cç][aã]o|ci[êe]ncia|cita[cç][aã]o)\b', re.IGNORECASE)

    for text_node in soup.find_all(string=True):
        if text_node.parent.name in ['style', 'script', 'head', 'title']:
            continue

        text = str(text_node)
        new_html = text

        if re_fgv: new_html = re_fgv.sub(r'<mark class="sjur-fgv">\1</mark>', new_html)
        if re_prazo: new_html = re_prazo.sub(r'<mark class="sjur-prazo">\1</mark>', new_html)
        if re_hits: new_html = re_hits.sub(r'<mark class="sjur-hit">\1</mark>', new_html)
        if re_cnjs: new_html = re_cnjs.sub(r'<mark class="sjur-cnj">\1</mark>', new_html)
        if re_indicios: new_html = re_indicios.sub(r'<mark class="sjur-indicio">\1</mark>', new_html)

        if new_html != text:
            text_node.replace_with(BeautifulSoup(new_html, "html.parser"))

    return str(soup)


# -----------------------------------------------------------------------------
# Lógica Principal da UI
# -----------------------------------------------------------------------------
if uploaded:
    df = load_df_from_source(uploaded)
elif default_csv and Path(default_csv).exists():
    df = load_df_from_source(default_csv)
else:
    st.warning("Carregue um arquivo CSV ou especifique um caminho válido.")
    st.stop()

st.markdown("""
<style>
    .stDataFrame table { width: 100%; border-collapse: collapse; }
    .stDataFrame th, .stDataFrame td { vertical-align: top !important; text-align: left; padding: 8px; border: 1px solid #ddd; }
    .scrollable-cell { max-height: 150px; overflow-y: auto; display: block; white-space: pre-wrap; word-wrap: break-word; }
</style>
""", unsafe_allow_html=True)

# Abas
tab_res, tab_view, tab_doc = st.tabs(["📊 Resultados", "📰 Visualização", "📘 Documentação"])

with tab_res:
    st.subheader("Filtros")
    score_min, score_max = int(df["score"].min()), int(df["score"].max())
    c1, c2, c3, c4 = st.columns([1, 1, 2, 2])
    score_range = c1.slider("Score", score_min, score_max, (score_min, score_max))
    only_flagged = c2.checkbox("Apenas `is_arquivamento=1`", False)
    q_subject = c3.text_input("Busca no assunto", "").strip().lower()
    q_hits = c4.text_input("Busca nos hits", "").strip().lower()

    fdf = df[
        (df["score"].between(score_range[0], score_range[1])) &
        (df["is_arquivamento_flag"] == 1 if only_flagged else True) &
        (df["subject"].str.lower().str.contains(q_subject, na=False)) &
        (df["hits"].str.lower().str.contains(q_hits, na=False))
        ].copy()

    sort_col = _get_query_param("sort", "score")
    sort_order = _get_query_param("order", "desc")
    fdf = fdf.sort_values(by=sort_col, ascending=(sort_order == "asc"))

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Recortes", len(df))
    c2.metric("Recortes Filtrados", len(fdf))
    c3.metric("Marcados como Arquivamento", int(df["is_arquivamento_flag"].sum()))

    st.subheader("Resultados filtrados")
    st.info(
        "🔴 **indicios**: processos com indícios positivos | 🔵 **processos**: todos os CNJs encontrados no recorte.")

    cols_to_show = ["received", "score", "is_arquivamento", "hits", "subject", "indicios", "processos"]
    view_df = fdf[[c for c in cols_to_show if c in fdf.columns]].copy()

    for col in ["processos", "indicios", "hits"]:
        if col in view_df.columns:
            view_df[col] = view_df[col].fillna('').apply(
                lambda x: f'<div class="scrollable-cell">{html.escape(x).replace("; ", "").replace(", ", "")}</div>')


    def build_link(row):
        params = {"viewrow": row["entry_id"]}
        return f'<a href="?{urllib.parse.urlencode(params)}" target="_self">abrir</a>'


    view_df["🔗 Ver HTML"] = fdf.apply(build_link, axis=1)

    st.markdown(view_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# --- Bloco de Ações na Sidebar ---
st.sidebar.divider()
st.sidebar.title("Ações")

if st.sidebar.button("Exportar Processos com Indícios (Excel)"):
    indicios_df = fdf[fdf['indicios'].notna() & (fdf['indicios'] != '')].copy()

    if indicios_df.empty:
        st.sidebar.warning("Nenhum processo com indício encontrado nos dados filtrados.")
    else:
        export_data = []
        for index, row in indicios_df.iterrows():
            processos_com_indicio = [p.strip() for p in row['indicios'].split(';') if p.strip()]
            for processo in processos_com_indicio:
                export_data.append({
                    "Processo com Indício": processo,
                    "Recorte (Assunto)": row.get('subject', ''),
                    "Data do Recorte": row.get('received', ''),
                    "Score do Recorte": row.get('score', 0),
                    "Hits no Recorte": row.get('hits', '').replace(',', ', ')
                })

        export_df = pd.DataFrame(export_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Processos com Indicios')
            worksheet = writer.sheets['Processos com Indicios']
            worksheet.set_column('A:A', 30)
            worksheet.set_column('B:B', 50)
            worksheet.set_column('C:C', 20)
            worksheet.set_column('D:D', 10)
            worksheet.set_column('E:E', 50)

        processed_data = output.getvalue()
        st.sidebar.download_button(
            label="⬇️ Baixar Relatório Excel",
            data=processed_data,
            file_name="relatorio_indicios_de_arquivamento.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.sidebar.success(f"{len(export_df)} ocorrências exportadas!")

# --- Aba de Visualização ---
with tab_view:
    st.subheader("Visualização do Recorte com Destaques")

    c1, c2 = st.columns([3, 1])
    with c1:
        st.caption("Destaques: 🔴 CNJs com indício | 🟡 Hits de arquivamento | 🟢 FGV | 🔵 Prazos/Intimações")
    with c2:
        filter_pubs = st.checkbox("Mostrar apenas publicações com indícios", value=False)

    viewrow_id = _get_query_param("viewrow")
    row_to_display = None

    if viewrow_id:
        row_match = df[df["entry_id"] == viewrow_id]
        if not row_match.empty:
            row_to_display = row_match.iloc[0]
    elif not fdf.empty:
        row_to_display = fdf.iloc[0]

    if row_to_display is not None:
        html_content_to_render = ""

        # Prioridade 1: Usar a coluna 'processed_publications' se existir
        if "processed_publications" in row_to_display and isinstance(row_to_display["processed_publications"], list) and \
                row_to_display["processed_publications"]:
            pubs_data = row_to_display["processed_publications"]

            if filter_pubs:
                pubs_to_show = [pub['html'] for pub in pubs_data if pub.get('score', 0) > 0]
            else:
                pubs_to_show = [pub['html'] for pub in pubs_data]

            if not pubs_to_show:
                if filter_pubs:
                    st.info("Nenhuma publicação com indícios positivos encontrada neste recorte.")
                # Se não houver publicações, html_content_to_render permanece vazio
            else:
                html_content_to_render = "<hr style='border-top: 2px dashed #ccc; margin: 20px 0;'>".join(pubs_to_show)

        # Prioridade 2 (Fallback): Se a coluna não existir, carregar do arquivo HTML
        else:
            html_path = Path(html_dir) / row_to_display["html_filename"]
            if html_path.exists():
                html_content_to_render = html_path.read_text(encoding="utf-8", errors="ignore")
            else:
                st.error(f"Arquivo HTML não encontrado: {html_path}")

        # Renderiza o conteúdo se ele foi preparado
        if html_content_to_render:
            processos_list = [p.strip() for p in row_to_display.get('processos', '').split('; ') if p.strip()]
            indicios_list = [p.strip() for p in row_to_display.get('indicios', '').split('; ') if p.strip()]

            highlighted_html = highlight_keywords_in_html(
                html_content_to_render,
                row_to_display["hits_norm"],
                processos_list,
                indicios_list
            )
            components.html(highlighted_html, height=700, scrolling=True)

    else:
        st.info("Selecione um recorte na aba 'Resultados' para visualizar ou limpe os filtros.")

with tab_doc:
    st.markdown("""
    ### O que esta aplicação faz?
    - **Análise por Publicação**: Cada publicação dentro de um recorte é analisada individualmente para máxima precisão.
    - **Lê um CSV**: Carrega os resultados do pipeline de coleta.
    - **Filtros Avançados**: Permite filtrar por score, flag de arquivamento e termos no assunto ou nos `hits`.
    - **Visualização com Destaques**: Exibe o HTML do recorte com destaques visuais:
        - 🔴 **CNJs com Indício**: Processos encontrados em publicações que contêm termos de arquivamento.
        - 🟡 **Hits de Arquivamento**: Os termos do léxico que geraram o score.
        - 🟢 **FGV**: Menções à Fundação Getúlio Vargas.
        - 🔵 **Prazos/Intimações**: Termos relacionados a prazos processuais.

    ### Explicação das Colunas
    - **score**: Soma dos scores de cada publicação individual dentro do recorte.
    - **is_arquivamento**: Flag `1` se o score total for >= 3.
    - **hits**: Termos do léxico que contribuíram para o score.
    - **processos**: Todos os CNJs únicos encontrados em todo o recorte.
    - **indicios**: Apenas os CNJs que estavam em publicações contendo indícios positivos de arquivamento.
    """)
