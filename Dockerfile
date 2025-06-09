# Etapa base
FROM python:3.11-slim

# Define variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho no container
WORKDIR /app

# Copia todos os arquivos (exceto os listados em .dockerignore)
COPY . /app

# Copia explicitamente o banco de dados (redundante, mas seguro)
COPY data/sjur_recortes.db /app/data/sjur_recortes.db

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expondo a porta usada pelo Streamlit
EXPOSE 8501

# Define modo padrão (prod) e sobrescrevível
ARG MODE=prod
# ARG MODE=des
ENV MODE=${MODE}

# Entrypoint condicional: usa TLS em prod
CMD ["sh", "-c", "if [ \"$MODE\" = \"prod\" ]; then \
  streamlit run menu_sjur_streamlit.py --server.address=0.0.0.0 \
           --server.port=8501 \
           --server.enableCORS=false \
           --server.sslCertFile=/etc/ssl/certs/server.crt \
           --server.sslKeyFile=/etc/ssl/certs/server.key; \
  else \
  streamlit run menu_sjur_streamlit.py --server.address=0.0.0.0 --server.port=8501; \
  fi"]
