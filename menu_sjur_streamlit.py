import streamlit as st
from pathlib import Path

# Configuração da página
st.set_page_config(page_title="SJUR - Menu Principal", layout="centered", page_icon="📘")

# Título principal
st.markdown("""
    <h1 style='text-align: center;'>SJUR - Coleta e Tratamento das Publicações da SERDON</h1>
    <h3 style='text-align: center; color: gray;'>DTI/SOLCORP - Soluções Corporativas</h3>
    <p style='text-align: center; font-size: 16px;'>Autor: Pedro Gentil</p>
""", unsafe_allow_html=True)

# Estilo CSS customizado
st.markdown("""
    <style>
    .menu-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 2rem;
        margin: 4rem auto;
        max-width: 800px;
    }
    .menu-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: #1f77b4;
        color: white;
        border-radius: 16px;
        padding: 2rem;
        height: 200px;
        transition: 0.3s;
    }
    .menu-item:hover {
        transform: scale(1.03);
        cursor: pointer;
        background: #1665a2;
    }
    .menu-item.disabled {
        background: #999;
        cursor: not-allowed;
    }
    .menu-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Caminho relativo para a pasta pages
PAGES_DIR = "pages"

# Cria os elementos do menu
st.markdown('<div class="menu-grid">', unsafe_allow_html=True)

# Validação (ativo)
if st.button("", key="val_btn"):
    st.switch_page(f"{PAGES_DIR}/analise_dados_sjur.py")

st.markdown(f"""
<div class="menu-item" onclick="document.querySelector('[data-testid=\"stButton\"] button[data-baseweb]').click()">
    <div class="menu-icon">🔍</div>
    <div><strong>Validação</strong><br><span style='font-size: 0.9rem;'>Análise dos dados coletados</span></div>
</div>
""", unsafe_allow_html=True)

# Resultados de Interesse (desativado)
st.markdown("""
<div class="menu-item disabled">
    <div class="menu-icon">📊</div>
    <div><strong>Resultados de Interesse</strong><br><span style='font-size: 0.9rem;'>Em breve</span></div>
</div>
""", unsafe_allow_html=True)

# Consulta DataJud (desativado)
st.markdown("""
<div class="menu-item disabled" style="grid-column: span 2;">
    <div class="menu-icon">📈</div>
    <div><strong>Consulta DataJud</strong><br><span style='font-size: 0.9rem;'>Em breve</span></div>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
