# scripts/collectors/outlook_collector.py

import win32com.client
import pythoncom
import unicodedata
from typing import List


def get_outlook_items(account_name: str, folder_path: str, date_filter: str | None, limit: int) -> List[any]:
    """Conecta-se ao Outlook, busca e retorna uma lista de itens de e-mail."""
    pythoncom.CoInitialize()
    mapi = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    # Encontra a conta
    norm_name = unicodedata.normalize("NFKD", account_name.lower())
    store = next((s for s in mapi.Stores if norm_name in unicodedata.normalize("NFKD", s.DisplayName.lower())), None)
    if not store:
        raise RuntimeError(f"Conta Outlook '{account_name}' não encontrada.")

    # Encontra a pasta
    node = store.GetRootFolder()
    for part in [p for p in folder_path.split("/") if p.strip()]:
        norm_part = unicodedata.normalize("NFKD", part.lower())
        node = next((f for f in node.Folders if unicodedata.normalize("NFKD", f.Name.lower()) == norm_part), None)
        if not node:
            raise RuntimeError(f"Pasta '{part}' não encontrada.")

    items = node.Items
    items.Sort("[ReceivedTime]", True)

    if date_filter:
        items = items.Restrict(date_filter)

    # Coleta os itens até o limite
    collected_items = []
    unlimited = (limit is None) or (limit <= 0)
    item = items.GetFirst()
    while item and (unlimited or len(collected_items) < limit):
        collected_items.append(item)
        item = items.GetNext()

    return collected_items
