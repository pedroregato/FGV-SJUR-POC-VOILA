# app/components/sidebar_actions.py

import streamlit as st
import pandas as pd
from io import BytesIO
from typing import Optional


def _create_excel_download(df: pd.DataFrame, sheet_name: str, filename: str, column_widths: dict):
    """Função auxiliar para gerar o botão de download do Excel."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        for col_letter, width in column_widths.items():
            worksheet.set_column(f'{col_letter}:{col_letter}', width)

    processed_data = output.getvalue()
    st.sidebar.download_button(
        label=f"⬇️ Baixar {sheet_name} (Excel)",
        data=processed_data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.sidebar.success(f"{len(df)} registros exportados!")


def render_export_button(
        active_tab: str,
        df_recortes: pd.DataFrame,
        df_publicacoes: pd.DataFrame,
        selected_recorte_id: Optional[str] = None
):
    """
    Renderiza um botão de exportação sensível ao contexto da aba ativa.

    Args:
        active_tab: O nome da aba atualmente ativa.
        df_recortes: O DataFrame de recortes filtrado.
        df_publicacoes: O DataFrame de publicações filtrado.
        selected_recorte_id: O ID do recorte atualmente selecionado.
    """
    st.sidebar.divider()
    st.sidebar.title("Ações")

    # --- LÓGICA DE EXPORTAÇÃO PARA A ABA DE RECORTES ---
    if active_tab == "📊 Análise de Recortes":
        if st.sidebar.button("Exportar Recortes Filtrados"):
            if df_recortes.empty:
                st.sidebar.warning("Nenhum recorte para exportar.")
                return

            export_cols = {
                "received": "Data Recebimento", "subject": "Assunto", "total_score": "Score",
                "pubs_com_indicios": "Pubs c/ Indícios", "pubs_com_cnj": "Pubs c/ CNJ",
                "processos_com_indicios": "Processos c/ Indícios", "processos": "Todos Processos"
            }
            df_to_export = df_recortes[[col for col in export_cols if col in df_recortes.columns]].rename(
                columns=export_cols)

            col_widths = {'A': 20, 'B': 60, 'C': 10, 'D': 20, 'E': 20, 'F': 50, 'G': 50}
            _create_excel_download(df_to_export, "Recortes", "relatorio_recortes.xlsx", col_widths)

    # --- LÓGICA DE EXPORTAÇÃO PARA A ABA DE PUBLICAÇÕES ---
    elif active_tab == "📑 Publicações do Recorte":
        if not selected_recorte_id:
            st.sidebar.info("Selecione um recorte para habilitar a exportação de suas publicações.")
            return

        if st.sidebar.button("Exportar Publicações do Recorte"):
            df_pubs_to_export = df_publicacoes[
                (df_publicacoes["email_entry_id"] == selected_recorte_id) &
                (df_publicacoes["score"] > 0)
                ].copy()

            if df_pubs_to_export.empty:
                st.sidebar.warning("Nenhuma publicação com indícios para exportar neste recorte.")
                return

            export_cols = {
                "score": "Score", "classification_level": "Nível",
                "processos": "Processos na Publicação", "hits": "Regras Acionadas",
                "email_subject": "Assunto do E-mail Pai"
            }
            df_to_export = df_pubs_to_export[[col for col in export_cols if col in df_pubs_to_export.columns]].rename(
                columns=export_cols)

            col_widths = {'A': 10, 'B': 20, 'C': 40, 'D': 60, 'E': 60}
            _create_excel_download(df_to_export, "Publicações", "relatorio_publicacoes.xlsx", col_widths)
