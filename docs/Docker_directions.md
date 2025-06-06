# 🐳 Docker Directions — Projeto SJUR-RECORTES

Este guia descreve como construir e executar o ambiente Docker do projeto **SJUR-RECORTES**, suportando múltiplos contextos: **desenvolvimento (dev)** e **produção (prod)**.

---

## ✅ Estrutura esperada de arquivos

```
.
├── Dockerfile
├── docker-compose.yml               # Configuração base
├── docker-compose-dev.yml          # Configuração para ambiente local
├── docker-compose-prod.yml         # Configuração para ambiente corporativo
├── .env                            # Variáveis de ambiente locais
├── .env.prod                       # Variáveis para produção (ex: MODE=production)
├── certs/
│   ├── server.crt                  # Certificado SSL (produção)
│   └── server.key
├── nginx/
│   └── nginx.conf                  # Configuração de reverse proxy NGINX
```

---

## ⚙️ Modo de desenvolvimento (local)

### ✅ Comando para subir o container:
```bash
docker-compose -f docker-compose.yml -f docker-compose-dev.yml up --build
```

### 📌 Serviços expostos:
- FastAPI (Uvicorn): http://localhost:8000
- Swagger (API): http://localhost:8000/docs
- Streamlit: http://localhost:8501

### 🧪 Variável usada:
```env
MODE=development
```

---

## 🔐 Modo de produção (com NGINX + TLS)

### ✅ Comando para subir o container:
```bash
docker-compose -f docker-compose.yml -f docker-compose-prod.yml --env-file .env.prod up --build
```

### 📌 Serviços expostos:
- NGINX com TLS: https://des-sjur-recortes.fgv.br
- Swagger (API): https://des-sjur-recortes.fgv.br/api/docs

### 🧪 Variável usada:
```env
MODE=production
```

> Certifique-se de que os certificados `server.crt` e `server.key` estejam válidos e posicionados em `./certs/`.

---

## 🔄 Parar e remover containers e volumes

```bash
docker-compose -f docker-compose.yml -f docker-compose-dev.yml down -v
# ou para produção
docker-compose -f docker-compose.yml -f docker-compose-prod.yml down -v
```

---

## 🩺 Verificar se está tudo rodando

```bash
docker ps
```

Você deve ver:
- `sjur-poc` em execução
- Portas 8000/8501 (dev) ou 443 (prod) expostas
