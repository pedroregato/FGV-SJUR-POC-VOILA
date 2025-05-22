# Etapa base
FROM python:3.11-slim

# Define variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Diretório de trabalho no container
WORKDIR /app

# Copia todos os arquivos (exceto os listados em .dockerignore)
COPY . /app

# Copia explicitamente o banco de dados (pode ser redundante, mas mantido por segurança)
COPY data/sjur_recortes.db /app/data/sjur_recortes.db

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Instalação do llama desabilitada (não usada na POC)
# RUN pip install app/llama.cpp

# Expondo a porta usada pelo Streamlit
EXPOSE 8501

# Define modo padrão (sobrescrevível via build arg)
ARG MODE=prod
ENV MODE=${MODE}

# Comando de execução condicional: com TLS em prod
CMD ["sh", "-c", "if [ \"$MODE\" = \"prod\" ]; then \
  streamlit run analise_dados_sjur.py --server.address=0.0.0.0 \
           --server.port=8501 \
           --server.enableCORS=false \
           --server.sslCertFile=/etc/ssl/certs/server.crt \
           --server.sslKeyFile=/etc/ssl/certs/server.key; \
  else \
  streamlit run analise_dados_sjur.py --server.address=0.0.0.0 --server.port=8501; \
  fi"]
