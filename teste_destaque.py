# teste_destaque.py — versão corrigida (proximidade prioritária ok)
# Correções:
# 1) make_gap() com chaves duplicadas em f-string -> gera {0,n} corretamente
# 2) ARQUIV aceita hífen e clítico "-se" (arquivem-se / arquive-se)
# 3) Todas as builders de proximidade atualizadas

import re
import json
import copy
from bs4 import BeautifulSoup
import streamlit as st

# ======================================================================
# 0. HELPERS DE REGEX
# ======================================================================
def make_gap(n: int) -> str:
    """
    Retorna um trecho regex que aceita até n 'tokens' entre termos, tolerando:
    - palavras (\w) e hífens/en-dash
    - separadores: espaço, vírgula, ponto e vírgula, travessão
    Ex.: ...{{0,3}} vira {0,3} na string final.
    """
    return rf"(?:[\w\-]+(?:\s+|,\s*|;\s*|–\s*)){{0,{n}}}"  # chaves duplicadas na f-string

# token ARQUIV: permite hífen normal, en-dash (U+2013) e non‑breaking hyphen (U+2011),
# além do clítico opcional "-se" antes do espaço seguinte.
ARQUIV_WORD = r"arquiv[\w\-\u2013\u2011]*"
ARQUIV = rf"{ARQUIV_WORD}(?:-se)?"

def build_baixa_arquiv_prox(n: int) -> str:
    GAP = make_gap(n)
    return rf"\b(?:(?:d[eê][-\s]se\s+)?baixa\s+{GAP}{ARQUIV}|{ARQUIV}\s+{GAP}baixa)\b"

def build_julgado_baixa_arquiv(n: int) -> str:
    GAP = make_gap(n)
    return rf"\bjulgado\s*,?\s+{GAP}baixa\s+{GAP}{ARQUIV}\b"

def build_extinto_arquiv_prox(n: int) -> str:
    GAP = make_gap(n)
    return rf"\bextinto\s+{GAP}{ARQUIV}\b"

def build_homolog_arquiv_prox(n: int) -> str:
    GAP = make_gap(n)
    return rf"\bhomolog\w*\s+{GAP}{ARQUIV}\b"

def build_sentenca_arquiv_prox(n: int) -> str:
    GAP = make_gap(n)
    return rf"\bsentença\s+{GAP}{ARQUIV}\b"

def build_transito_arquiv_prox(n: int) -> str:
    GAP = make_gap(n)
    return rf"\btransit\w*\s+em\s+julgado\s+{GAP}{ARQUIV}\b"

# Mapa de builders por id de regra
PROX_BUILDERS = {
    "baixa_arquiv_prox": build_baixa_arquiv_prox,
    "julgado_baixa_arquiv": build_julgado_baixa_arquiv,
    "extinto_arquiv_prox": build_extinto_arquiv_prox,
    "homolog_arquiv_prox": build_homolog_arquiv_prox,
    "sentenca_arquiv_prox": build_sentenca_arquiv_prox,
    "transito_arquiv_prox": build_transito_arquiv_prox,
}

# ======================================================================
# 1. REGEX PADRÕES (EDITÁVEIS)
# ======================================================================
DEFAULT_CNJ_PATTERN = r"\b\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}\b"
CNJ_FLEX_PATTERN = r"\b\d{7}-\d{2}[.\u00A0]\d{4}[.\u00A0]\d[.\u00A0]\d{2}[.\u00A0]\d{4}\b"

