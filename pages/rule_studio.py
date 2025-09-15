# pages/rule_studio.py (VERSÃO REFATORADA)

import streamlit as st
import regex as re
from bs4 import BeautifulSoup
import json
from app.rules.archival_rules import sjur_rules
from app.styles.highlighter import apply_manual_highlight, generate_css_from_style_data

st.set_page_config(page_title="Estúdio de Regras - SJUR", layout="wide")


# --- Funções Auxiliares Refatoradas ---
def extract_hex_color(color_value):
    """Extrai apenas a parte hexadecimal de um valor de cor CSS, removendo !important"""
    if not color_value:
        return "#ffffff"

    # Remove !important e espaços extras
    clean_color = color_value.split("!important")[0].strip()
    return clean_color


def create_color_picker(label, color_value, default_color, key):
    """Cria um color_picker padronizado extraindo apenas a parte hexadecimal"""
    clean_color = extract_hex_color(color_value) if color_value else default_color
    return st.color_picker(label, value=clean_color, key=key)


def save_rules_to_json(file_path, rules_dict):
    try:
        # Cria uma cópia do dicionário removendo objetos não serializáveis
        serializable_dict = {}
        for rule_id, rule_spec in rules_dict.items():
            serializable_rule = rule_spec.copy()

            # Remove qualquer atributo que comece com underscore (como _compiled_regex)
            keys_to_remove = [key for key in serializable_rule.keys() if key.startswith('_')]
            for key in keys_to_remove:
                del serializable_rule[key]

            # Se houver estilo, também remove atributos com underscore
            if 'style' in serializable_rule:
                style_keys_to_remove = [key for key in serializable_rule['style'].keys() if key.startswith('_')]
                for key in style_keys_to_remove:
                    del serializable_rule['style'][key]

            serializable_dict[rule_id] = serializable_rule

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Falha ao salvar o arquivo {file_path.name}: {e}")
        return False


def get_target_file_and_dict(rule_id):
    """Retorna o arquivo e dicionário alvo para uma regra específica"""
    if rule_id in sjur_rules.mandatory_rules:
        return sjur_rules.mandatory_rules_file, clean_dict_for_serialization(sjur_rules.mandatory_rules)
    elif rule_id in sjur_rules.determinant_rules:
        return sjur_rules.determinant_rules_file, clean_dict_for_serialization(sjur_rules.determinant_rules)
    elif rule_id in sjur_rules.context_rules:
        return sjur_rules.context_rules_file, clean_dict_for_serialization(sjur_rules.context_rules)
    return None, None


def clean_dict_for_serialization(rules_dict):
    """Remove objetos não serializáveis do dicionário de regras"""
    cleaned_dict = {}
    for rule_id, rule_spec in rules_dict.items():
        cleaned_rule = rule_spec.copy()

        # Remove atributos que começam com underscore
        keys_to_remove = [key for key in cleaned_rule.keys() if key.startswith('_')]
        for key in keys_to_remove:
            del cleaned_rule[key]

        # Limpa também o dicionário de estilo se existir
        if 'style' in cleaned_rule:
            style_keys_to_remove = [key for key in cleaned_rule['style'].keys() if key.startswith('_')]
            for key in style_keys_to_remove:
                del cleaned_rule['style'][key]

        cleaned_dict[rule_id] = cleaned_rule

    return cleaned_dict


def render_rule_button(rule_id, spec):
    """Renderiza um botão de regra com estilo consistente"""
    style = spec.get("style", {})
    bg_color = style.get("background_color", "#f0f2f6")
    text_color = style.get("text_color", "#31333F")
    border_color = text_color if bg_color.lower() in ['#ffffff', '#fff'] else 'transparent'

    button_style = f"""
    div[data-testid="stButton"] > button[data-test-id="btn_{rule_id}"] {{
        background-color: {bg_color}; 
        color: {text_color}; 
        border: 1px solid {border_color}; 
        width: 100%; 
    }}
    """
    st.markdown(f"<style>{button_style}</style>", unsafe_allow_html=True)

    if st.button(spec['description'], key=f"btn_{rule_id}", use_container_width=True):
        st.session_state.selected_rule_id = rule_id


