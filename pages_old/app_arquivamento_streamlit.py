# app_arquivamento_streamlit.py

from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

# Importa TODOS os nossos componentes de UI
from app.styles.html_styler import render_html_with_js_styling
from app.components.sidebar_filters import render_and_apply_filters
from app.components.sidebar_actions import render_export_button
from app.components.tab_html_view import render_html_view_tab

# -----------------------------------------------------------------------------
# Configurações gerais e Estado da Sessão
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Analisador de Recortes (SJUR)", layout="wide")
st.title("📄 Analisador de Recortes com Indícios de Arquivamento")

# Inicialização do estado da sessão
if 'selected_recorte_id' not in st.session_state:
    st.session_state.selected_recorte_id = None
if 'selected_pub_id' not in st.session_state:
    st.session_state.selected_pub_id = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📊 Análise de Recortes"


# =============================================================================
# Carregamento de Dados
# =============================================================================
@st.cache_data
def load_data(recortes_path, publicacoes_path):
    """Carrega os arquivos CSV em DataFrames."""
    try:
        df_recortes = pd.read_csv(recortes_path, sep=";", keep_default_na=False)
        df_publicacoes = pd.read_csv(publicacoes_path, sep=";", keep_default_na=False)
        if 'html_content' not in df_publicacoes.columns:
            df_publicacoes['html_content'] = ""
        return df_recortes, df_publicacoes
    except FileNotFoundError:
        return None, None


st.sidebar.title("Fonte de Dados")
recortes_csv_path = st.sidebar.text_input("CSV de Recortes", value="outputs/recortes.csv")
publicacoes_csv_path = st.sidebar.text_input("CSV de Publicações", value="outputs/publicacoes.csv")
html_dir = st.sidebar.text_input("Pasta de HTML", value="outputs/html")

df_recortes_raw, df_publicacoes_raw = load_data(recortes_csv_path, publicacoes_csv_path)

if df_recortes_raw is None:
    st.error(f"Arquivos CSV não encontrados. Verifique os caminhos e execute o coletor.")
    st.stop()

# =============================================================================
# LÓGICA DA SIDEBAR (Componentes)
# =============================================================================
df_recortes, df_publicacoes = render_and_apply_filters(df_recortes_raw, df_publicacoes_raw)

# =============================================================================
# NAVEGAÇÃO PRINCIPAL (Abas)
# =============================================================================
tab_options = ["📊 Análise de Recortes", "📑 Publicações do Recorte", "📰 Visualização do HTML", "📘 Documentação"]
try:
    active_tab_index = tab_options.index(st.session_state.active_tab)
except ValueError:
    active_tab_index = 0

active_tab = st.radio(
    "Navegação", tab_options, index=active_tab_index, key="tabs_radio",
    horizontal=True, label_visibility="collapsed"
)
st.session_state.active_tab = active_tab

# =============================================================================
# LÓGICA DA SIDEBAR (Continuação - Ações sensíveis ao contexto)
# =============================================================================
render_export_button(
    active_tab=active_tab,
    df_recortes=df_recortes,
    df_publicacoes=df_publicacoes,
    selected_recorte_id=st.session_state.selected_recorte_id
)

# =============================================================================
# ROTEAMENTO PARA O CONTEÚDO DE CADA ABA
# =============================================================================

