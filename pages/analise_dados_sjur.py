import streamlit as st
import sqlite3
import pandas as pd
import re
from datetime import datetime, date
from typing import Tuple, Dict, Any, Optional, List
import logging
from app.database.db_connection import get_connection

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações gerais do aplicativo
st.set_page_config(
    layout="wide",
    page_title="Análise dos Dados do Pipeline SJUR",
    page_icon="📊"
)

from app.database.db_connection import DB_PATH

def check_health():
    """Exibe o status do banco de dados na interface do usuário."""
    try:
        if not DB_PATH.exists():
            st.error(f"❌ Banco de dados não encontrado em: `{DB_PATH}`")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabelas = {row[0] for row in cursor.fetchall()}

        tabelas_esperadas = {"emails", "recortes", "partes", "metadados"}
        faltando = tabelas_esperadas - tabelas

        if faltando:
            st.warning(f"⚠️ Banco conectado, mas faltam tabelas: {', '.join(faltando)}")
        else:
            st.success("✅ Banco de dados carregado e íntegro.")

        conn.close()

    except Exception as e:
        st.error(f"Erro ao verificar integridade do banco: {str(e)}")


# --- Funções principais ---
@st.cache_data(ttl=3600, show_spinner="Carregando dados do banco...")
def carregar_dados() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Carrega dados das tabelas do banco de dados com tratamento robusto de datas

    Returns:
        Tuple contendo DataFrames de: emails, recortes, partes, metadados
    """
    conn = None
    try:
        conn = get_connection()

        logger.info("Carregando dados das tabelas...")
        emails = pd.read_sql_query("SELECT * FROM emails", conn)
        recortes = pd.read_sql_query("SELECT * FROM recortes", conn)
        partes = pd.read_sql_query("SELECT * FROM partes", conn)
        metadados = pd.read_sql_query("SELECT * FROM metadados", conn)

        # Função auxiliar para conversão segura de datas
        def converter_datetime(serie, date_formats=['%d/%m/%Y %H:%M', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']):
            for fmt in date_formats:
                try:
                    return pd.to_datetime(serie, format=fmt, errors='raise')
                except ValueError:
                    continue
            return pd.to_datetime(serie, errors='coerce')

        # Converter colunas de data
        for df in [emails, recortes]:
            if 'data_recebimento' in df.columns:
                df['data_recebimento'] = converter_datetime(df['data_recebimento'])
            if 'data_publicacao' in df.columns:
                df['data_publicacao'] = converter_datetime(df['data_publicacao'])

        logger.info("Dados carregados com sucesso")
        return emails, recortes, partes, metadados

    except sqlite3.Error as e:
        logger.error(f"Erro no banco de dados: {str(e)}", exc_info=True)
        st.error("Erro ao conectar ao banco de dados. Verifique a conexão e tente novamente.")
        st.stop()
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar dados: {str(e)}", exc_info=True)
        st.error("Ocorreu um erro inesperado ao carregar os dados.")
        st.stop()
    finally:
        if conn is not None:
            conn.close()


def configurar_sidebar(recortes: pd.DataFrame, metadados: pd.DataFrame) -> Dict[str, Any]:
    """Configura todos os filtros na sidebar e retorna um dicionário com os valores"""
    st.sidebar.header("🔍 Filtros Avançados")

    min_date = date(2000, 1, 1)
    max_date = date.today()

    # Opções de unidade_fgv, incluindo vazios como "(Vazio)"
    unidades = metadados["unidade_fgv"].fillna("(Vazio)").unique().tolist()
    unidades_opcoes = ["(Todos)"] + sorted(unidades, key=lambda x: x.lower())

    # Opções de número de processo (ordenado desc.)
    processos = metadados["numero_processo"].dropna().unique().tolist()
    processos_ordenados = sorted(processos, reverse=True)
    processos_opcoes = ["(Todos)"] + processos_ordenados

    filtros = {
        'assunto': st.sidebar.text_input("Filtrar por assunto"),
        'remetente': st.sidebar.text_input("Filtrar por remetente"),
        'unidade': st.sidebar.text_input("Filtrar por unidade do e-mail"),
        'unidade_fgv': st.sidebar.selectbox("Filtrar por Unidade FGV (metadado)", unidades_opcoes),  # atualizado
        'numero_processo': st.sidebar.selectbox("Filtrar por Número do Processo", processos_opcoes),  # novo
        'data_de': st.sidebar.date_input("Data de recebimento (de)", value=None, min_value=min_date, max_value=max_date),
        'data_ate': st.sidebar.date_input("Data de recebimento (até)", value=None, min_value=min_date, max_value=max_date),
        'data_pub_de': st.sidebar.date_input("Data de publicação (de)", value=None, min_value=min_date, max_value=max_date, key="data_pub_de"),
        'data_pub_ate': st.sidebar.date_input("Data de publicação (até)", value=None, min_value=min_date, max_value=max_date, key="data_pub_ate"),
        'tipo': st.sidebar.selectbox("Filtrar por tipo de recorte", ["(Todos)"] + sorted(recortes["tipo"].dropna().unique().tolist())),
        'reu': st.sidebar.text_input("Filtrar por réu (nome ou parte do nome)"),
        'keywords': st.sidebar.text_input("Palavras-chave para destacar (separadas por vírgula)")
    }

    if filtros['data_de'] and filtros['data_ate'] and filtros['data_de'] > filtros['data_ate']:
        st.sidebar.error("A data 'de' deve ser anterior à data 'até'")
    if filtros['data_pub_de'] and filtros['data_pub_ate'] and filtros['data_pub_de'] > filtros['data_pub_ate']:
        st.sidebar.error("A data de publicação 'de' deve ser anterior à data 'até'")

    return filtros


def aplicar_filtros(
        emails: pd.DataFrame,
        recortes: pd.DataFrame,
        partes: pd.DataFrame,
        filtros: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica todos os filtros aos DataFrames com tratamento robusto"""
    try:
        # Cópias para não modificar os DataFrames originais
        emails_filtrados = emails.copy()
        recortes_filtrados = recortes.copy()

        # Filtros nos e-mails
        if filtros['assunto']:
            emails_filtrados = emails_filtrados[
                emails_filtrados["assunto"].str.contains(
                    filtros['assunto'], case=False, na=False, regex=False
                )
            ]

        if filtros['remetente']:
            emails_filtrados = emails_filtrados[
                emails_filtrados["remetente"].str.contains(
                    filtros['remetente'], case=False, na=False, regex=False
                )
            ]

        if filtros['unidade']:
            emails_filtrados = emails_filtrados[
                emails_filtrados["area"].str.contains(
                    filtros['unidade'], case=False, na=False, regex=False
                )
            ]

        if filtros['data_de']:
            emails_filtrados = emails_filtrados[
                (emails_filtrados["data_recebimento"].notna()) &
                (emails_filtrados["data_recebimento"].dt.date >= filtros['data_de'])
            ]

        if filtros['data_ate']:
            emails_filtrados = emails_filtrados[
                (emails_filtrados["data_recebimento"].notna()) &
                (emails_filtrados["data_recebimento"].dt.date <= filtros['data_ate'])
            ]

        # Filtros nos recortes
        if filtros['data_pub_de']:
            recortes_filtrados = recortes_filtrados[
                (recortes_filtrados["data_publicacao"].notna()) &
                (recortes_filtrados["data_publicacao"].dt.date >= filtros['data_pub_de'])
            ]

        if filtros['data_pub_ate']:
            recortes_filtrados = recortes_filtrados[
                (recortes_filtrados["data_publicacao"].notna()) &
                (recortes_filtrados["data_publicacao"].dt.date <= filtros['data_pub_ate'])
            ]

        # Aplicação combinada do filtro por tipo E por réu
        tipo_filtrado = recortes_filtrados.copy()

        if filtros['tipo'] != "(Todos)":
            tipo_filtrado = tipo_filtrado[
                tipo_filtrado["tipo"] == filtros['tipo']
            ]

        if filtros['reu']:
            try:
                ids_com_reu = partes[
                    (partes["papel"].str.lower() == "reu") &
                    (partes["parte"].str.contains(filtros['reu'], case=False, na=False, regex=False))
                ]["id_recorte"].unique().tolist()

                # Interseção: tipo AND réu
                tipo_filtrado = tipo_filtrado[
                    tipo_filtrado["id"].isin(ids_com_reu)
                ]
            except Exception as e:
                logger.error(f"Erro ao filtrar por réu: {str(e)}")
                st.warning("Erro ao aplicar filtro por réu")

        # Resultado final dos recortes filtrados
        recortes_filtrados = tipo_filtrado

        # Emails vinculados aos recortes resultantes
        emails_filtrados = emails_filtrados[
            emails_filtrados["message_id"].isin(recortes_filtrados["message_id"])
        ]

        return emails_filtrados, recortes_filtrados

    except Exception as e:
        logger.error(f"Erro ao aplicar filtros: {str(e)}", exc_info=True)
        st.error("Ocorreu um erro ao aplicar os filtros. Verifique os dados e tente novamente.")
        return pd.DataFrame(), pd.DataFrame()



