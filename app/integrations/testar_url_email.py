import os

# Link gerado pelo EntryID do Outlook
outlook_link = "outlook:0000000051A6618F9402A146AA36444B12802DEC0700788CE02B293FAA428AFEAEB37B50E1E900000000010C0000788CE02B293FAA428AFEAEB37B50E1E900004305C9CE0000"

try:
    print(f"🟢 Tentando abrir link: {outlook_link}")
    os.startfile(outlook_link)
    print("✅ Comando enviado ao sistema. Verifique se o Outlook foi acionado.")
except Exception as e:
    print(f"❌ Erro ao tentar abrir o link no Outlook: {e}")
