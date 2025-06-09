import streamlit as st
from pathlib import Path
from PIL import Image
import base64

# Configuração da página
st.set_page_config(page_title="SJUR - Menu Principal", layout="centered", page_icon="📘")

# Título principal
st.markdown("""
    <h1 style='text-align: center;'>SJUR - Coleta e Tratamento das Publicações da SERDON</h1>
    <h3 style='text-align: center; color: gray;'>DTI/SOLCORP - Soluções Corporativas</h3>
    <p style='text-align: center; font-size: 16px;'>Autor: Pedro Gentil</p>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    .menu-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        justify-items: center;
        align-items: center;
        margin-top: 3rem;
    }
    .menu-item {
        border: 2px solid #ccc;
        border-radius: 1rem;
        padding: 2rem;
        width: 200px;
        height: 200px;
        text-align: center;
        transition: all 0.2s ease-in-out;
    }
    .menu-item:hover {
        border-color: #1f77b4;
        box-shadow: 0px 0px 12px rgba(0, 0, 0, 0.2);
        cursor: pointer;
    }
    .menu-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

# Caminhos relativos para os scripts
SCRIPT_DIR = Path(__file__).resolve().parent
STREAMLIT_DIR = SCRIPT_DIR / "pages"

# --- Funções de navegação ---
def redirecionar_para(caminho_script: Path):
    st.switch_page(str(caminho_script.relative_to(SCRIPT_DIR)))

# --- Itens do menu ---
with col1:
    if st.button("\U0001F50D\nValidação", use_container_width=True):
        redirecionar_para(STREAMLIT_DIR / "analise_dados_sjur.py")

    if st.button("\U0001F50E\nResultados de Interesse", use_container_width=True):
        st.info("Esta funcionalidade ainda está em desenvolvimento.")

with col2:
    if st.button("\U0001F4CA\nConsulta DataJud", use_container_width=True):
        st.info("Esta funcionalidade ainda está em desenvolvimento.")
