import win32com.client
from typing import Optional


def buscar_entryid_por_message_id(message_id: str) -> Optional[str]:
    """
    Busca o EntryID de um e-mail no Outlook local com base no Message-ID (cabeçalho MIME).

    Args:
        message_id (str): O Message-ID (ex: <1234@dominio.com>).

    Returns:
        str | None: O EntryID do Outlook, se encontrado.
    """
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox = outlook.GetDefaultFolder(6)  # 6 = Caixa de entrada

    messages = inbox.Items
    messages.Sort("[ReceivedTime]", True)  # Mais recentes primeiro

    for message in messages:
        try:
            headers = message.PropertyAccessor.GetProperty(
                "http://schemas.microsoft.com/mapi/proptag/0x007D001E"
            )
            if message_id.lower() in headers.lower():
                return message.EntryID
        except Exception:
            continue

    return None


def gerar_link_outlook_desktop(entry_id: str) -> str:
    """
    Gera um link de abertura direta no Outlook Desktop usando o EntryID.

    Args:
        entry_id (str): EntryID do e-mail no Outlook.

    Returns:
        str: Link do tipo 'outlook:{entry_id}'
    """
    return f"outlook:{entry_id}"


def gerar_link_outlook_por_message_id(message_id: str) -> Optional[str]:
    """
    Interface completa: busca e-mail e retorna link clicável no Outlook Desktop.

    Args:
        message_id (str): O Message-ID do e-mail.

    Returns:
        str | None: Link 'outlook:{entry_id}', se encontrado.
    """
    entry_id = buscar_entryid_por_message_id(message_id)
    if entry_id:
        return gerar_link_outlook_desktop(entry_id)
    return None