def formatar_data(data) -> str:
    """Formata uma data para exibição amigável"""
    if pd.isna(data):
        return "N/A"
    try:
        return data.strftime('%d/%m/%Y %H:%M')
    except AttributeError:
        return str(data)


def exibir_detalhes_email(email_info: pd.Series) -> None:
    """Exibe os detalhes de um email selecionado"""
    with st.expander("📩 Detalhes do E-mail", expanded=True):
        cols = st.columns(2)

        with cols[0]:
            st.markdown(f"""
            **📌 Assunto:** {email_info.get('assunto', 'N/A')}  
            **📧 Remetente:** {email_info.get('remetente', 'N/A')}  
            **📅 Data Recebimento:** {formatar_data(email_info.get('data_recebimento'))}  
            **🏢 Área:** {email_info.get('area', 'N/A')}  
            """)

        with cols[1]:
            st.markdown(f"""
            **📰 Jornal:** {email_info.get('jornal', 'N/A')}  
            **🔢 Código:** {email_info.get('codigo', 'N/A')}  
            **🏛️ Escritório:** {email_info.get('escritorio', 'N/A')}  
            """)


def destacar_palavras_chave(texto: str, keywords: Optional[str]) -> str:
    """Destaca palavras-chave no texto de forma flexível (substrings, case insensitive)"""
    if not keywords or not isinstance(texto, str):
        return texto

    try:
        # Limpa e divide as palavras-chave
        palavras = [kw.strip() for kw in re.split(r"[;,]", keywords) if kw.strip()]

        # Para cada palavra-chave, destacar todas as ocorrências como substrings
        for palavra in palavras:
            if not palavra:  # Pula strings vazias
                continue

            # Usa regex para encontrar todas as ocorrências (case insensitive)
            pattern = re.compile(re.escape(palavra), re.IGNORECASE)
            texto = pattern.sub(
                lambda match: f'<span style="background-color: #ffff00; font-weight: bold;">{match.group(0)}</span>',
                texto
            )

        return texto
    except Exception as e:
        logger.error(f"Erro ao destacar palavras-chave: {str(e)}")
        return texto


