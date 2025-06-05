# Etapa base (usando slim-buster para compatibilidade)
FROM python:3.11-slim-buster

# Variáveis de ambiente padrão
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*


# Instala ferramentas de rede + ODBC Driver
RUN apt-get update && \
    apt-get install -y curl gnupg2 apt-transport-https software-properties-common \
                       unixodbc-dev iputils-ping telnet && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia apenas os requirements para cache mais eficiente
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

RUN apt-get update && apt-get install -y iputils-ping telnet

# Copia o restante da aplicação
COPY . .

# Cria usuário e ajusta permissões
RUN useradd -r -s /bin/false appuser && \
    chown -R appuser:appuser /app

ENV HOME=/app

USER appuser

# Exposição de portas para API e Streamlit
EXPOSE 8000 8501

# Define argumento para build e transforma em variável de ambiente
# ARG MODE=des
ARG MODE=prod
ENV MODE=${MODE}

# Comando condicional: executa Uvicorn + Streamlit, com ou sem TLS
CMD ["sh", "-c", "\
uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-access-log & \
if [ \"$MODE\" = \"prod\" ]; then \
  streamlit run analise_dados_sjur.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.enableCORS=false \
    --server.sslCertFile=/etc/ssl/certs/server.crt \
    --server.sslKeyFile=/etc/ssl/certs/server.key; \
else \
  streamlit run analise_dados_sjur.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true; \
fi"]
