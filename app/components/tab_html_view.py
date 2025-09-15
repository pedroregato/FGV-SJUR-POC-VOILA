
# app/components/tab_html_view.py

from pathlib import Path
from typing import Optional
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from app.components.html_highlighter import highlight_html_from_csv_data


def render_html_view_tab(
        df_recortes_raw: pd.DataFrame,
        df_publicacoes_raw: pd.DataFrame,
        selected_recorte_id: Optional[str],
        selected_pub_id: Optional[str],
        html_dir: str
):
    st.subheader("Publicação do Recorte")

    # Filtros
    colA, colB = st.columns(2)
    with colA:
        only_with_indications_recortes = st.checkbox("Mostrar apenas recortes com indícios (parte>0 e score>0)", value=False)
    with colB:
        only_with_indications_pubs = st.checkbox("Mostrar apenas publicações com indícios (parte>0 e score>0)", value=False)

    df_recortes = df_recortes_raw.copy()
    df_pubs = df_publicacoes_raw.copy()

    # Filtra recortes/publicações
    if only_with_indications_pubs:
        df_pubs = df_pubs[(df_pubs.get('parte', 0).astype(int) > 0) & (df_pubs.get('score', 0).astype(float) > 0)]
    if only_with_indications_recortes:
        # Mantém apenas recortes que têm publicações filtradas
        keep_ids = set(df_pubs['email_entry_id'].unique().tolist())
        df_recortes = df_recortes[df_recortes['entry_id'].isin(keep_ids)]

    # Seleciona recorte
    recorte_ids = df_recortes['entry_id'].tolist()
    default_recorte = selected_recorte_id or (recorte_ids[0] if recorte_ids else None)
    recorte_index = recorte_ids.index(default_recorte) if default_recorte in recorte_ids else 0 if recorte_ids else 0
    recorte_id = st.selectbox("Selecione o recorte:", recorte_ids, index=recorte_index)

    # Publicações do recorte
    pubs_recorte = df_pubs[df_pubs['email_entry_id'] == recorte_id].copy()

    # Tabela compacta
    if not pubs_recorte.empty:
        st.dataframe(
            pubs_recorte[['publication_id', 'parte', 'score', 'classification_level', 'processos', 'hits']]
            .rename(columns={'classification_level': 'level'}),
            use_container_width=True, height=180
        )
    else:
        st.info("Não há publicações neste recorte após os filtros aplicados.")

    # Seleciona publicação
    pub_ids = pubs_recorte['publication_id'].tolist()
    default_pub_id = selected_pub_id or (pub_ids[0] if pub_ids else None)
    pub_index = pub_ids.index(default_pub_id) if default_pub_id in pub_ids else 0 if pub_ids else 0
    pub_id = st.selectbox("Selecione a publicação:", pub_ids, index=pub_index)

    if not pub_ids:
        return

    # Carrega HTML
    row = pubs_recorte[pubs_recorte['publication_id'] == pub_id].iloc[0]
    html_path = Path(html_dir) / row.get('html_filename', '')
    if html_path.exists():
        html_content = html_path.read_text(encoding='utf-8', errors='ignore')
    else:
        html_content = row.get('html_content', '')

    # Legenda
    st.markdown("""
    **Legenda de cores**
    - <span style="background:#ffd5e5;padding:2px 6px;border-radius:4px">Proximidade (Baixa ↔ Arquiv* etc.)</span>
    - <span style="background:#d4edda;padding:2px 6px;border-radius:4px">CNJ</span>
    - <span style="background:#fff3cd;padding:2px 6px;border-radius:4px">Padrões básicos</span>
    - <span style="background:#d32f2f;color:#fff;padding:2px 6px;border-radius:4px">FGV como parte</span>
    - <span style="background:#e8f0fe;padding:2px 6px;border-radius:4px">Rótulos processuais (Parte/Autor/Réu etc.)</span>
    """, unsafe_allow_html=True)

    # Destaques
    cnjs = [s.strip() for s in str(row.get('processos', '')).split(';') if s.strip()]
    hits_csv = row.get('hits', '')
    highlighted = highlight_html_from_csv_data(html_content, hits_csv, cnjs)

    components.html(highlighted, height=800, scrolling=True)
