import os
import re
from typing import Optional


def gerar_html_do_email(email_obj, pasta_html: str) -> Optional[str]:
    """
    Salva o corpo HTML de um e-mail em um arquivo .html.
    Retorna o caminho do arquivo salvo ou None em caso de erro.
    """
    try:
        from datetime import datetime

        data_email = email_obj.ReceivedTime.strftime("%Y-%m-%d_%H%M%S")
        subject = email_obj.Subject or "sem_assunto"
        html_body = getattr(email_obj, "HTMLBody", email_obj.Body)

        nome_arquivo_safe = re.sub(r"[^\w\-]", "_", subject)[:50]
        nome_arquivo_html = f"{data_email}_{nome_arquivo_safe}.html"
        caminho_html = os.path.join(pasta_html, nome_arquivo_html)
        os.makedirs(pasta_html, exist_ok=True)

        with open(caminho_html, "w", encoding="utf-8") as f:
            f.write(html_body)

        return caminho_html
    except Exception as e:
        print(f"Erro ao gerar HTML do e-mail: {e}")
        return None
