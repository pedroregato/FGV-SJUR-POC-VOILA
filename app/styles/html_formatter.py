# app/styles/html_formatter.py

import re

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


def get_styled_html(
        html_content: str,
        hits: list[str] | None = None,
        cnjs: list[str] | None = None,
        indicios: list[str] | None = None
) -> str:
    """
    Aplica múltiplos estilos e destaques a um trecho de código HTML.

    Args:
        html_content: O HTML original a ser processado.
        hits: Lista de termos (regras de arquivamento) para destacar em amarelo.
        cnjs: Lista de todos os números de processo para destacar em azul.
        indicios: Lista de termos de indício para destacar em vermelho.

    Returns:
        O HTML formatado como uma string.
    """
    if not HAS_BS4 or not html_content:
        return html_content or "<p>Conteúdo HTML indisponível.</p>"

    is_full_html = html_content.strip().lower().startswith(('<!doctype', '<html'))
    if not is_full_html:
        html_content = f"<html><head></head><body>{html_content}</body></html>"

    soup = BeautifulSoup(html_content, "html.parser")

    # Estilos CSS completos, baseados no seu anexo.
    style_rules = """
    <style>
      body { background-color: white !important; color: #333 !important; }
      mark.sjur-hit { background: #ffeb3b !important; padding: 0 .2em !important; border-radius: 3px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important; color: #000 !important; font-weight: bold !important; border: 1px solid #ffc107 !important; }
      mark.sjur-cnj { background: #e3f2fd !important; padding: 0 .2em !important; border-radius: 3px !important; border: 1px solid #90caf9 !important; }
      mark.sjur-indicio { background: #ff4444 !important; color: white !important; padding: 0 .2em !important; border-radius: 3px !important; font-weight: bold !important; border: 1px solid #cc0000 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important; }
      mark.sjur-fgv { background: #4caf50 !important; color: white !important; padding: 0 .2em !important; border-radius: 3px !important; font-weight: bold !important; border: 1px solid #388e3c !important; }
      mark.sjur-prazo { background: #1565c0 !important; color: white !important; padding: 0 .2em !important; border-radius: 3px !important; font-weight: bold !important; border: 1px solid #0d47a1 !important; }
    </style>
    """

    head = soup.find('head')
    if head:
        head.insert(0, BeautifulSoup(style_rules, "html.parser"))

    # Compilação de todas as Regex necessárias
    re_hits = re.compile(r'(' + '|'.join(re.escape(term) for term in hits if term) + r')',
                         re.IGNORECASE) if hits else None
    re_cnjs = re.compile(r'(' + '|'.join(re.escape(cnj) for cnj in cnjs if cnj) + r')') if cnjs else None
    re_indicios = re.compile(r'(' + '|'.join(re.escape(ind) for ind in indicios if ind) + r')',
                             re.IGNORECASE) if indicios else None
    re_fgv = re.compile(r'\b(funda[cç][aã]o getulio vargas|fgv)\b', re.IGNORECASE)
    re_prazo = re.compile(r'\b(prazo|termo|dilig[êe]ncia|intima[cç][aã]o|ci[êe]ncia|cita[cç][aã]o)\b', re.IGNORECASE)

    for text_node in soup.body.find_all(string=True):
        if text_node.parent.name in ['style', 'script']:
            continue

        original_text = str(text_node)
        temp_html = original_text

        # Aplica as substituições em uma ordem de prioridade para evitar sobreposição incorreta
        if re_fgv: temp_html = re_fgv.sub(r'<mark class="sjur-fgv">\1</mark>', temp_html)
        if re_prazo: temp_html = re_prazo.sub(r'<mark class="sjur-prazo">\1</mark>', temp_html)
        if re_hits: temp_html = re_hits.sub(r'<mark class="sjur-hit">\1</mark>', temp_html)
        if re_indicios: temp_html = re_indicios.sub(r'<mark class="sjur-indicio">\1</mark>', temp_html)
        if re_cnjs: temp_html = re_cnjs.sub(r'<mark class="sjur-cnj">\1</mark>', temp_html)

        if temp_html != original_text:
            text_node.replace_with(BeautifulSoup(temp_html, "html.parser"))

    if not is_full_html and soup.body:
        return soup.body.decode_contents()

    return str(soup)
