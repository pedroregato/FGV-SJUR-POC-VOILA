# Etapa base
FROM python:3.11-slim

# Variáveis de ambiente padrão
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Diretório de trabalho no container
WORKDIR /app

# Copia todo o conteúdo da pasta api/ (contexto local) para /app no container
COPY . /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Define modo padrão (sobrescrevível via build arg)
ARG MODE=prod
ENV MODE=${MODE}

# Corrigido: main.py está diretamente em /app
CMD ["sh", "-c", "if [ \"$MODE\" = \"prod\" ]; then \
  uvicorn main:app --host 0.0.0.0 --port 8000 --no-access-log; \
else \
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload; \
fi"]
