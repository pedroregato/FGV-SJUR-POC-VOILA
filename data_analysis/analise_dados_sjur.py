import streamlit as st
import sqlite3
import pandas as pd
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

# Aplicar filtros
filtro = emails.copy()
if filtro_assunto:
    filtro = filtro[filtro["assunto"].str.contains(filtro_assunto, case=False, na=False)]
if filtro_remetente:
    filtro = filtro[filtro["remetente"].str.contains(filtro_remetente, case=False, na=False)]

st.sidebar.markdown(f"**{len(filtro)}** e-mail(s) encontrados.")

# Master: listagem de e-mails
st.subheader("✉️ E-mails processados")
email_selecionado = st.selectbox("Selecione um e-mail:", filtro["message_id"].tolist())

# Detalhes do e-mail
email_info = filtro[filtro["message_id"] == email_selecionado].iloc[0]
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
recortes_email = recortes[recortes["message_id"] == email_selecionado]
st.subheader("📎 Recortes vinculados")

for _, rec in recortes_email.iterrows():
    st.markdown("---")
    st.markdown(f"### 🔖 Recorte ID: {rec['id']} — Tipo: {rec['tipo']}")
    st.markdown(f"**Nome Pesquisado:** {rec['nome_pesquisado']}  \n"
                f"**Tribunal:** {rec['tribunal']}  \n"
                f"**Secretaria:** {rec['secretaria']}  \n"
                f"**Data Publicação:** {rec['data_publicacao']}")

    with st.expander("📝 Texto da publicação"):
        st.write(rec['publicacao'])

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
