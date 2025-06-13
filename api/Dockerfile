# Etapa base
FROM python:3.11-slim

# Variáveis de ambiente padrão
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/api:/app

# Diretório de trabalho no container
WORKDIR /app

# Copia o conteúdo da pasta api/ para /app
COPY . /app

# Copia o pacote compartilhado (app/)
COPY ../app /app/app

# Instala pacotes necessários e o driver do SQL Server
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Utilitários básicos
    curl gnupg2 wget apt-transport-https \
    build-essential gcc g++ \
    # ODBC
    unixodbc unixodbc-dev \
    # Bibliotecas gráficas (caso necessário por dependências)
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    # Ferramentas de rede para diagnóstico
    iputils-ping telnet && \
    \
    # Instala o repositório do driver Microsoft
    mkdir -p /etc/apt/keyrings && \
    wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    \
    # Instala o driver do SQL Server
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 && \
    \
    # Limpeza para manter a imagem leve
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Instala dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Define modo padrão (sobrescrevível via build arg)
ARG MODE=prod
ENV MODE=${MODE}

# Entrypoint condicional: usa TLS em prod
CMD ["sh", "-c", "if [ \"$MODE\" = \"prod\" ]; then \
  uvicorn api.main:app --host 0.0.0.0 --port 8000 \
         --ssl-keyfile=/etc/ssl/certs/server.key \
         --ssl-certfile=/etc/ssl/certs/server.crt \
         --no-access-log; \
  else \
  uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload; \
  fi"]

