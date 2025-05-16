import win32com.client

# Conectar ao Outlook
outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

# Nome da conta e pasta correta
conta_outlook = "SJUR Coleta Serdon"
account_folder = outlook.Folders[conta_outlook]
inbox = account_folder.Folders["Inbox"]  # Acessa a Inbox

# Obter os e-mails
messages = inbox.Items
messages.Sort("[ReceivedTime]", True)  # Ordena do mais recente para o mais antigo

print(f"Total de e-mails encontrados: {messages.Count}")

# Contadores
emails_com_resultado = 0
emails_sem_resultado = 0
emails_sem_termo = []

# Verificar a presença do termo "Resultado da Pesquisa"
for message in messages:
    try:
        body = message.Body.lower()
        if "resultado da pesquisa" in body:
            emails_com_resultado += 1
        else:
            emails_sem_resultado += 1
            emails_sem_termo.append(message.Subject)

    except Exception as e:
        print(f"Erro ao processar e-mail: {e}")

# Exibir estatísticas
print(f"\nE-mails que contêm 'Resultado da Pesquisa': {emails_com_resultado}")
print(f"E-mails que **NÃO** contêm 'Resultado da Pesquisa': {emails_sem_resultado}")

# Listar os e-mails que não possuem o termo
if emails_sem_termo:
    print("\nE-mails sem 'Resultado da Pesquisa':")
    for assunto in emails_sem_termo:
        print(f"- {assunto}")

print("\nVerificação concluída!")