# --- Aba 1: Análise de Recortes ---
if active_tab == "📊 Análise de Recortes":
    st.header("Recortes (E-mails) Filtrados")

    if st.session_state.selected_recorte_id and st.session_state.selected_recorte_id not in df_recortes[
        'entry_id'].values:
        selected_row = df_recortes_raw[df_recortes_raw['entry_id'] == st.session_state.selected_recorte_id]
        df_recortes = pd.concat([selected_row, df_recortes], ignore_index=True)
        st.warning(f"A linha selecionada foi mantida na visualização, embora não corresponda aos filtros atuais.")

    st.metric("Total de Recortes Analisados", len(df_recortes_raw))
    st.metric("Recortes na Visualização Atual", len(df_recortes))

    # ======================================================================
    # CORREÇÃO: Lógica para pré-marcar a linha selecionada
    # ======================================================================
    if 'Analisar' not in df_recortes.columns:
        df_recortes['Analisar'] = False
    if st.session_state.selected_recorte_id:
        # Define a coluna 'Analisar' como True para a linha cujo 'entry_id' corresponde ao ID salvo
        df_recortes.loc[df_recortes['entry_id'] == st.session_state.selected_recorte_id, 'Analisar'] = True
    # ======================================================================

    cols_recortes = ["Analisar", "total_score", "pubs_com_indicios", "pubs_com_cnj", "processos_com_indicios",
                     "processos", "subject", "received"]
    view_cols = [col for col in cols_recortes if col in df_recortes.columns]
    view_df_recortes = df_recortes[view_cols + ["entry_id"]].sort_values(by="total_score", ascending=False)

    st.info("Marque a caixa de seleção 'Analisar' na linha do recorte desejado.")

    edited_df = st.data_editor(
        view_df_recortes,
        column_config={
            "entry_id": None, "Analisar": st.column_config.CheckboxColumn(required=True),
            "total_score": st.column_config.NumberColumn("Score", format="%.2f"),
            "pubs_com_indicios": st.column_config.NumberColumn("Pubs c/ Indícios"),
            "pubs_com_cnj": st.column_config.NumberColumn("Pubs c/ CNJ"),
            "processos_com_indicios": st.column_config.TextColumn("Processos c/ Indícios", width="medium"),
            "processos": st.column_config.TextColumn("Todos Processos", width="medium"),
            "subject": st.column_config.TextColumn("Assunto", width="large"),
            "received": st.column_config.TextColumn("Recebido"),
        },
        hide_index=True, key="recortes_editor"
    )

    selected_rows = edited_df[edited_df["Analisar"]]
    if not selected_rows.empty:
        selected_id = selected_rows.iloc[0]["entry_id"]
        if st.session_state.selected_recorte_id != selected_id:
            st.session_state.selected_recorte_id = selected_id
            st.session_state.selected_pub_id = None
            st.session_state.active_tab = "📑 Publicações do Recorte"
            st.rerun()
    else:
        # Se nenhuma linha estiver selecionada, limpa o estado
        st.session_state.selected_recorte_id = None
        st.session_state.selected_pub_id = None

# --- Aba 2: Publicações do Recorte ---
if active_tab == "📑 Publicações do Recorte":
    st.header("Análise das Publicações do Recorte Selecionado")
    if not st.session_state.selected_recorte_id:
        st.info("Marque um recorte na aba '📊 Análise de Recortes' para ver suas publicações.")
    else:
        recorte_info = df_recortes[df_recortes["entry_id"] == st.session_state.selected_recorte_id]
        if recorte_info.empty:
            st.warning(
                "O recorte selecionado não atende aos filtros atuais da barra lateral. Desmarque os filtros para vê-lo.")
            st.stop()

        st.subheader(f"Recorte: {recorte_info.iloc[0]['subject']}")
        df_pubs_filtradas = df_publicacoes[df_publicacoes["email_entry_id"] == st.session_state.selected_recorte_id]
        df_pubs_com_indicio = df_pubs_filtradas[df_pubs_filtradas["score"] > 0].copy()

        if df_pubs_com_indicio.empty:
            st.success("✔️ Nenhuma publicação com indícios de arquivamento (Score > 0) encontrada neste recorte.")
        else:
            # ======================================================================
            # CORREÇÃO: Lógica para pré-marcar a publicação selecionada
            # ======================================================================
            if 'Visualizar' not in df_pubs_com_indicio.columns:
                df_pubs_com_indicio['Visualizar'] = False
            if st.session_state.selected_pub_id:
                df_pubs_com_indicio.loc[
                    df_pubs_com_indicio['publication_id'] == st.session_state.selected_pub_id, 'Visualizar'] = True
            # ======================================================================

            cols_pubs = ["Visualizar", "tribunal", "secretaria", "data_publicacao", "score", "classification_level",
                         "processos", "hits", "publication_id"]
            cols_to_show = [col for col in cols_pubs if col in df_pubs_com_indicio.columns]
            st.info("Marque 'Visualizar' para destacar a publicação na aba de HTML.")
            sorted_pubs_df = df_pubs_com_indicio[cols_to_show].sort_values(by="score", ascending=False)

            edited_pubs_df = st.data_editor(
                sorted_pubs_df,
                column_config={
                    "publication_id": None, "Visualizar": st.column_config.CheckboxColumn(required=True),
                    "tribunal": st.column_config.TextColumn("Tribunal", width="medium"),
                    "secretaria": st.column_config.TextColumn("Secretaria", width="medium"),
                    "data_publicacao": st.column_config.TextColumn("Data da Publicação", width="small"),
                    "score": st.column_config.NumberColumn("Score", format="%.2f"),
                    "classification_level": "Nível",
                    "processos": st.column_config.TextColumn("Processos na Publicação", width="medium"),
                    "hits": st.column_config.TextColumn("Regras Acionadas", width="large"),
                },
                hide_index=True, key="pubs_editor"
            )

            selected_pub_rows = edited_pubs_df[edited_pubs_df["Visualizar"]]
            if not selected_pub_rows.empty:
                selected_pub_id = selected_pub_rows.iloc[0]["publication_id"]
                if st.session_state.selected_pub_id != selected_pub_id:
                    st.session_state.selected_pub_id = selected_pub_id
                    st.session_state.active_tab = "📰 Visualização do HTML"
                    st.rerun()
            else:
                # Se nenhuma publicação for selecionada, limpa o estado
                st.session_state.selected_pub_id = None

