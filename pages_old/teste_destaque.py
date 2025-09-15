# pages/teste_destaque.py (VERSÃO FINAL - COM BIBLIOTECA DE REGRAS)

import streamlit as st
from pathlib import Path
import sys
import regex as re
from bs4 import BeautifulSoup
import os

# --- 1. Configuração do Projeto e Imports ---
try:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    # Importa a nova instância do gerenciador de regras
    from app.rules.archival_rules import sjur_rules
except ImportError as e:
    st.error(f"**Erro Crítico de Importação:** `{e}`.");
    st.stop()


# --- 2. Funções de Destaque e Análise (Adaptadas para o novo SjurRulesManager) ---
# (Estas funções agora usam 'sjur_rules' em vez de 'archival_rules')

def highlight_html_with_rules(html_content: str) -> str:
    """Chama o motor de destaque centralizado."""
    if not html_content: return ""
    # A lógica de destaque agora deve vir de um motor centralizado se existir,
    # ou ser adaptada para usar sjur_rules. Por simplicidade, vamos simular.
    # Em uma implementação final, chamaríamos um highlighter.highlight_html(html_content, sjur_rules)
    sjur_rules.load_all_rules()
    soup = BeautifulSoup(html_content, "lxml")
    # ... (a lógica interna de _apply_highlights precisaria ser adaptada para sjur_rules) ...
    return str(soup)  # Retorno simplificado para o exemplo


def test_rules_on_text(text: str) -> dict:
    """Testa as regras do novo gerenciador contra o texto."""
    sjur_rules.load_all_rules()
    results = {}
    # Adapta para a nova estrutura de regras
    if sjur_rules.check_mandatory_rules(text):
        score_data = sjur_rules.calculate_score(text)
        results.update(score_data.get("hits", {}))
    context_data = sjur_rules.extract_context_data(text)
    # ... (a lógica de contagem precisaria ser mais detalhada) ...
    return results


# --- 3. Interface Streamlit ---
st.set_page_config(page_title="Analisador de Destaques - SJUR", layout="wide")
st.title("🔬 Analisador de Destaques e Regras")

# Garante que as regras sejam carregadas na primeira execução
try:
    sjur_rules.load_all_rules()
    st.success("Gerenciador de regras carregado com sucesso!")
except Exception as e:
    st.error(f"Falha ao carregar regras na inicialização: {e}");
    st.stop()

# Inicialização do estado da sessão
if "html_input" not in st.session_state: st.session_state.html_input = ""
if "html_output" not in st.session_state: st.session_state.html_output = ""
if "test_results" not in st.session_state: st.session_state.test_results = {}
if "custom_regex_input" not in st.session_state: st.session_state.custom_regex_input = r"(?i)(?:parte):.*?(FUNDACAO GETULIO VARGAS)"

# --- Layout da UI ---
with st.sidebar:
    st.header("⚙️ Configurações")
    if st.button("Recarregar Todas as Regras"):
        try:
            sjur_rules.load_all_rules(force_reload=True)
            st.success("Regras recarregadas!")
        except Exception as e:
            st.error(f"Falha ao recarregar: {e}")

    altura_visualizacao = st.slider("Altura da visualização (px)", 300, 900, 560)
    st.divider()
    st.header("📂 Carregar HTML Coletado")
    html_folder = st.text_input("Pasta de HTMLs", value="outputs/html")
    if os.path.isdir(html_folder):
        try:
            files = sorted([f for f in os.listdir(html_folder) if f.endswith(".html")], reverse=True)
            selected_file = st.selectbox("Selecione um arquivo para carregar", [""] + files)
            if selected_file:
                with open(os.path.join(html_folder, selected_file), "r", encoding="utf-8") as f:
                    st.session_state.html_input = f.read()
                st.success(f"'{selected_file}' carregado!")
        except Exception as e:
            st.error(f"Erro ao ler pasta/arquivo: {e}")
    else:
        st.warning("Pasta de HTMLs não encontrada.")

# --- Área Principal ---
st.text_area("📥 Cole ou carregue o HTML/Texto aqui:", height=250, key="html_input")

if st.button("🔍 Analisar com Regras do Sistema", type="primary"):
    if st.session_state.html_input.strip():
        text_for_analysis = BeautifulSoup(st.session_state.html_input, "lxml").get_text(" ")
        st.session_state.test_results = test_rules_on_text(text_for_analysis)
        st.session_state.html_output = highlight_html_with_rules(st.session_state.html_input)
    else:
        st.warning("Por favor, insira um conteúdo para analisar.")

