import re
from bs4 import BeautifulSoup

# =======================
# Paleta de cores (alto contraste)
# =======================
HIGHLIGHT_STYLES = {
    "prox": "background-color: #28a745; color: white; font-weight: bold;",   # proximidade
    "hit": "background-color: #ffc107; color: black; font-weight: bold;",    # padrões básicos
    "cnj": "background-color: #17a2b8; color: white; font-weight: bold;",    # CNJ
    "fgv": "background-color: #dc3545; color: white; font-weight: bold;",    # FGV como parte
    "fgv-text": "color: #dc3545; font-weight: bold;",                        # FGV menção genérica
    "label": "background-color: #9b59b6; color: white; font-weight: bold;",  # rótulos processuais
}

# =======================
# Padrões regex
# =======================
REGEX_PATTERNS = {
    "cnj": re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"),
    "transito": re.compile(r"transit[oa]?\s+em\s+julgado", re.IGNORECASE),
    "arquivar": re.compile(r"arquiv\w*", re.IGNORECASE),
    "baixa": re.compile(r"baix[ae]\w*", re.IGNORECASE),
    "extincao": re.compile(r"(extinguindo\s+o\s+processo|julgo\s+extinto\s+o\s+processo)", re.IGNORECASE),
    "fgv": re.compile(r"FUNDACAO\s+GETULIO\s+VARGAS", re.IGNORECASE),
    "labels": re.compile(r"\b(PARTE[S]?|AUTOR[AE]?|R[EÉ]U|POLO\s+ATIVO|POLO\s+PASSIVO)\b", re.IGNORECASE),
}

# =======================
# Funções auxiliares
# =======================
def apply_highlight(text: str, pattern: re.Pattern, css_class: str) -> str:
    """Aplica marcação HTML para um padrão regex."""
    def replacer(match):
        return f'<mark class="sjur-{css_class}">{match.group(0)}</mark>'
    return pattern.sub(replacer, text)


def highlight_html(html: str, hits: list[str] = None, cnjs: list[str] = None) -> str:
    """
    Realça padrões no HTML fornecido.
    Ordem de prioridade: proximidade > básicos > labels > FGV parte > FGV genérico > CNJ
    """
    soup = BeautifulSoup(html, "html.parser")

    # força fundo branco
    if soup.body:
        soup.body["style"] = "background-color: white !important; color: black;"

    raw_text = str(soup)

    # --- Proximidade (pré-marca neutra) ---
    raw_text = apply_highlight(raw_text, REGEX_PATTERNS["baixa"], "key")
    raw_text = apply_highlight(raw_text, REGEX_PATTERNS["arquivar"], "key")
    raw_text = apply_highlight(raw_text, REGEX_PATTERNS["transito"], "key")
    raw_text = promote_proximities(raw_text)

    # --- Extinção / básicos ---
    raw_text = apply_highlight(raw_text, REGEX_PATTERNS["extincao"], "hit")

    # --- Labels processuais ---
    raw_text = apply_highlight(raw_text, REGEX_PATTERNS["labels"], "label")

    # --- FGV (parte primeiro, depois genérico) ---
    raw_text = highlight_fgv(raw_text)

    # --- CNJs ---
    if cnjs:
        for cnj in cnjs:
            cnj_esc = re.escape(cnj)
            raw_text = re.sub(cnj_esc, f'<mark class="sjur-cnj">{cnj}</mark>', raw_text)
    raw_text = apply_highlight(raw_text, REGEX_PATTERNS["cnj"], "cnj")

    # Substitui marca neutra por básicos (após proximidade)
    raw_text = raw_text.replace('class="sjur-key"', 'class="sjur-hit"')

    return wrap_with_styles(raw_text)


def promote_proximities(html: str, window: int = 12) -> str:
    """
    Promove pares 'baixa + arquivar' e 'transito + arquivar' dentro da janela de tokens.
    """
    tokens = html.split()
    positions = { "baixa": [], "arquivar": [], "transito": [] }

    for i, tok in enumerate(tokens):
        if 'sjur-key' in tok:
            if "baix" in tok.lower():
                positions["baixa"].append(i)
            if "arquiv" in tok.lower():
                positions["arquivar"].append(i)
            if "transit" in tok.lower():
                positions["transito"].append(i)

    def promote(p1, p2):
        for i in positions[p1]:
            for j in positions[p2]:
                if abs(i - j) <= window:
                    tokens[i] = tokens[i].replace("sjur-key", "sjur-prox")
                    tokens[j] = tokens[j].replace("sjur-key", "sjur-prox")

    promote("baixa", "arquivar")
    promote("transito", "arquivar")

    return " ".join(tokens)


def highlight_fgv(html: str) -> str:
    """Destaca FGV como parte (fundo vermelho) ou menção genérica (texto vermelho)."""
    def replacer(match):
        ctx = match.string[max(0, match.start() - 30):match.end() + 30]
        if re.search(r"(PARTE[S]?|AUTOR[AE]?|R[EÉ]U|POLO\s+ATIVO|POLO\s+PASSIVO)", ctx, re.IGNORECASE):
            return f'<mark class="sjur-fgv">{match.group(0)}</mark>'
        return f'<span class="sjur-fgv-text">{match.group(0)}</span>'

    return REGEX_PATTERNS["fgv"].sub(replacer, html)


def wrap_with_styles(html: str) -> str:
    """Inclui estilos inline para classes CSS."""
    styles = "<style>\n"
    for cls, style in HIGHLIGHT_STYLES.items():
        styles += f".sjur-{cls} {{{style}}}\n"
    styles += "</style>\n"
    return styles + html


def highlight_html_from_csv_data(html: str, hits_csv_string: str, cnjs: list[str] = None) -> str:
    """Wrapper compatível com dados vindos do CSV."""
    hits = [h.strip() for h in hits_csv_string.split(";") if h.strip()]
    return highlight_html(html, hits, cnjs)


def extract_hit_texts_from_csv(hits_csv_string: str) -> list[str]:
    """Extrai hits amigáveis do CSV (string separada por ';')."""
    return [h.strip() for h in hits_csv_string.split(";") if h.strip()]