# --- Aba 3: Visualização do HTML (Componentizada) ---
if active_tab == "📰 Visualização do HTML":
    render_html_view_tab(
        df_recortes_raw=df_recortes_raw,
        df_publicacoes_raw=df_publicacoes_raw,
        selected_recorte_id=st.session_state.selected_recorte_id,
        selected_pub_id=st.session_state.selected_pub_id,
        html_dir=html_dir
    )

# --- Aba 4: Documentação ---
if active_tab == "📘 Documentação":
    st.markdown("""
    # Documentação das Regras Heurísticas para Detecção de Arquivamento

    **Projeto:** FGV – SJUR – Coleta e Tratamento de Informações Jurídicas  
    **Versão das Regras:** 1.4.0  
    **Propósito:** Detalhar a metodologia, a estrutura e os critérios utilizados pelo classificador heurístico para identificar indícios de arquivamento de processos em publicações jurídicas.

    ---

    ## 1. Visão Geral e Metodologia

    O classificador heurístico opera sobre o texto extraído das publicações jurídicas para calcular um **escore de arquivamento (`score`)**. Este escore é gerado através de um sistema de **regras ponderadas**, onde diferentes termos e contextos recebem pesos positivos ou negativos.

    O processo segue três etapas principais:

    1.  **Normalização do Texto:** O texto original é padronizado (minúsculas, remoção de acentos) para garantir a consistência da análise.
    2.  **Análise por Padrões (Regex):** O sistema varre o texto em busca de padrões textuais (expressões regulares) definidos no arquivo `archival_heuristic_rules.json`. Cada padrão encontrado contribui com seu peso para o escore total.
    3.  **Classificação por Limiares:** O escore numérico final é traduzido em uma classificação categórica (ex: "Arquivamento forte"), facilitando a interpretação pelo usuário.

    Esta abordagem é transparente, auditável e permite que as regras de negócio sejam refinadas de forma centralizada, sem a necessidade de alterar o código-fonte da aplicação.

    ---

    ## 2. Detalhamento das Categorias de Padrões

    As regras são organizadas em categorias semânticas para refletir a natureza e a força de cada indício.

    ### 2.1. Categoria: `nucleo`

    **Função:** Contém os sinais mais fortes e diretos de arquivamento, baixa ou extinção. A presença de um termo desta categoria é um indicador de alta confiança.

    | Regra (Descrição) | Peso | Exemplo de Expressão Capturada |
    | :------------------ | :--- | :------------------------------ |
    | **Comando de Arquivamento** | `1.00` | `arquive-se`, `arquivem-se` |
    | **Arquivamento Definitivo** | `1.00` | `arquivamento definitivo`, `arquivado definitivamente` |
    | **Baixa com Contexto de Arquivamento** | `0.90` | `baixa e posterior arquivamento` |
    | **Baixa Definitiva** | `0.80` | `baixa definitiva` |
    | **Comando de Extinção** | `0.75` | `extinto o processo`, `extinção do feito` |
    | **Arquivamento (Genérico)** | `0.70` | `determino o arquivamento` |
    | **Baixa na Distribuição** | `0.60` | `baixa na distribuição` |
    | **Arquivamento Provisório** | `0.50` | `arquivamento provisório` |

    ### 2.2. Categoria: `adicional`

    **Função:** Contém eventos processuais que, embora não sejam o ato de arquivamento em si, são fortes indicadores de que o processo está em sua fase final.

    | Regra (Descrição) | Peso | Exemplo de Expressão Capturada |
    | :------------------ | :--- | :------------------------------ |
    | **Trânsito em Julgado** | `0.65` | `transitada em julgado`, `transitado o feito em julgado` |
    | **Desistência da Ação** | `0.50` | `homologo a desistência` |
    | **Decisão de Mérito (Julgamento)** | `0.45` | `julgo improcedente o pedido`, `julgar procedente a ação` |
    | **Decisão em Mandado de Segurança** | `0.45` | `concedo a segurança`, `denegar a segurança` |
    | **Revelia** | `0.35` | `decreto a revelia`, `não apresentou contestação` |

    ### 2.3. Categoria: `reforco`

    **Função:** Contém termos que indicam o contexto de uma decisão final. Sozinhos, têm baixo impacto, mas aumentam a confiança quando combinados com regras das categorias `nucleo` ou `adicional`.

    | Regra (Descrição) | Peso | Exemplo de Expressão Capturada |
    | :------------------ | :--- | :------------------------------ |
    | **Termos de Fecho/Dispositivo** | `0.20` | `sentença`, `dispositivo`, `isto posto`, `ante o exposto` |

    ### 2.4. Categoria: `negacao`

    **Função:** Contém termos que indicam o oposto de um arquivamento. A presença de um destes termos aplica uma penalidade severa ao escore, ajudando a evitar falsos positivos.

    | Regra (Descrição) | Peso | Exemplo de Expressão Capturada |
    | :------------------ | :---- | :------------------------------ |
    | **Negação ou Desarquivamento** | `-1.00` | `desarquive-se`, `não é caso de arquivamento` |

    ---

    ## 3. Regras de Contexto e Classificação Final

    ### 3.1. Boost de Proximidade

    Para aumentar a precisão, uma pontuação bônus (`boost`) é aplicada se certos termos aparecerem próximos no texto.

    -   **Condição:** A expressão "trânsito em julgado" (e suas variações) aparece a até 300 caracteres de distância do comando "arquive-se" (ou "arquivem-se").
    -   **Efeito:** Adiciona `+0.20` ao escore final.
    -   **Justificativa:** Esta combinação representa o fluxo processual mais clássico e confiável para o arquivamento.

    ### 3.2. Limiares de Classificação (`thresholds`)

    Após o cálculo final do escore, o sistema o converte em um nível de confiança legível:

    | Nível de Confiança | Condição de Escore | Descrição |
    | :----------------- | :----------------- | :---------- |
    | **Arquivamento forte** | `score ≥ 0.90` | A publicação contém indícios explícitos e de alta confiança de que o processo foi encerrado. |
    | **Arquivamento provável** | `0.60 ≤ score < 0.90` | A publicação contém múltiplos indícios consistentes, mas sem um comando direto e inequívoco. |
    | **Não identificado** | `score < 0.60` | A publicação não apresenta indícios suficientes para uma classificação positiva. |
    """)