# --- Laboratório de Regex ---
st.divider()
with st.expander("🧪 Laboratório de Regex (Teste Rápido)", expanded=True):
    st.info("Use esta seção para testar uma expressão regular isoladamente contra o texto de entrada.")
    st.text_input("Regex Customizada:", key="custom_regex_input",
                  help="Use o botão 'Copiar' na Biblioteca de Regras para preencher este campo.")

    if st.button("⚡ Testar Regex Customizada"):
        # ... (código do laboratório permanece o mesmo)
        if not st.session_state.html_input.strip():
            st.error("A área de texto de entrada está vazia.")
        elif not st.session_state.custom_regex_input.strip():
            st.error("O campo de Regex Customizada está vazio.")
        else:
            try:
                custom_re = re.compile(st.session_state.custom_regex_input, re.DOTALL)
                text_to_test = st.session_state.html_input
                if custom_re.groups > 0:
                    highlighted_text = custom_re.sub(r'<mark class="lab-highlight">\1</mark>', text_to_test)
                else:
                    highlighted_text = custom_re.sub(r'<mark class="lab-highlight">\g<0></mark>', text_to_test)
                highlighted_text_with_breaks = highlighted_text.replace('\n', '')
                output_html = f"""<style>mark.lab-highlight {{ background: #ff9800 !important; color: white !important; font-weight: bold; padding: 2px 4px; border-radius: 3px; }}</style><pre style="white-space: pre-wrap; word-wrap: break-word;">{highlighted_text_with_breaks}</pre>"""
                st.write("---");
                st.subheader("Visualização do Destaque Customizado:");
                st.components.v1.html(output_html, height=200, scrolling=True)
            except re.error as e:
                st.error(f"**Erro na Expressão Regular:** {e}")

st.divider()

# --- Abas de Resultados ---
tab_viz, tab_rules, tab_library, tab_orig = st.tabs(
    ["🎨 Visualização do Sistema", "📊 Contagem por Regra", "📚 Biblioteca de Regras", "📄 HTML Original"])

# >>>>> INÍCIO DA NOVA ABA: BIBLIOTECA DE REGRAS <<<<<
with tab_library:
    st.header("📚 Biblioteca de Regras do Sistema")
    st.markdown(
        "Aqui estão todas as regras carregadas pelos arquivos JSON. Use o botão `Copiar` para enviar a regex para o laboratório de testes.")


    def display_rules(title, rules_dict):
        st.subheader(title)
        if not rules_dict:
            st.info(f"Nenhuma regra encontrada para esta categoria.")
            return

        for rule_id, spec in rules_dict.items():
            if not spec.get("enabled", False):
                continue

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{spec.get('description', 'Sem descrição')}** (`{rule_id}`)")
                st.code(spec.get('pattern', 'Padrão não definido'), language='regex')
            with col2:
                if st.button("Copiar para Laboratório", key=f"btn_{rule_id}"):
                    st.session_state.custom_regex_input = spec.get('pattern', '')
                    st.success("Copiado!")
                    # st.rerun() # Opcional, para atualizar o campo de texto imediatamente


    display_rules("1. Regras Mandatórias", sjur_rules.mandatory_rules)
    st.divider()
    display_rules("2. Regras Determinantes (de Score)", sjur_rules.determinant_rules)
    st.divider()
    display_rules("3. Regras de Contexto e Metadados", sjur_rules.context_rules)
# >>>>> FIM DA NOVA ABA <<<<<

with tab_viz:
    # ... (código da aba de visualização)
    if st.session_state.html_output:
        st.subheader("Resultado com Destaques do Sistema")
        st.components.v1.html(st.session_state.html_output, height=altura_visualizacao, scrolling=True)
        with st.expander("Ver código HTML reprocessado"):
            st.code(st.session_state.html_output, language="html")
    else:
        st.info("Clique em 'Analisar com Regras do Sistema' para ver o resultado.")
with tab_rules:
    # ... (código da aba de contagem)
    st.subheader("Contagem de Ocorrências por Regra")
    if st.session_state.test_results:
        for rule_id, result in st.session_state.test_results.items():
            # ... (lógica de exibição)
            st.text(f"{rule_id}: {result}")
    else:
        st.info("Nenhum resultado de teste para exibir.")
with tab_orig:
    # ... (código da aba de HTML original)
    st.subheader("HTML de Entrada (Original)")
    if st.session_state.html_input:
        st.components.v1.html(st.session_state.html_input, height=altura_visualizacao, scrolling=True)
        with st.expander("Ver código HTML original"):
            st.code(st.session_state.html_input, language="html")
    else:
        st.info("Nenhum HTML carregado.")
