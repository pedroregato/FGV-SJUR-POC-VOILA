# app/modules/utils/html_highlight.py
## Realce HTML
from __future__ import annotations
import html
import re
from typing import List

def highlight_html(raw_text: str, terms_regex: List[str]) -> str:
    html_safe = html.escape(raw_text)
    def markit(s, pat):
        return re.sub(pat, lambda m: f"<mark class='match'>{m.group(0)}</mark>", s, flags=re.IGNORECASE)
    for pat in terms_regex:
        html_safe = markit(html_safe, pat)
    style = "<style>.match{background:#ffec99;padding:0 .15em;border-radius:.2em}</style>"
    return style + "<pre style='white-space:pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;'>" + html_safe + "</pre>"
