# Dockerfile para teste com dados fixos

# Etapa base
FROM python:3.11-slim

# Define variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho no container
WORKDIR /app

# Copia todos os arquivos da aplicação
COPY . /app

# =================================================================================
# ### ALTERAÇÃO PARA TESTE ###
# Copia a pasta 'outputs' para dentro da imagem.
# Isso "congela" os dados para o teste de deploy.
# Certifique-se de que a pasta 'outputs' existe no contexto do build.
# =================================================================================
COPY outputs/ /app/outputs/

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expondo a porta usada pelo Streamlit
EXPOSE 8501

# Define modo padrão (desenvolvimento) e permite que seja sobrescrito
ARG MODE=des
ENV MODE=${MODE}

# Entrypoint condicional: usa TLS em prod
# >>> Garanta que o nome do script está correto aqui <<<
CMD ["sh", "-c", "if [ \"$MODE\" = \"prod\" ]; then \
  streamlit run app_arquivamento_streamlit.py --server.address=0.0.0.0 \
           --server.port=8501 \
           --server.enableCORS=false \
           --server.sslCertFile=/etc/ssl/certs/server.crt \
           --server.sslKeyFile=/etc/ssl/certs/server.key; \
  else \
  streamlit run app_arquivamento_streamlit.py --server.address=0.0.0.0 --server.port=8501; \
  fi"]
