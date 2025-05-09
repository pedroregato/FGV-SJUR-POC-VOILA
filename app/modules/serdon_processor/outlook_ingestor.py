import win32com.client
from datetime import datetime
from typing import List, Optional


class OutlookIngestor:
    def __init__(self, conta: str = "SJUR Coleta Serdon"):
        self.conta = conta

    def obter_emails(
        self,
        remetente_alvo: Optional[str] = None,
        assunto_contem: Optional[str] = None,
        data_minima: Optional[datetime] = None
    ) -> List:
        print(f"Conectando ao Outlook na conta: {self.conta}")
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        try:
            account_folder = outlook.Folders[self.conta]
            inbox = account_folder.Folders["Inbox"]
            print(f"Conta '{self.conta}' encontrada com sucesso.")
        except Exception as e:
            print(f"Erro ao acessar a conta '{self.conta}': {e}")
            raise

        messages = inbox.Items
        messages.Sort("[ReceivedTime]", True)
        print(f"Total de e-mails encontrados: {len(messages)}")

        filtrados = []
        for message in messages:
            try:
                if remetente_alvo and remetente_alvo.lower() not in str(message.SenderEmailAddress).lower():
                    continue
                if assunto_contem and assunto_contem.lower() not in str(message.Subject).lower():
                    continue
                if data_minima and message.ReceivedTime < data_minima:
                    continue
                filtrados.append(message)
            except Exception as e:
                print(f"⚠️ Erro ao processar mensagem: {e}")
                continue

        print(f"Total de e-mails após filtro: {len(filtrados)}")
        return filtrados