def exibir_recortes(
        recortes_email: pd.DataFrame,
        partes: pd.DataFrame,
        metadados: pd.DataFrame,
        keywords: Optional[str] = None
) -> None:
    """Exibe todos os recortes de um email com tratamento robusto"""
    if recortes_email.empty:
        st.warning("Nenhum recorte encontrado para este e-mail.")
        return

    for _, rec in recortes_email.iterrows():
        try:
            with st.container():
                st.markdown("---")
                st.markdown(f"### 🔖 Recorte ID: {rec.get('id', 'N/A')} — Tipo: `{rec.get('tipo', 'N/A')}`")

                # Justificativa da IA
                if pd.notna(rec.get("justificativa_ia")):
                    with st.expander("💡 Justificativa da Classificação"):
                        st.info(rec["justificativa_ia"])

                # Metadados básicos
                cols = st.columns(3)
                with cols[0]:
                    st.markdown(f"**🔎 Nome Pesquisado:** {rec.get('nome_pesquisado', 'N/A')}")
                with cols[1]:
                    st.markdown(f"**⚖️ Tribunal:** {rec.get('tribunal', 'N/A')}")
                with cols[2]:
                    st.markdown(f"**📅 Data Publicação:** {formatar_data(rec.get('data_publicacao'))}")

                # Texto da publicação com highlight
                with st.expander("📝 Texto da Publicação", expanded=False):
                    texto = str(rec.get('publicacao', 'Texto não disponível'))
                    texto_destacado = destacar_palavras_chave(texto, keywords)
                    st.markdown(texto_destacado, unsafe_allow_html=True)

                # Partes do processo
                partes_recorte = partes[partes["id_recorte"] == rec["id"]]
                if not partes_recorte.empty:
                    with st.expander("👥 Partes Envolvidas", expanded=False):
                        for papel in partes_recorte["papel"].unique():
                            nomes = partes_recorte[partes_recorte["papel"] == papel]["parte"].tolist()
                            st.markdown(f"**{str(papel).capitalize()}:**")
                            for nome in nomes:
                                st.markdown(f"- {nome}")

                # Metadados extraídos
                metadado = metadados[metadados["id_recorte"] == rec["id"]]
                if not metadado.empty:
                    with st.expander("📊 Metadados Extraídos", expanded=False):
                        dados = metadado.iloc[0].drop(labels=["id", "id_recorte"], errors='ignore').to_dict()
                        for campo, valor in dados.items():
                            if pd.notna(valor):
                                st.markdown(f"**{str(campo).replace('_', ' ').title()}:** {valor}")

        except Exception as e:
            logger.error(f"Erro ao exibir recorte ID {rec.get('id', 'unknown')}: {str(e)}", exc_info=True)
            st.error(f"Erro ao exibir um dos recortes. Detalhes foram registrados no log.")


