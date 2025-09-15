# app/styles/highlighter.py (VERSÃO CORRIGIDA E ORGANIZADA)

import regex as re
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from app.rules.archival_rules import sjur_rules

# --- Funções Principais ---

def apply_manual_highlight(text: str, pattern: re.Pattern, css_class: str) -> str:
    """Aplica highlighting manual preservando o texto original."""
    last_end = 0
    parts = []

    for match in pattern.finditer(text):
        target_group_index = pattern.groups if pattern.groups > 0 else 0
        try:
            start_highlight, end_highlight = match.start(target_group_index), match.end(target_group_index)
            parts.append(text[last_end:start_highlight])
            parts.append(f'<mark class="{css_class}">{text[start_highlight:end_highlight]}</mark>')
            last_end = end_highlight
        except IndexError:
            # Se não conseguir acessar o grupo, usa a correspondência completa
            start_highlight, end_highlight = match.start(), match.end()
            parts.append(text[last_end:start_highlight])
            parts.append(f'<mark class="{css_class}">{text[start_highlight:end_highlight]}</mark>')
            last_end = end_highlight
            continue

    parts.append(text[last_end:])
    return "".join(parts)

def generate_global_css_reset() -> str:
    """Gera CSS para resetar estilos conflitantes nos elementos mark."""
    return """
    <style>
    mark {
        all: initial !important;
        display: inline !important;
        padding: 1px 3px !important;
        border-radius: 3px !important;
    }
    mark * {
        all: initial !important;
        display: inline !important;
    }
    </style>
    """

def generate_css_from_style_data(style_data: dict) -> str:
    """Gera CSS com !important para forçar sobrescrita de estilos."""
    class_name = style_data.get("class_name")
    if not class_name:
        return ""

    css_props = []

    # Processa background_color corretamente
    bg_color = style_data.get("background_color", "")
    if bg_color:
        if "!important" in bg_color:
            bg_color = bg_color.replace("!important", "").strip()
        css_props.append(f"background-color: {bg_color} !important;")

    # Processa text_color corretamente
    text_color = style_data.get("text_color", "")
    if text_color:
        if "!important" in text_color:
            text_color = text_color.replace("!important", "").strip()
        css_props.append(f"color: {text_color} !important;")

    # Processa outras propriedades
    if "font_weight" in style_data:
        css_props.append(f"font-weight: {style_data['font_weight']} !important;")
    if "border" in style_data:
        border_value = style_data["border"]
        if "!important" in border_value:
            border_value = border_value.replace("!important", "").strip()
        css_props.append(f"border: {border_value} !important;")

    # Propriedades base sempre aplicadas
    css_props.append("padding: 1px 3px !important;")
    css_props.append("border-radius: 3px !important;")
    css_props.append("display: inline !important;")

    return f"mark.{class_name} {{ {' '.join(css_props)} }}"

def get_rule_style(rule_id: str) -> dict:
    """Retorna o estilo de uma regra específica."""
    sjur_rules.load_all_rules()
    all_rules = {**sjur_rules.mandatory_rules, **sjur_rules.determinant_rules, **sjur_rules.context_rules}

    if rule_id in all_rules:
        return all_rules[rule_id].get("style", {})
    return {}

# --- Funções de Highlight com Retorno de Metadados ---

