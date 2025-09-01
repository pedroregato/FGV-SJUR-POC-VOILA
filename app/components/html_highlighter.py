# coding: utf-8
"""
Highlighter de HTML para indícios de arquivamento
- Aceita tanto argumentos POSITIONAL quanto KEYWORD: (html, hits_list, cnj_list)
  ou (html_content=..., hits_to_highlight=..., cnjs_to_highlight=...).
- Recalcula e UNE HITS pelas regras centrais quando o CSV não trouxe (ou trouxe defasado).
- Prioridade visual: 1) Proximidade (verde), 2) CNJ (azul), 3) Básicos (amarelo).
- Fundo branco forçado (neutraliza bgcolor herdado).
"""
import re
from typing import List, Optional
from bs4 import BeautifulSoup

# Regras centralizadas
try:
    from app.rules.archival_rules import archival_rules
    HAS_RULES = True
except Exception:
    HAS_RULES = False
    archival_rules = None

CSS = """
<style>
  body { background-color: #ffffff !important; color: #333 !important; }
  table, tr, td, th { background-color: #ffffff !important; }
  [bgcolor] { background-color: #ffffff !important; }
  mark.sjur-hit { background: #ffeb3b !important; padding: 0.1em 0.2em !important; border-radius: 3px !important; color: #000 !important; font-weight: bold !important; }
  /* Paleta do teste isolado para CNJ */
  mark.sjur-cnj { background: #e3f2fd !important; padding: 0.1em 0.2em !important; border-radius: 3px !important; border: 1px solid #90caf9 !important; }
  mark.sjur-proximity { background: #d8f5dc !important; padding: 0.12em 0.25em !important; border-radius: 4px !important; border: 2px solid #2e7d32 !important; box-shadow: 0 0 0 2px rgba(46,125,50,0.18) inset !important; color: #0a3010 !important; font-weight: 700 !important; }
</style>
"""

def _inject_css(soup: BeautifulSoup) -> None:
    css = BeautifulSoup(CSS, "html.parser")
    if soup.head:
        soup.head.insert(0, css)
    else:
        soup.insert(0, css)

def _iter_text_nodes(soup: BeautifulSoup):
    for node in soup.find_all(string=True):
        parent = node.parent.name if node.parent else ""
        if parent in ("style", "script", "head", "title", "mark"):
            continue
        yield node

def _apply_regex(soup: BeautifulSoup, pattern: re.Pattern, css_class: str) -> None:
    for text_node in list(_iter_text_nodes(soup)):
        original = str(text_node)
        replaced = pattern.sub(fr'<mark class="{css_class}">\g<0></mark>', original)
        if replaced != original:
            text_node.replace_with(BeautifulSoup(replaced, "html.parser"))

def _get_cnj_pattern() -> str:
    if HAS_RULES and archival_rules is not None:
        try:
            if hasattr(archival_rules, "get_cnj_pattern"):
                return archival_rules.get_cnj_pattern()
            if hasattr(archival_rules, "rules") and "cnj" in archival_rules.rules:
                return archival_rules.rules["cnj"].get("pattern", r"\b\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}\b")
        except Exception:
            pass
    return r"\b\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}\b"

def _recalc_hits_from_rules(html: str):
    """Retorna (prox_texts, basic_texts) usando EXACTAMENTE as regras centrais (match_text)."""
    if not (HAS_RULES and archival_rules is not None):
        return [], []
    try:
        text = BeautifulSoup(html, "html.parser").get_text(" ")
        matches = archival_rules.find_matches(text)
        prox = [m.get("match_text") for m in matches if m.get("rule_type") == "proximity" and m.get("match_text")]
        bas  = [m.get("match_text") for m in matches if m.get("rule_type") == "basic" and m.get("match_text")]
        return prox, bas
    except Exception:
        return [], []

def highlight_html(*args,
                   **kwargs) -> str:
    """
    Assinaturas aceitas:
      - highlight_html(html, hits_list=None, cnj_list=None)
      - highlight_html(html_content=..., hits_to_highlight=..., cnjs_to_highlight=...)
    """
    # Compatibilidade com chamadas existentes
    html = None
    hits_list: Optional[List[str]] = None
    cnj_list: Optional[List[str]]  = None

    # 1) Tenta positional
    if len(args) >= 1:
        html = args[0]
    if len(args) >= 2:
        hits_list = args[1]
    if len(args) >= 3:
        cnj_list = args[2]

    # 2) Tenta keywords usadas na app
    html = kwargs.get("html_content", html)
    hits_list = kwargs.get("hits_to_highlight", hits_list)
    cnj_list = kwargs.get("cnjs_to_highlight", cnj_list)

    if not html:
        return ""

    # Normaliza listas
    hits_list = [h for h in (hits_list or []) if isinstance(h, str) and h.strip()]
    cnj_list = [c for c in (cnj_list or []) if isinstance(c, str) and c.strip()]

    soup = BeautifulSoup(html, "html.parser")
    _inject_css(soup)

    # Se não vieram HITS (ou vieram capengas), recalcula pelos regexs centrais e UNE
    recalc_prox, recalc_basic = _recalc_hits_from_rules(html)

    # União preservando ordem:
    #  - Prioridade de aplicação final: PROX → CNJ → BÁSICO
    #  - Aqui apenas mesclamos listas; a priorização acontece na aplicação
    seen = set()
    prox_texts = []
    bas_texts  = []

    # Heurística para classificar os hits vindos do CSV entre prox/básico
    def is_proximity_string(s: str) -> bool:
        s2 = s.lower()
        return ("arquiv" in s2 and "baixa" in s2) or ("julgado" in s2 and "arquiv" in s2)

    for h in (hits_list or []):
        if h in seen: continue
        seen.add(h)
        (prox_texts if is_proximity_string(h) else bas_texts).append(h)

    for h in recalc_prox:
        if h in seen: continue
        seen.add(h)
        prox_texts.append(h)

    for h in recalc_basic:
        if h in seen: continue
        seen.add(h)
        bas_texts.append(h)

    # ===== 1) PROXIMIDADE (verde) =====
    # Termos mais longos primeiro para evitar sobreposição
    prox_texts.sort(key=lambda t: (len(t.split()), len(t)), reverse=True)
    for t in prox_texts:
        try:
            rx = re.compile(re.escape(t), re.IGNORECASE)
            _apply_regex(soup, rx, "sjur-proximity")
        except re.error:
            continue

    # ===== 2) CNJ (azul) =====
    # 2.1) CNJs explícitos
    for c in cnj_list:
        try:
            rx = re.compile(re.escape(c), re.IGNORECASE)
            _apply_regex(soup, rx, "sjur-cnj")
        except re.error:
            continue
    # 2.2) Regex global
    try:
        rx_cnj = re.compile(_get_cnj_pattern(), re.IGNORECASE)
        _apply_regex(soup, rx_cnj, "sjur-cnj")
    except re.error:
        pass

    # ===== 3) BÁSICOS (amarelo) =====
    bas_texts.sort(key=lambda t: (len(t.split()), len(t)), reverse=True)
    for t in bas_texts:
        try:
            rx = re.compile(re.escape(t), re.IGNORECASE)
            _apply_regex(soup, rx, "sjur-hit")
        except re.error:
            continue

    return str(soup)
