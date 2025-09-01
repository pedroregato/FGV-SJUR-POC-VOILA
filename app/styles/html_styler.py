# app/styles/html_styler.py

import json
from pathlib import Path

# Constrói os caminhos para os arquivos de estilo de forma robusta
STYLE_DIR = Path(__file__).parent
CSS_FILE = STYLE_DIR / "styler.css"
JS_FILE = STYLE_DIR / "styler.js"


def render_html_with_js_styling(
        html_content: str,
        hits: list[str],
        cnjs: list[str],
        focused_pub_id: str | None
) -> str:
    """
    Renderiza o HTML lendo os arquivos CSS e JS externos e injetando as
    instruções necessárias para a estilização no lado do cliente.
    """
    try:
        # Lê o conteúdo dos arquivos CSS e JS
        css_code = CSS_FILE.read_text(encoding="utf-8")
        js_template = JS_FILE.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        return f"<p><b>Erro de configuração:</b> Arquivo de estilo não encontrado: {e}.</p>"

    # Prepara as instruções para o JavaScript
    instructions = {
        "htmlContent": html_content,  # Passa o HTML como parte das instruções
        "hits": hits,
        "cnjs": cnjs,
        "focusedPubId": focused_pub_id
    }
    js_instructions = json.dumps(instructions)

    # Monta o HTML final
    return f"""
    <html>
        <head>
            <style>{css_code}</style>
        </head>
        <body>
            <div id="sjur-html-container"></div>
            <script>
                {js_template}

                // Chama a função principal do nosso script JS com as instruções do Python
                document.addEventListener('DOMContentLoaded', function() {{
                    const instructions = {js_instructions};
                    applySjurStyling(instructions);
                }});
            </script>
        </body>
    </html>
    """