def render_statistics():
    """Renderiza as estatísticas de configuração"""
    st.header("📊 Configuração das Regras")

    # Calcula estatísticas
    ALL_RULES = {**sjur_rules.mandatory_rules, **sjur_rules.determinant_rules, **sjur_rules.context_rules}
    total_rules = len(ALL_RULES)
    enabled_rules = sum(1 for rule in ALL_RULES.values() if rule.get('enabled', True))

    mandatory_count = len(sjur_rules.mandatory_rules)
    mandatory_enabled = sum(1 for rule in sjur_rules.mandatory_rules.values() if rule.get('enabled', True))

    determinant_count = len(sjur_rules.determinant_rules)
    determinant_enabled = sum(1 for rule in sjur_rules.determinant_rules.values() if rule.get('enabled', True))

    context_count = len(sjur_rules.context_rules)
    context_enabled = sum(1 for rule in sjur_rules.context_rules.values() if rule.get('enabled', True))

    # Cards de resumo
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", total_rules)
    with col2:
        st.metric("Ativas", enabled_rules)
    with col3:
        st.metric("Taxa", f"{enabled_rules / total_rules * 100:.1f}%")

    # Barras de progresso por categoria
    st.write("**Ativação por Categoria:**")

    st.caption("🔐 Mandatórias")
    st.progress(mandatory_enabled / mandatory_count if mandatory_count > 0 else 0)
    st.caption(f"{mandatory_enabled}/{mandatory_count}")

    st.caption("🎯 Determinantes")
    st.progress(determinant_enabled / determinant_count if determinant_count > 0 else 0)
    st.caption(f"{determinant_enabled}/{determinant_count}")

    st.caption("🏷️ Contextuais")
    st.progress(context_enabled / context_count if context_count > 0 else 0)
    st.caption(f"{context_enabled}/{context_count}")


# --- Inicialização e Carregamento de Regras ---
try:
    sjur_rules.load_all_rules(force_reload=True)
    ALL_RULES = {**sjur_rules.mandatory_rules, **sjur_rules.determinant_rules, **sjur_rules.context_rules}
except Exception as e:
    st.error(f"**Erro fatal ao carregar as regras:** {e}")
    st.stop()

st.sidebar.checkbox("Modo Debug", key="debug_mode")

# --- Layout da Aplicação ---
st.title("🎨 Estúdio de Regras e Estilos")
st.markdown("Uma ferramenta dedicada para visualizar, testar e **editar** as regras de análise do sistema.")

# --- SEÇÃO 1: Biblioteca de Regras (Sidebar) ---
with st.sidebar:
    st.header("📚 Biblioteca de Regras")
    st.info("Selecione uma regra para carregar na Bancada de Edição.")

    if 'selected_rule_id' not in st.session_state:
        st.session_state.selected_rule_id = list(sjur_rules.determinant_rules.keys())[0]

    with st.expander("1. Regras Mandatórias", expanded=False):
        for rule_id, spec in sjur_rules.mandatory_rules.items():
            render_rule_button(rule_id, spec)

    with st.expander("2. Regras Determinantes (Score)", expanded=False):
        st.subheader("Tipo: Proximidade")
        for rule_id, spec in sjur_rules.determinant_rules.items():
            if spec.get("type") == "proximity":
                render_rule_button(rule_id, spec)

        st.subheader("Tipo: Básica")
        for rule_id, spec in sjur_rules.determinant_rules.items():
            if spec.get("type") == "basic":
                render_rule_button(rule_id, spec)

    with st.expander("3. Regras de Contexto e Metadados", expanded=False):
        for rule_id, spec in sjur_rules.context_rules.items():
            render_rule_button(rule_id, spec)

    # Estatísticas
    with st.expander("📊 Estatísticas de Configuração", expanded=False):
        render_statistics()

# --- SEÇÃO 2: Bancada de Edição e Testes ---
st.header("🛠️ Bancada de Edição e Testes")

selected_id = st.session_state.selected_rule_id
spec = ALL_RULES.get(selected_id)
if not spec:
    st.error("Regra selecionada não encontrada.")
    st.stop()

