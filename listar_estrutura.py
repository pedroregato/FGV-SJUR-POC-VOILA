import os

def listar_estrutura(diretorio_raiz=".", prefixo=""):
    for item in sorted(os.listdir(diretorio_raiz)):
        caminho_completo = os.path.join(diretorio_raiz, item)
        if item in [".venv", "notebook_backup", "notebooks", ".git", "outputs", "emails_html", "emails_json", ".idea", ".pytest_cashe", "requirements",
                    "__pycache__", "tests", "__pycache__", "ggml", "examples", "llama.cpp", "v"]:
            continue  # Ignora a pasta de ambiente virtual
        print(prefixo + "|-- " + item)
        if os.path.isdir(caminho_completo):
            listar_estrutura(caminho_completo, prefixo + "|   ")

# Executar no diretório raiz do projeto
if __name__ == "__main__":
    print("📁 Estrutura do projeto:\n")
    listar_estrutura(".")
