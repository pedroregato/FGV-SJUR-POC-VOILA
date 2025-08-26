import requests
import pandas as pd

# ===== CONFIGURAÇÕES =====
LOGIN_URL = "http://desenv.infogerpro.com.br/api/login"
CONSULTA_URL_BASE = "http://desenv.infogerpro.com.br/api/apiGerpro/getDadosProcessos"
#LOGIN_URL = "https://infogerpro.com.br/api/login"
#CONSULTA_URL_BASE = "https://infogerpro.com.br/api/apiGerpro/getDadosProcessos"
EMAIL = "sjur@fgv.br"
PASSWORD = "gerpro10"

def login_gerpro(email: str, password: str) -> str:
    print("🔐 Realizando login na API do GERPRO...")

    payload = {'email': email, 'password': password}
    headers = {'Accept': 'application/json'}

    response = requests.post(LOGIN_URL, headers=headers, data=payload)

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        if token:
            print("✅ Login realizado com sucesso.")
            return token
        else:
            print("❌ Token não encontrado na resposta.")
            print("Resposta completa:", data)
    else:
        print(f"❌ Erro no login ({response.status_code})")
        print("Resposta:", response.text)

    raise SystemExit("🚫 Não foi possível autenticar na API do GERPRO.")

def consultar_processos(token: str, data_minima: str):
    print(f"📄 Consultando processos a partir da data {data_minima}...")

    url = f"{CONSULTA_URL_BASE}/{data_minima}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        processos = response.json()

        if not processos:
            print("⚠️ Nenhum processo retornado pela API.")
            return

        print(f"📦 Total de processos retornados: {len(processos)}")

        # Exibe tabela formatada
        df = pd.DataFrame(processos)

        colunas_interesse = [
            'processo', 'numJustica', 'dtDistribuicao', 'dtAtualizacao',
            'comarca', 'classe', 'fase', 'motivo', 'advogado', 'valorCausa'
        ]

        colunas_existentes = [col for col in colunas_interesse if col in df.columns]

        print("\n📊 Visualização tabular:")
        print(df[colunas_existentes].to_string(index=False))
    else:
        print(f"❌ Erro na consulta ({response.status_code})")
        print("Resposta:", response.text)

# ===== EXECUÇÃO PRINCIPAL =====
if __name__ == "__main__":
    token = login_gerpro(EMAIL, PASSWORD)
    consultar_processos(token, data_minima="2025-07-14")