st.subheader(f"Editando: `{selected_id}`")
st.write(f"_{spec.get('description', 'Sem descrição.')}_")

with st.container(border=True):
    new_pattern = st.text_area("Padrão Regex:", value=spec.get("pattern", ""), height=100, key=f"pattern_{selected_id}")

    is_determinant_rule = selected_id in sjur_rules.determinant_rules
    new_score = None
    if is_determinant_rule:
        new_score = st.number_input("Score da Regra:", min_value=-5.0, max_value=5.0,
                                    value=float(spec.get("score", 0.0)), step=0.1,
                                    format="%.2f", key=f"score_{selected_id}")

    style_data = spec.get("style", {})
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        new_bg_color = create_color_picker("Cor de Fundo",
                                           style_data.get("background_color"),
                                           "#ffffff",
                                           f"bg_{selected_id}")

    with col2:
        new_text_color = create_color_picker("Cor do Texto",
                                             style_data.get("text_color"),
                                             "#000000",
                                             f"txt_{selected_id}")

    with col3:
        sample_text = spec.get("description", "Texto de Exemplo")
        st.markdown("**Amostra:**")
        st.markdown(
            f'<div style="background-color:{new_bg_color}; color:{new_text_color}; padding: 10px; border-radius: 5px; text-align: center;">{sample_text}</div>',
            unsafe_allow_html=True)

    if st.button("💾 Salvar Alterações no JSON", key=f"save_{selected_id}"):
        target_file, target_dict = get_target_file_and_dict(selected_id)

        if target_file and target_dict:
            target_dict[selected_id]['pattern'] = new_pattern
            if 'style' not in target_dict[selected_id]:
                target_dict[selected_id]['style'] = {}

            target_dict[selected_id]['style']['background_color'] = f"{new_bg_color} !important"
            target_dict[selected_id]['style']['text_color'] = f"{new_text_color} !important"

            if is_determinant_rule and new_score is not None:
                target_dict[selected_id]['score'] = new_score

            if save_rules_to_json(target_file, target_dict):
                st.success(f"Regra salva em `{target_file.name}`!")
                sjur_rules.load_all_rules(force_reload=True)
        else:
            st.error("Não foi possível determinar o arquivo de origem.")

# --- Área de Teste ---
st.divider()
input_text = st.text_area("Texto para Análise:", height=150,
                          placeholder="Cole aqui o texto ou HTML a ser testado...",
                          key="main_input_text")

col_btn1, col_btn2 = st.columns(2)
run_single_test = col_btn1.button("⚡ Aplicar Regra Editada", use_container_width=True)
run_full_pipeline = col_btn2.button("🚀 Simular Pipeline Completo", type="primary", use_container_width=True)

# --- Inicialização do Estado dos Resultados ---
if 'single_test_result' not in st.session_state:
    st.session_state.single_test_result = None
if 'full_pipeline_result' not in st.session_state:
    st.session_state.full_pipeline_result = None

# --- Lógica de Processamento ---
# Adicione esta função auxiliar
def debug_style_info(style_data, new_bg_color, new_text_color):
    """Debug para mostrar informações de estilo"""
    st.write("🔍 Debug de Estilos:")
    st.write(f"BG original: {style_data.get('background_color')}")
    st.write(f"BG novo: {new_bg_color}")
    st.write(f"Texto original: {style_data.get('text_color')}")
    st.write(f"Texto novo: {new_text_color}")
    st.write(f"Classe: {style_data.get('class_name')}")