# --- Página Principal ---
def main():
    st.title("📬 Análise dos Dados do Pipeline SJUR")

    # Verificação visual da saúde do banco
    check_health()

    # Carregar dados
    with st.spinner("Carregando dados do banco..."):
        emails, recortes, partes, metadados = carregar_dados()

    # Configurar sidebar e obter filtros
    filtros = configurar_sidebar(recortes, metadados)


    # Aplicar filtros
    with st.spinner("Aplicando filtros..."):
        emails_filtrados, recortes_filtrados = aplicar_filtros(
            emails, recortes, partes, filtros
        )

    # 🔍 Filtro por Unidade FGV
    if filtros.get("unidade_fgv") and filtros["unidade_fgv"] != "(Todos)":
        valor = None if filtros["unidade_fgv"] == "(Vazio)" else filtros["unidade_fgv"]
        ids_unidade = metadados[
            metadados["unidade_fgv"].fillna("(Vazio)") == filtros["unidade_fgv"]
            ]["id_recorte"].unique().tolist()

        recortes_filtrados = recortes_filtrados[recortes_filtrados["id"].isin(ids_unidade)]
        emails_filtrados = emails_filtrados[emails_filtrados["message_id"].isin(recortes_filtrados["message_id"])]

    # 🔍 Filtro por Número do Processo
    if filtros.get("numero_processo") and filtros["numero_processo"] != "(Todos)":
        ids_proc = metadados[
            metadados["numero_processo"] == filtros["numero_processo"]
            ]["id_recorte"].unique().tolist()

        recortes_filtrados = recortes_filtrados[recortes_filtrados["id"].isin(ids_proc)]
        emails_filtrados = emails_filtrados[emails_filtrados["message_id"].isin(recortes_filtrados["message_id"])]

    # Mostrar estatísticas na sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Estatísticas")
    st.sidebar.markdown(f"- **E-mails encontrados:** {len(emails_filtrados)}")
    st.sidebar.markdown(f"- **Recortes encontrados:** {len(recortes_filtrados)}")

    # Opção para exportar dados
    if not emails_filtrados.empty:
        try:
            csv = emails_filtrados.to_csv(index=False, encoding='utf-8').encode('utf-8')
            st.sidebar.download_button(
                "⬇️ Exportar E-mails Filtrados",
                csv,
                "emails_filtrados.csv",
                "text/csv",
                help="Exporta a lista de e-mails com os filtros atuais"
            )
        except Exception as e:
            logger.error(f"Erro ao exportar dados: {str(e)}")
            st.sidebar.error("Erro ao preparar dados para exportação")

    # Seção principal - Listagem de e-mails
    st.subheader("✉️ E-mails Processados")

    if emails_filtrados.empty:
        st.warning("Nenhum e-mail encontrado com os filtros aplicados.")
        st.stop()

    # Paginação com validação
    page_size = st.sidebar.selectbox("Itens por página", [5, 10, 20, 50], index=1)
    total_pages = max(1, (len(emails_filtrados) // page_size) + 1)

    try:
        page_number = st.number_input(
            'Página',
            min_value=1,
            max_value=total_pages,
            value=1,
            help=f"Navegue entre as {total_pages} páginas de resultados"
        )

        # Selecionar e-mail
        emails_paginados = emails_filtrados.iloc[
                           (page_number - 1) * page_size: page_number * page_size
                           ]

        email_options = {
            row[
                "message_id"]: f"{row['assunto'][:70]}{'...' if len(row['assunto']) > 70 else ''} | {formatar_data(row.get('data_recebimento'))}"
            for _, row in emails_paginados.iterrows()
        }

        email_selecionado = st.selectbox(
            "Selecione um e-mail para detalhar:",
            options=list(email_options.keys()),
            format_func=lambda x: email_options[x]
        )

        # Detalhes do e-mail selecionado
        email_info = emails_filtrados[emails_filtrados["message_id"] == email_selecionado].iloc[0]
        exibir_detalhes_email(email_info)

        # Recortes vinculados ao e-mail
        st.subheader("📎 Recortes Vinculados")
        recortes_email = recortes_filtrados[
            recortes_filtrados["message_id"] == email_selecionado
            ]

        exibir_recortes(recortes_email, partes, metadados, filtros['keywords'])

    except Exception as e:
        logger.error(f"Erro na interface principal: {str(e)}", exc_info=True)
        st.error("Ocorreu um erro ao exibir os dados. Tente recarregar a página.")


if __name__ == "__main__":
    main()