# app/components/tab_html_view.py

import re
from pathlib import Path
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from app.components.html_highlighter import highlight_html


def render_html_view_tab(
        df_recortes_raw: pd.DataFrame,
        df_publicacoes_raw: pd.DataFrame,
        selected_recorte_id: str | None,
        selected_pub_id: str | None,
        html_dir: str
):
    st.header("Visualização do HTML")

    if not selected_recorte_id:
        st.info("Selecione um recorte na aba '📊 Análise de Recortes' para visualizar o HTML.")
        return

    recorte_row = df_recortes_raw[df_recortes_raw["entry_id"] == selected_recorte_id].iloc[0]
    st.subheader(f"Recorte: {recorte_row.get('subject', 'Assunto não encontrado')}")

    pub_row = None
    if selected_pub_id:
        pub_row = df_publicacoes_raw[df_publicacoes_raw["publication_id"] == selected_pub_id].iloc[0]

    view_mode = "Recorte Completo"
    if pub_row is not None:
        view_mode = st.radio("Escopo:", ["Apenas a Publicação", "Recorte Completo"], index=0, horizontal=True)

    html_content, hits_list, processos_list = "", [], []

    if pub_row is not None:
        # ======================================================================
        # MUDANÇA CRÍTICA: Extrair os termos do léxico para o destaque
        # ======================================================================
        hits_raw = pub_row.get('hits', '')
        # Extrai o texto capturado pela regex, que é o que precisamos para o destaque
        hits_list = re.findall(r'texto: "([^"]+)"', hits_raw)

        # Fallback para o formato antigo, se necessário
        if not hits_list and hits_raw:
            hits_list = [h.split(' (texto:')[0].strip() for h in hits_raw.split(';')]

        processos_list = [p.strip() for p in str(pub_row.get('processos', '')).split(';') if p.strip()]

    if view_mode == "Apenas a Publicação" and pub_row is not None:
        html_content = pub_row.get("html_content", "")
    else:
        html_path = Path(html_dir) / recorte_row["html_filename"]
        if html_path.exists():
            html_content = html_path.read_text(encoding="utf-8", errors="ignore")
        else:
            st.error(f"Arquivo HTML não encontrado: {html_path}")

    if html_content:
        highlighted_html = highlight_html(
            html_content=html_content,
            hits_to_highlight=hits_list,
            cnjs_to_highlight=processos_list
        )
        components.html(highlighted_html, height=800, scrolling=True)