# Básicos (prioridade 2)
DEFAULT_BASIC_PATTERNS = {
    "arq_direto": {
        "description": "Comando Direto de Arquivamento (sem 'baixa')",
        "pattern": r"\b(arquivem?-se|arquive-se)\b",
        "enabled": True
    },
    "baixa_distribuicao": {
        "description": "Baixa na Distribuição",
        "pattern": r"\b(?:baixa\s+na\s+distribu[ií]ção|dando[-\s]se\s+baixa\s+na\s+distribu[ií]ção)\b",
        "enabled": True
    },
    "transito_julgado": {
        "description": "Trânsito em Julgado",
        "pattern": r"\b(?:tr[âa]nsito\s+em\s+julgado|transitad[oa]\s+em\s+julgado)\b",
        "enabled": True
    },
    "extincao_processo": {
        "description": "Extinção do Processo",
        "pattern": r"\b(?:julgo\s+extinto|declaro\s+extinto|processo\s+extinto)\b",
        "enabled": True
    },
    "homologacao": {
        "description": "Homologação",
        "pattern": r"\b(?:homologo|homologa[-\s]se|fica\s+homologado)\b",
        "enabled": True
    },
    "procedencia_improcedencia": {
        "description": "Procedência ou Improcedência",
        "pattern": r"\b(?:julgo\s+(?:im)?procedentes?|(?:im)?procedentes?\s+o\s+pedido|denego\s+a\s+seguran[çc]a)\b",
        "enabled": True
    },
    "desistencia": {
        "description": "Desistência",
        "pattern": r"\b(?:homologo\s+(?:o\s+)?pedido\s+de\s+desist[êe]ncia|desist[êe]ncia\s+homologada)\b",
        "enabled": True
    },
    "acordo_homologado": {
        "description": "Acordo Homologado",
        "pattern": r"\b(?:acordo\s+homologado|homologo\s+o\s+acordo|transa[çc][ãa]o\s+homologada)\b",
        "enabled": True
    }
}

# Proximidade (prioridade 1)
DEFAULT_PROXIMITY_PATTERNS = {
    "baixa_arquiv_prox": {
        "description": "Proximidade: Baixa ↔ Arquiv*",
        "pattern": build_baixa_arquiv_prox(3),
        "enabled": True,
        "max_distance": 3
    },
    "julgado_baixa_arquiv": {
        "description": "Proximidade: Julgado + Baixa + Arquiv*",
        "pattern": build_julgado_baixa_arquiv(5),
        "enabled": True,
        "max_distance": 5
    },
    "extinto_arquiv_prox": {
        "description": "Proximidade: Extinto + Arquiv*",
        "pattern": build_extinto_arquiv_prox(5),
        "enabled": True,
        "max_distance": 5
    },
    "homolog_arquiv_prox": {
        "description": "Proximidade: Homolog* + Arquiv*",
        "pattern": build_homolog_arquiv_prox(5),
        "enabled": True,
        "max_distance": 5
    },
    "sentenca_arquiv_prox": {
        "description": "Proximidade: Sentença + Arquiv*",
        "pattern": build_sentenca_arquiv_prox(10),
        "enabled": True,
        "max_distance": 10
    },
    "transito_arquiv_prox": {
        "description": "Proximidade: Trânsito em Julgado + Arquiv*",
        "pattern": build_transito_arquiv_prox(5),
        "enabled": True,
        "max_distance": 5
    }
}