def highlight_html_with_metadata(html_content: str) -> Dict[str, Any]:
    """
    Aplica destaque ao HTML e retorna tanto o HTML processado quanto os metadados encontrados.
    """
    if not html_content:
        return {"html": "", "cnjs": [], "metadata": {}}

    try:
        soup = BeautifulSoup(html_content, 'lxml')
        cnjs_found = []
        metadata = {}

        # Carrega as regras
        sjur_rules.load_all_rules()

        # Extrai texto para análise de regras
        text_for_analysis = soup.get_text(" ", strip=True)

        # 1. Aplica destaque de CNJs e coleta os valores
        cnj_pattern = re.compile(r'\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b')
        text_nodes = soup.find_all(string=True)

        for text_node in text_nodes:
            if text_node.parent and text_node.parent.name not in ['script', 'style']:
                # Destaca CNJs
                matches = cnj_pattern.findall(text_node)
                if matches:
                    cnjs_found.extend(matches)
                    highlighted_text = cnj_pattern.sub(
                        r'<mark class="sjur-cnj">\g<0></mark>',
                        text_node
                    )
                    text_node.replace_with(BeautifulSoup(highlighted_text, 'html.parser'))

        # 2. Aplica outras regras de destaque (FGV, etc.)
        fgv_pattern = re.compile(r'(?i)(fundacao\s+getulio\s+vargas|fgv|carlos\s+ivan\s+simonsen\s+leal)')
        for text_node in soup.find_all(string=True):
            if text_node.parent and text_node.parent.name not in ['script', 'style']:
                if fgv_pattern.search(text_node):
                    highlighted_text = fgv_pattern.sub(
                        r'<mark class="sjur-fgv">\g<0></mark>',
                        text_node
                    )
                    text_node.replace_with(BeautifulSoup(highlighted_text, 'html.parser'))

        # 3. Extrai metadados adicionais usando as regras de contexto
        context_data = sjur_rules.extract_context_data(text_for_analysis)
        metadata.update(context_data.get("metadata", {}))

        # Adiciona CNJs encontrados aos metadados
        if cnjs_found:
            metadata['cnjs'] = list(set(cnjs_found))

        return {
            "html": str(soup),
            "cnjs": list(set(cnjs_found)),
            "metadata": metadata
        }

    except Exception as e:
        print(f"Erro no highlight_html: {e}")
        return {"html": html_content, "cnjs": [], "metadata": {}}

def highlight_html(html_content: str) -> str:
    """
    Aplica destaque às regras encontradas no HTML, PRESERVANDO formatação original.
    (Função original mantida para compatibilidade)
    """
    if not html_content:
        return ""

    # Garante que as regras estão carregadas
    sjur_rules.load_all_rules()

    # Reset global de estilos
    css_reset = generate_global_css_reset()

    working_html = html_content
    css_styles = []

    # Obtém todas as regras
    all_rules = {}
    all_rules.update(sjur_rules.mandatory_rules)
    all_rules.update(sjur_rules.determinant_rules)
    all_rules.update(sjur_rules.context_rules)

    # Aplica todas as regras de highlight
    for rule_id, rule_spec in all_rules.items():
        if (rule_spec.get("enabled", False) and
                rule_spec.get("_compiled_regex") and
                rule_spec.get("type") != "metadata_extractor"):

            try:
                css_class = rule_spec.get("style", {}).get("class_name", f"highlight-{rule_id}")

                # Gera CSS para esta regra
                css_styles.append(generate_css_from_style_data(rule_spec.get("style", {})))

                # Aplica highlighting
                working_html = apply_manual_highlight(working_html, rule_spec["_compiled_regex"], css_class)
            except Exception as e:
                print(f"Erro ao aplicar regra {rule_id}: {e}")
                continue

    # Remove estilos duplicados
    css_styles = list(dict.fromkeys(css_styles))

    # Combina todos os estilos CSS
    full_css = css_reset + "<style>" + "\n".join(css_styles) + "</style>"

    return full_css + working_html

# --- Função de compatibilidade para manter imports existentes ---
def safe_highlight_html(html_content: str) -> str:
    """
    Função de compatibilidade - mesma coisa que highlight_html.
    Mantida para não quebrar imports existentes.
    """
    return highlight_html(html_content)

# --- Teste da função ---
if __name__ == "__main__":
    # Teste rápido
    test_html = "Parte: CARLOS IVAN SIMONSEN LEAL Parte: ESTADO DO AMAZONAS"
    result = highlight_html(test_html)
    print("Resultado do highlight:")
    print(result)

    # Teste com função de metadados
    metadata_result = highlight_html_with_metadata(test_html)
    print("\nResultado com metadados:")
    print(f"HTML: {metadata_result['html'][:100]}...")
    print(f"CNJs: {metadata_result['cnjs']}")
    print(f"Metadata: {metadata_result['metadata']}")