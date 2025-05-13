import streamlit as st
import sqlite3
import pandas as pd
import re
from datetime import datetime
from app.database.db_connection import get_connection

# Conexão e carregamento
@st.cache_data
def carregar_dados():
    conn = get_connection()
    emails = pd.read_sql_query("SELECT * FROM emails", conn)
    recortes = pd.read_sql_query("SELECT * FROM recortes", conn)
    partes = pd.read_sql_query("SELECT * FROM partes", conn)
    metadados = pd.read_sql_query("SELECT * FROM metadados", conn)
    conn.close()
    return emails, recortes, partes, metadados

# Interface
st.set_page_config(layout="wide")
st.title("📬 Análise dos Dados do Pipeline SJUR")

emails, recortes, partes, metadados = carregar_dados()

# Sidebar com filtros
st.sidebar.header("🔍 Filtros")
filtro_assunto = st.sidebar.text_input("Filtrar por assunto")
filtro_remetente = st.sidebar.text_input("Filtrar por remetente")
filtro_unidade = st.sidebar.text_input("Filtrar por unidade FGV")
filtro_data_de = st.sidebar.date_input("Data de recebimento (de)", value=None)
filtro_data_ate = st.sidebar.date_input("Data de recebimento (até)", value=None)
filtro_data_pub_de = st.sidebar.date_input("Data de publicação (de)", value=None, key="data_pub_de")
filtro_data_pub_ate = st.sidebar.date_input("Data de publicação (até)", value=None, key="data_pub_ate")
tipos_disponiveis = recortes["tipo"].dropna().unique().tolist()
tipos_disponiveis.sort()
filtro_tipo = st.sidebar.selectbox("Filtrar por tipo de recorte", ["(Todos)"] + tipos_disponiveis)
filtro_reu = st.sidebar.text_input("Filtrar por réu (nome ou parte do nome)")
filtro_keywords = st.sidebar.text_input("Palavras-chave para destacar (separadas por , ou ;)")

# Filtro: emails
filtro_emails = emails.copy()
if filtro_assunto:
    filtro_emails = filtro_emails[filtro_emails["assunto"].str.contains(filtro_assunto, case=False, na=False)]
if filtro_remetente:
    filtro_emails = filtro_emails[filtro_emails["remetente"].str.contains(filtro_remetente, case=False, na=False)]
if filtro_unidade:
    filtro_emails = filtro_emails[filtro_emails["area"].str.contains(filtro_unidade, case=False, na=False)]
if filtro_data_de:
    filtro_emails = filtro_emails[pd.to_datetime(filtro_emails["data_recebimento"], errors="coerce") >= pd.to_datetime(filtro_data_de)]
if filtro_data_ate:
    filtro_emails = filtro_emails[pd.to_datetime(filtro_emails["data_recebimento"], errors="coerce") <= pd.to_datetime(filtro_data_ate)]

# Filtro: recortes
recortes_filtrados = recortes.copy()
if filtro_tipo != "(Todos)":
    recortes_filtrados = recortes_filtrados[recortes_filtrados["tipo"] == filtro_tipo]
if filtro_data_pub_de:
    recortes_filtrados = recortes_filtrados[pd.to_datetime(recortes_filtrados["data_publicacao"], errors="coerce") >= pd.to_datetime(filtro_data_pub_de)]
if filtro_data_pub_ate:
    recortes_filtrados = recortes_filtrados[pd.to_datetime(recortes_filtrados["data_publicacao"], errors="coerce") <= pd.to_datetime(filtro_data_pub_ate)]

# Filtro: réu
if filtro_reu:
    ids_com_reu = partes[
        (partes["papel"].str.lower() == "réu") &
        (partes["parte"].str.contains(filtro_reu, case=False, na=False))
    ]["id_recorte"].unique().tolist()
    recortes_filtrados = recortes_filtrados[recortes_filtrados["id"].isin(ids_com_reu)]

# Filtro cruzado: emails que têm recortes filtrados
emails_filtrados = filtro_emails[filtro_emails["message_id"].isin(recortes_filtrados["message_id"])]

st.sidebar.markdown(f"**{len(emails_filtrados)}** e-mail(s) encontrados.")

# Master: listagem de e-mails
st.subheader("✉️ E-mails processados")
if emails_filtrados.empty:
    st.warning("Nenhum e-mail encontrado com os filtros aplicados.")
    st.stop()

email_selecionado = st.selectbox("Selecione um e-mail:", emails_filtrados["message_id"].tolist())

# Detalhes do e-mail
email_info = emails_filtrados[emails_filtrados["message_id"] == email_selecionado].iloc[0]
st.markdown(f"""
**Assunto:** {email_info['assunto']}  
**Remetente:** {email_info['remetente']}  
**Data Recebimento:** {email_info['data_recebimento']}  
**Jornal:** {email_info['jornal']}  
**Código:** {email_info['codigo']}  
**Área:** {email_info['area']}  
**Escritório:** {email_info['escritorio']}  
""")

# Recortes vinculados
recortes_email = recortes_filtrados[recortes_filtrados["message_id"] == email_selecionado]
st.subheader("📎 Recortes vinculados")

for _, rec in recortes_email.iterrows():
    st.markdown("---")
    st.markdown(f"### 🔖 Recorte ID: {rec['id']} — Tipo: {rec['tipo']}")

    if rec.get("justificativa_ia"):
        st.markdown(f"💬 **Justificativa da IA:** {rec['justificativa_ia']}")

    st.markdown(f"**Nome Pesquisado:** {rec['nome_pesquisado']}  \n"
                f"**Tribunal:** {rec['tribunal']}  \n"
                f"**Secretaria:** {rec['secretaria']}  \n"
                f"**Data Publicação:** {rec['data_publicacao']}")

    with st.expander("📝 Texto da publicação"):
        texto = rec['publicacao']
        if filtro_keywords:
            for kw in re.split(r"[;,]", filtro_keywords):
                kw = kw.strip()
                if kw:
                    texto = texto.replace(kw, f"**:blue[{kw}]**")
        st.markdown(texto, unsafe_allow_html=True)

    # Partes
    partes_recorte = partes[partes["id_recorte"] == rec["id"]]
    if not partes_recorte.empty:
        st.markdown("**👤 Partes identificadas:**")
        for papel in partes_recorte["papel"].unique():
            nomes = partes_recorte[partes_recorte["papel"] == papel]["parte"].tolist()
            st.markdown(f"- **{papel.capitalize()}(s):** {', '.join(nomes)}")

    # Metadados
    metadado = metadados[metadados["id_recorte"] == rec["id"]]
    if not metadado.empty:
        st.markdown("**📊 Metadados extraídos via LLM:**")
        dados = metadado.iloc[0].drop(labels=["id", "id_recorte"]).to_dict()
        for campo, valor in dados.items():
            st.markdown(f"- **{campo.replace('_', ' ').capitalize()}:** {valor}")
    else:
        st.warning("⚠️ Nenhum metadado encontrado para este recorte.")