if run_single_test:
    st.session_state.full_pipeline_result = None
    if not input_text:
        st.warning("Por favor, insira um texto para análise.")
    else:
        try:
            pattern_to_test = new_pattern
            # ✅ USA A CLASSE CSS ORIGINAL da regra
            css_class = style_data.get("class_name", "temp-highlight")
            pattern = re.compile(pattern_to_test, re.DOTALL | re.IGNORECASE)
            matches = pattern.findall(input_text)
            rule_score = (len(matches) * new_score) if is_determinant_rule and new_score is not None else 0

            highlighted_text = apply_manual_highlight(input_text, pattern, css_class)

            # ✅ CORREÇÃO: Usa o estilo ORIGINAL do JSON SEM MODIFICAÇÕES
            temp_style_data = spec.get("style", {}).copy()

            css = generate_css_from_style_data(temp_style_data)
            output_html = f"<style>{css}</style><pre style='white-space: pre-wrap; word-wrap: break-word;'>{highlighted_text}</pre>"

            st.session_state.single_test_result = {
                "matches": len(matches),
                "rule_score": rule_score,
                "html": output_html,
                "is_determinant": is_determinant_rule
            }

        except Exception as e:
            st.session_state.single_test_result = {"error": str(e)}

        # Debug opcional
        if st.session_state.get('debug_mode', False):
            st.write("🔍 Debug - Teste Individual:")
            st.write(f"Padrão: {new_pattern}")
            st.write(f"Matches: {len(matches)}")
            st.write(f"Classe CSS: {css_class}")
            st.write(f"Estilo aplicado: {temp_style_data}")

# pages/rule_studio.py (CORREÇÃO - Linhas 280-290)

if run_full_pipeline:
    st.session_state.single_test_result = None
    if not input_text:
        st.warning("Por favor, insira um texto para análise.")
    else:
        from app.styles.highlighter import highlight_html

        # Usa texto puro para análise (preserva performance)
        text_plain = BeautifulSoup(input_text, "lxml").get_text()

        passes_mandatory = sjur_rules.check_mandatory_rules(text_plain)
        score_data = sjur_rules.calculate_score(text_plain)
        context_data = sjur_rules.extract_context_data(text_plain)

        final_html = highlight_html(input_text)

        st.session_state.full_pipeline_result = {
            "passes_mandatory": passes_mandatory,
            "score": score_data.get('score', 0.0),
            "metadata": context_data.get("metadata", {}),
            "html": final_html
        }

        # ✅ DEBUG DETALHADO para regras de contexto
        if st.session_state.get('debug_mode', False):
            st.write("🔍 Debug - Regras de Contexto:")
            for rule_id, rule_spec in sjur_rules.context_rules.items():
                compiled = rule_spec.get("_compiled_regex") is not None
                enabled = rule_spec.get("enabled", False)
                rule_type = rule_spec.get("type", "unknown")
                has_style = "style" in rule_spec and "class_name" in rule_spec.get("style", {})

                st.write(
                    f"- {rule_id}: type={rule_type}, enabled={enabled}, compiled={compiled}, has_style={has_style}")

                # Testa cada regra individualmente
                if compiled and enabled and rule_spec.get("type") == "highlight":
                    matches = rule_spec["_compiled_regex"].findall(text_plain)
                    st.write(f"  → Matches: {len(matches)}")

# --- Área de Exibição de Resultados ---
if st.session_state.single_test_result:
    result = st.session_state.single_test_result
    st.subheader("Resultados da Análise Isolada")

    if "error" in result:
        st.error(f"**Erro ao aplicar a regra:** {result['error']}")
    else:
        res_col1, res_col2 = st.columns(2)
        res_col1.metric("Ocorrências Encontradas", result["matches"])

        if result["is_determinant"]:
            res_col2.metric("Score Gerado por esta Regra", f"{result['rule_score']:.2f}")

        html_with_style = f"""
        <div style="height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; border-radius: 5px;">
            {result["html"]}
        </div>
        """
        st.html(html_with_style)

if st.session_state.full_pipeline_result:
    result = st.session_state.full_pipeline_result
    st.subheader("Resultados da Simulação do Pipeline Completo")

    res_col1, res_col2 = st.columns(2)
    with res_col1:
        if result["passes_mandatory"]:
            st.success("✅ **Regras Mandatórias:** Satisfeitas.")
        else:
            st.error("❌ **Regras Mandatórias:** Falhou. O score seria zerado.")

    res_col2.metric("Score Determinante Total", f"{result['score']:.2f}")

    with st.expander("Metadados Extraídos"):
        st.json(result["metadata"])

    html_with_style = f"""
    <div style="height: 400px; overflow-y: auto; border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px;
                background-color: #fafafa; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.4;">
        {result["html"]}
    </div>
    """
    st.html(html_with_style)