# app/components/sidebar_filters.py

import streamlit as st
import pandas as pd

def render_and_apply_filters(
    df_recortes_raw: pd.DataFrame,
    df_publicacoes_raw: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Renderiza todos os filtros na barra lateral e retorna os DataFrames filtrados.
    """
    st.sidebar.divider()
    st.sidebar.title("Filtros")

    # Filtro para mostrar apenas recortes com indícios
    only_with_indications = st.sidebar.checkbox(
        "Mostrar apenas recortes com indícios (Score > 0)",
        value=True
    )

    df_recortes = df_recortes_raw.copy()
    if only_with_indications:
        df_recortes = df_recortes[df_recortes["total_score"] > 0]

    # 1. Filtro por Score
    if not df_recortes.empty:
        score_min = float(df_recortes["total_score"].min())
        score_max = float(df_recortes["total_score"].max())

        # ======================================================================
        # CORREÇÃO: Lógica para evitar o crash do slider
        # Se min e max forem iguais, não há o que filtrar, então não mostramos o slider.
        # ======================================================================
        if score_min < score_max:
            score_range = st.sidebar.slider(
                "Filtrar por Score Agregado",
                min_value=score_min,
                max_value=score_max,
                value=(score_min, score_max)
            )
            # Aplica o filtro do slider
            df_recortes = df_recortes[df_recortes["total_score"].between(score_range[0], score_range[1])]
        else:
            # Apenas informa o usuário que não há variação de score para filtrar
            st.sidebar.caption(f"Score de todos os recortes filtrados: {score_min:.2f}")
            # Não é necessário filtrar mais, pois todos os scores são iguais

    # Retorna os dataframes. O de publicações não é filtrado aqui,
    # pois depende da seleção na grade principal.
    return df_recortes, df_publicacoes_raw
