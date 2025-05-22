# Etapa base
FROM python:3.11-slim

# Define variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Diretório de trabalho no container
WORKDIR /app

# Copia arquivos do projeto (excluindo os ignorados no .dockerignore)
COPY . /app

# Copia arquivos do banco de dados
COPY data/sjur_recortes.db /app/data/sjur_recortes.db

# Instala dependências do sistema (ajuste se necessário)
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# Instala o módulo llama_cpp_python a partir do código-fonte local
# RUN pip install app/llama.cpp

# Expondo a porta usada pelo Streamlit
EXPOSE 8501

# Comando de execução do app
CMD ["streamlit", "run", "analise_dados_sjur.py", "--server.address=0.0.0.0"]
