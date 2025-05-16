from outlook_utils import gerar_link_outlook_desktop
import win32com.client

def extrair_message_id(headers: str) -> str:
    for line in headers.splitlines():
        if line.lower().startswith("message-id:"):
            return line.split(":", 1)[1].strip()
    return ""

def testar_links_outlook(conta="SJUR Coleta Serdon", max_emails=10):
    print(f"📥 Testando geração de links para os primeiros {max_emails} e-mails da conta '{conta}'\n")

    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    account_folder = outlook.Folders[conta]
    inbox = account_folder.Folders["Inbox"]
    messages = inbox.Items
    messages.Sort("[ReceivedTime]", True)

    for i, message in enumerate(messages):
        if i >= max_emails:
            break
        try:
            subject = message.Subject
            entry_id = message.EntryID
            headers = message.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x007D001E")
            message_id = extrair_message_id(headers)

            print(f"--- E-mail {i+1} ---")
            print(f"🧾 Assunto     : {subject}")
            print(f"✉️ Message-ID : {message_id or '❌ Não encontrado'}")
            print(f"📎 EntryID     : {entry_id}")
            print(f"🔗 Link Outlook: {gerar_link_outlook_desktop(entry_id)}\n")

        except Exception as e:
            print(f"⚠️ Erro ao processar e-mail {i+1}: {e}\n")

if __name__ == "__main__":
    testar_links_outlook()
