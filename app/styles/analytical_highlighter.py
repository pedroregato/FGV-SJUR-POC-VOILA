# app/styles/analytical_highlighter.py

import regex as re
from bs4 import BeautifulSoup
from app.rules.archival_rules import sjur_rules

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
    bg_color = style_data.get("background_color", "")
    if bg_color:
        if "!important" in bg_color:
            bg_color = bg_color.replace("!important", "").strip()
        css_props.append(f"background-color: {bg_color} !important;")

    text_color = style_data.get("text_color", "")
    if text_color:
        if "!important" in text_color:
            text_color = text_color.replace("!important", "").strip()
        css_props.append(f"color: {text_color} !important;")

    if "font_weight" in style_data:
        css_props.append(f"font-weight: {style_data['font_weight']} !important;")
    if "border" in style_data:
        border_value = style_data["border"]
        if "!important" in border_value:
            border_value = border_value.replace("!important", "").strip()
        css_props.append(f"border: {border_value} !important;")

    css_props.append("padding: 1px 3px !important;")
    css_props.append("border-radius: 3px !important;")
    css_props.append("display: inline !important;")

    return f"mark.{class_name} {{ {' '.join(css_props)} }}"

def highlight_html_analytical(html_content: str) -> str:
    """
    Aplica destaque analítico completo (estilo rule_studio) ao HTML.
    """
    if not html_content:
        return ""

    # Garante que as regras estão carregadas
    sjur_rules.load_all_rules()

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
                css_styles.append(generate_css_from_style_data(rule_spec.get("style", {})))
                working_html = apply_manual_highlight(working_html, rule_spec["_compiled_regex"], css_class)
            except Exception as e:
                print(f"Erro ao aplicar regra {rule_id}: {e}")
                continue

    # Remove estilos duplicados
    css_styles = list(dict.fromkeys(css_styles))

    # Combina todos os estilos CSS
    full_css = css_reset + "<style>" + "\n".join(css_styles) + "</style>"

    return full_css + working_html