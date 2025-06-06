# Etapa base — compatível com builds Linux
FROM python:3.11-slim

# Variáveis de ambiente padrão
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema + NGINX
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libglib2.0-0 libsm6 libxrender1 libxext6 sqlite3 \
    curl gnupg2 apt-transport-https software-properties-common \
    unixodbc-dev iputils-ping telnet \
    nginx \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o restante da aplicação
COPY . .

# Copia configuração do NGINX (certificados são montados em produção via volume)
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Cria usuário e ajusta permissões
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
ENV HOME=/app
USER appuser

# Expondo portas conforme o ambiente:
# - Apenas 443 em produção (via NGINX)
# - 8000 (FastAPI) e 8501 (Streamlit) em desenvolvimento
EXPOSE 443 8000 8501

# Define o modo (production ou development)
ARG MODE=production
ENV MODE=${MODE}

# Entrypoint condicional:
# - Executa Uvicorn + Streamlit sempre
# - Em produção, inicia o NGINX
# - Em desenvolvimento, mantém os serviços ativos com tail -f
CMD ["sh", "-c", "\
uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-access-log & \
streamlit run analise_dados_sjur.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true & \
if [ \"$MODE\" = \"production\" ]; then \
  nginx -g 'daemon off;'; \
else \
  tail -f /dev/null; \
fi"]