# ======================================================================
# 2. FUNÇÃO DE DESTAQUE
# ======================================================================
def highlight_html_with_custom_regex(html_content: str, cnj_pattern: str, basic_patterns: dict,
                                     proximity_patterns: dict, use_cnj: bool = True) -> str:
    """
    Destaca termos específicos no HTML. Prioridade:
      1) Proximidade (verde), 2) Básicos (amarelo), 3) CNJ (azul).
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    style = """
    <style>
      body { background-color: #ffffff !important; color: #333 !important; }
      mark.sjur-hit { background: #ffeb3b !important; padding: 0 2px !important; border-radius: 3px !important; border: 1px solid #f5d742 !important; }
      mark.sjur-cnj { background: #e3f2fd !important; padding: 0 2px !important; border-radius: 3px !important; border: 1px solid #90caf9 !important; }
      mark.sjur-proximity {
          background: #b9f6ca !important;      /* verde mais forte */
          padding: 0 2px !important;
          border-radius: 3px !important;
          border: 1px solid #2e7d32 !important; /* contraste */
          box-shadow: 0 0 0 2px rgba(46,125,50,.15) inset; /* “realce” extra */
        }
    </style>
    """
    if soup.head:
        soup.head.insert(0, BeautifulSoup(style, "html.parser"))
    else:
        soup.insert(0, BeautifulSoup(style, "html.parser"))

    # 1) Proximidade
    for rule_id, rule_data in proximity_patterns.items():
        if rule_data.get("enabled", True) and rule_data.get("pattern", "").strip():
            try:
                regex = re.compile(rule_data["pattern"], re.IGNORECASE)
                for text_node in soup.find_all(string=True):
                    if text_node.parent.name in ["style", "script", "head", "title", "mark"]:
                        continue
                    new_html = regex.sub(r'<mark class="sjur-proximity">\g<0></mark>', str(text_node))
                    if new_html != str(text_node):
                        text_node.replace_with(BeautifulSoup(new_html, "html.parser"))
            except re.error as e:
                st.error(f"Erro no regex de proximidade '{rule_id}': {e}")

    # 2) Básicos
    for rule_id, rule_data in basic_patterns.items():
        if rule_data.get("enabled", True) and rule_data.get("pattern", "").strip():
            try:
                regex = re.compile(rule_data["pattern"], re.IGNORECASE)
                for text_node in soup.find_all(string=True):
                    if text_node.parent.name in ["style", "script", "head", "title", "mark"]:
                        continue
                    new_html = regex.sub(r'<mark class="sjur-hit">\g<0></mark>', str(text_node))
                    if new_html != str(text_node):
                        text_node.replace_with(BeautifulSoup(new_html, "html.parser"))
            except re.error as e:
                st.error(f"Erro no regex básico '{rule_id}': {e}")

    # 3) CNJ
    if use_cnj and cnj_pattern.strip():
        try:
            cnj_regex = re.compile(cnj_pattern, re.IGNORECASE)
            for text_node in soup.find_all(string=True):
                if text_node.parent.name in ["style", "script", "head", "title", "mark"]:
                    continue
                new_html = cnj_regex.sub(r'<mark class="sjur-cnj">\g<0></mark>', str(text_node))
                if new_html != str(text_node):
                    text_node.replace_with(BeautifulSoup(new_html, "html.parser"))
        except re.error as e:
            st.error(f"Erro no regex CNJ: {e}")

    return str(soup)

# ======================================================================
# 3. TESTES DOS REGEX
# ======================================================================
def test_custom_regex_patterns(text: str, cnj_pattern: str, basic_patterns: dict, proximity_patterns: dict) -> dict:
    results = {}

    # CNJ
    if cnj_pattern.strip():
        try:
            cnj_matches = re.findall(cnj_pattern, text, re.IGNORECASE)
            results["cnj"] = {"pattern": cnj_pattern, "matches": cnj_matches, "count": len(cnj_matches), "type": "cnj"}
        except re.error as e:
            results["cnj"] = {"pattern": cnj_pattern, "matches": [], "count": 0, "error": str(e), "type": "cnj"}

    # Básicos
    for rule_id, rule_data in basic_patterns.items():
        if rule_data.get("enabled", True) and rule_data.get("pattern", "").strip():
            try:
                matches = re.findall(rule_data["pattern"], text, re.IGNORECASE)
                results[rule_id] = {
                    "description": rule_data["description"],
                    "pattern": rule_data["pattern"],
                    "matches": matches,
                    "count": len(matches),
                    "type": "basic",
                }
            except re.error as e:
                results[rule_id] = {
                    "description": rule_data["description"],
                    "pattern": rule_data["pattern"],
                    "matches": [],
                    "count": 0,
                    "error": str(e),
                    "type": "basic",
                }

    # Proximidade
    for rule_id, rule_data in proximity_patterns.items():
        if rule_data.get("enabled", True) and rule_data.get("pattern", "").strip():
            try:
                matches = re.findall(rule_data["pattern"], text, re.IGNORECASE)
                results[rule_id] = {
                    "description": rule_data["description"],
                    "pattern": rule_data["pattern"],
                    "matches": matches,
                    "count": len(matches),
                    "type": "proximity",
                    "max_distance": rule_data.get("max_distance", "N/A"),
                }
            except re.error as e:
                results[rule_id] = {
                    "description": rule_data["description"],
                    "pattern": rule_data["pattern"],
                    "matches": [],
                    "count": 0,
                    "error": str(e),
                    "type": "proximity",
                    "max_distance": rule_data.get("max_distance", "N/A"),
                }

    return results

# ======================================================================
# 4. EXEMPLOS
# ======================================================================
EXEMPLOS = {
    "Exemplo 1 - Proximidade Baixa+Arquiv": "Transitada em julgado, arquivem-se os autos com baixa na distribuição. |comunicacao_id: 348894399|",
    "Exemplo 2 - Homologação Completa": "<td bgcolor=\"#FDEBEA\">Publicacao Processo: 0910389-11.2023.8.19.0001 Orgao: 1º Juizado ... LUCIANA MOCCO Juiz Titular |comunicacao_id: 270461796|</td>",
    "Exemplo 3 - Extinção com Proximidade": "<td bgcolor=\"#FDEBEA\">Publicacao Processo: 0042896-14.2025.8.25.0001 ... JULGO EXTINTO ... após o trânsito em julgado, dê-se baixa e arquive-se. |comunicacao_id: 348894399|</td>",
}

# ======================================================================
# 5. UI STREAMLIT
# ======================================================================
st.set_page_config(page_title="Teste Regex Editável - SJUR", layout="wide")
st.title("🔧 Teste de Regex Editável com Proximidade - Sistema SJUR")
st.markdown("**Ferramenta para experimentar e ajustar regex patterns em tempo real**")

# 6) Estado
if "cnj_pattern" not in st.session_state:
    st.session_state.cnj_pattern = DEFAULT_CNJ_PATTERN

if "basic_patterns" not in st.session_state:
    st.session_state.basic_patterns = copy.deepcopy(DEFAULT_BASIC_PATTERNS)

if "proximity_patterns" not in st.session_state:
    st.session_state.proximity_patterns = copy.deepcopy(DEFAULT_PROXIMITY_PATTERNS)

# 7) Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")

    st.subheader("📋 Exemplos")
    exemplo_selecionado = st.selectbox(
        "Escolha um exemplo:",
        ["Personalizado"] + list(EXEMPLOS.keys()),
        index=0
    )
    if exemplo_selecionado != "Personalizado":
        if st.button("🔄 Carregar Exemplo"):
            st.session_state.html_input = EXEMPLOS[exemplo_selecionado]
            st.rerun()

    st.divider()
    st.subheader("🎯 Configurações Gerais")
    use_cnj = st.checkbox("Destacar CNJs", value=True)
    altura_visualizacao = st.slider("Altura da visualização (px)", 300, 800, 500)
    mostrar_regex_details = st.checkbox("Mostrar detalhes dos regex", value=True)
    mostrar_codigo_resultado = st.checkbox("Mostrar código HTML resultante", value=False)

    st.divider()
    st.subheader("🔄 Reset Patterns")
    if st.button("🔄 Restaurar Patterns Padrão"):
        st.session_state.cnj_pattern = DEFAULT_CNJ_PATTERN
        st.session_state.basic_patterns = copy.deepcopy(DEFAULT_BASIC_PATTERNS)
        st.session_state.proximity_patterns = copy.deepcopy(DEFAULT_PROXIMITY_PATTERNS)
        st.rerun()

# 8) Entrada
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📥 HTML de entrada")
    html_input = st.text_area(
        "Cole o HTML aqui:",
        value=st.session_state.get("html_input", ""),
        height=200,
        key="html_input",
        help="Cole o HTML completo da publicação que você quer testar"
    )

with col2:
    st.subheader("🎨 Legenda de Cores e Prioridades")
    st.markdown("""
    1. 🟢 **Verde:** Patterns de proximidade
    2. 🟡 **Amarelo:** Patterns básicos
    3. 🔵 **Azul:** Números CNJ
    """)

# 9) Editores
st.divider()
st.subheader("🔧 Regex Patterns Editáveis")
tab_proximity, tab_basic, tab_cnj = st.tabs(["🔗 Patterns de Proximidade (Prioridade 1)", "🎯 Patterns Básicos (Prioridade 2)", "🔢 CNJ Pattern (Prioridade 3)"])

with tab_proximity:
    st.markdown("**Patterns de proximidade (editáveis e reconstruídos pela distância):**")
    st.info("💡 A cada ajuste de 'Distância máx.' o pattern é recalculado automaticamente.")

    for rule_id in list(st.session_state.proximity_patterns.keys()):
        rule_data = st.session_state.proximity_patterns[rule_id]
        with st.expander(f"🔗 {rule_data['description']}", expanded=False):
            col_enable, col_desc, col_dist = st.columns([1, 2, 1])

            with col_enable:
                enabled = st.checkbox("Ativo", value=rule_data.get("enabled", True), key=f"prox_enabled_{rule_id}")
                st.session_state.proximity_patterns[rule_id]["enabled"] = enabled

            with col_desc:
                description = st.text_input("Descrição:", value=rule_data["description"], key=f"prox_desc_{rule_id}")
                st.session_state.proximity_patterns[rule_id]["description"] = description

            with col_dist:
                max_distance = st.number_input(
                    "Distância máx:",
                    min_value=1, max_value=20,
                    value=int(rule_data.get("max_distance", 3)),
                    key=f"prox_dist_{rule_id}",
                    help="Máximo de palavras entre os termos"
                )
                st.session_state.proximity_patterns[rule_id]["max_distance"] = int(max_distance)

            if rule_id in PROX_BUILDERS:
                new_pattern = PROX_BUILDERS[rule_id](int(max_distance))
                st.session_state.proximity_patterns[rule_id]["pattern"] = new_pattern

            pattern = st.text_area(
                "Pattern (pode editar manualmente se quiser sobrescrever):",
                value=st.session_state.proximity_patterns[rule_id]["pattern"],
                height=80,
                key=f"prox_pattern_{rule_id}",
                help="Regex para proximidade"
            )
            st.session_state.proximity_patterns[rule_id]["pattern"] = pattern

with tab_basic:
    st.markdown("**Patterns básicos (editáveis):**")
    for rule_id in list(st.session_state.basic_patterns.keys()):
        rule_data = st.session_state.basic_patterns[rule_id]
        with st.expander(f"🎯 {rule_data['description']}", expanded=False):
            col_enable, col_desc = st.columns([1, 3])

            with col_enable:
                enabled = st.checkbox("Ativo", value=rule_data.get("enabled", True), key=f"basic_enabled_{rule_id}")
                st.session_state.basic_patterns[rule_id]["enabled"] = enabled

            with col_desc:
                description = st.text_input("Descrição:", value=rule_data["description"], key=f"basic_desc_{rule_id}")
                st.session_state.basic_patterns[rule_id]["description"] = description

            pattern = st.text_area(
                "Pattern:",
                value=st.session_state.basic_patterns[rule_id]["pattern"],
                height=80,
                key=f"basic_pattern_{rule_id}",
                help="Regex para este tipo de hit"
            )
            st.session_state.basic_patterns[rule_id]["pattern"] = pattern

with tab_cnj:
    st.markdown("**Regex para identificar números CNJ:**")
    col_cnj1, col_cnj2 = st.columns([1, 1])
    with col_cnj1:
        cnj_mode = st.radio("Modo CNJ", ["Padrão", "Tolerante (NBSP)"], horizontal=True)
    with col_cnj2:
        st.caption("O modo Tolerante aceita NBSP entre blocos numéricos.")

    if cnj_mode == "Padrão":
        default_candidate = DEFAULT_CNJ_PATTERN
    else:
        default_candidate = CNJ_FLEX_PATTERN

    current = st.session_state.cnj_pattern
    if current in (DEFAULT_CNJ_PATTERN, CNJ_FLEX_PATTERN):
        st.session_state.cnj_pattern = default_candidate

    cnj_pattern = st.text_area(
        "Pattern CNJ (pode editar manualmente):",
        value=st.session_state.cnj_pattern,
        height=68,
        key="cnj_pattern_input",
        help="Regex para capturar números de processo CNJ"
    )
    if cnj_pattern != st.session_state.cnj_pattern:
        st.session_state.cnj_pattern = cnj_pattern

# 10) Rodar
st.divider()
col_btn = st.columns([2, 1, 2])
with col_btn[1]:
    aplicar_regex = st.button("🔍 **APLICAR REGEX PATTERNS**", type="primary", use_container_width=True)

if aplicar_regex and st.session_state.get("html_input", "").strip():
    html_input_val = st.session_state["html_input"]

    texto_limpo = BeautifulSoup(html_input_val, "html.parser").get_text(" ")

    test_results = test_custom_regex_patterns(
        texto_limpo,
        st.session_state.cnj_pattern,
        st.session_state.basic_patterns,
        st.session_state.proximity_patterns
    )

    html_resultado = highlight_html_with_custom_regex(
        html_input_val,
        st.session_state.cnj_pattern,
        st.session_state.basic_patterns,
        st.session_state.proximity_patterns,
        use_cnj=use_cnj
    )

    st.divider()
    if mostrar_regex_details:
        st.subheader("📊 Resultados dos Regex Tests")
        col_met1, col_met2, col_met3, col_met4 = st.columns(4)

        total_matches = sum(result["count"] for result in test_results.values() if "count" in result)
        basic_matches = sum(result["count"] for result in test_results.values() if result.get("type") == "basic" and "count" in result)
        proximity_matches = sum(result["count"] for result in test_results.values() if result.get("type") == "proximity" and "count" in result)
        cnj_matches = sum(result["count"] for result in test_results.values() if result.get("type") == "cnj" and "count" in result)

        with col_met1:
            st.metric("🎯 Total de Matches", total_matches)
        with col_met2:
            st.metric("🟡 Matches Básicos", basic_matches)
        with col_met3:
            st.metric("🟢 Matches Proximidade", proximity_matches)
        with col_met4:
            st.metric("🔵 Matches CNJ", cnj_matches)

        col_basic_detail, col_prox_detail = st.columns(2)
        with col_basic_detail:
            st.markdown("**🟡 Patterns Básicos:**")
            for rule_id, result in test_results.items():
                if result.get("type") == "basic":
                    if result.get("count", 0) > 0:
                        with st.expander(f"✅ {result.get('description', rule_id)} - {result['count']} match(es)"):
                            st.write("**Matches encontrados:**")
                            for match in result["matches"]:
                                st.write(f"• `{match}`")
                            st.code(result["pattern"], language="regex")
                    elif "error" in result:
                        with st.expander(f"❌ {result.get('description', rule_id)} - ERRO"):
                            st.error(f"Erro no regex: {result['error']}")
                            st.code(result["pattern"], language="regex")

        with col_prox_detail:
            st.markdown("**🟢 Patterns de Proximidade:**")
            for rule_id, result in test_results.items():
                if result.get("type") == "proximity":
                    if result.get("count", 0) > 0:
                        with st.expander(f"✅ {result.get('description', rule_id)} - {result['count']} match(es)"):
                            st.write("**Matches encontrados:**")
                            for match in result["matches"]:
                                st.write(f"• `{match}`")
                            st.write(f"**Distância máxima:** {result.get('max_distance', 'N/A')} palavras")
                            st.code(result["pattern"], language="regex")
                    elif "error" in result:
                        with st.expander(f"❌ {result.get('description', rule_id)} - ERRO"):
                            st.error(f"Erro no regex: {result['error']}")
                            st.code(result["pattern"], language="regex")

        if "cnj" in test_results:
            cnj_result = test_results["cnj"]
            if cnj_result.get("count", 0) > 0:
                with st.expander(f"🔵 CNJs Encontrados - {cnj_result['count']} match(es)"):
                    st.write("**CNJs encontrados:**")
                    for match in cnj_result["matches"]:
                        st.write(f"• `{match}`")
                    st.code(cnj_result["pattern"], language="regex")

    st.subheader("🎨 Resultado com Destaque")
    st.components.v1.html(html_resultado, height=altura_visualizacao, scrolling=True)

    if mostrar_codigo_resultado:
        st.subheader("💻 Código HTML Resultante")
        st.code(html_resultado, language="html")

    st.divider()
    st.subheader("🔍 Comparação Lado a Lado")
    col_antes, col_depois = st.columns(2)
    with col_antes:
        st.markdown("**📄 ANTES (Original)**")
        st.components.v1.html(f"<style>body{{background:#fff;}}</style>{st.session_state['html_input']}", height=300, scrolling=True)
    with col_depois:
        st.markdown("**✨ DEPOIS (Com Destaques)**")
        st.components.v1.html(html_resultado, height=300, scrolling=True)

elif not st.session_state.get("html_input", "").strip():
    st.info("👆 Cole um HTML na área acima e clique em 'APLICAR REGEX PATTERNS' para testar.")

# 11) Ajuda
st.divider()
with st.expander("📖 Como usar esta ferramenta avançada"):
    st.markdown("""
    ### 🎯 Objetivo
    Editar e experimentar **regex patterns** em tempo real, incluindo **regras de proximidade**.

    ### 🔧 Funcionalidades
    - **Regex editáveis**
    - **Patterns de proximidade** com distância configurável e reconstrução automática
    - **Três tipos de destaque**: Proximidade (verde), Básicos (amarelo), CNJ (azul)
    - **Resultados detalhados** por regra

    ### 💡 Dicas para proximidade
    - `(?:\\w+\\s+){0,N}` funciona, mas **gaps tolerantes** capturam melhor: vírgulas, hífens, etc.
    - Ajuste a **Distância máx.** conforme o tipo de regra.
    """)

st.markdown("---")
st.markdown("🔧 **Ferramenta de Teste Regex Editável - Projeto SJUR/FGV** | Versão com Proximidade e Edição em Tempo Real")
