
# 🛠️ Instruções de Build - Projeto SJUR (API e Frontend)

Repositório Git: [`https://src.tic.fgv.br/scm/solcorp/sjur-recortes.git`](https://src.tic.fgv.br/scm/solcorp/sjur-recortes.git)

---

## ⚙️ Estrutura do Projeto

```plaintext
sjur-recortes/
├── api/            # Camada backend - API FastAPI
├── app/            # Código compartilhado (módulos comuns)
├── frontend/       # Camada frontend - Streamlit e notebooks
├── .env            # Variáveis globais (opcional)
```

---

## 🔁 Ambientes

| Camada   | Tipo           | URL / Local |
|----------|----------------|-------------|
| **API**       | Dev (online)   | https://des-sjur-recortesapi.fgv.br |
| **Frontend**  | Dev (online)   | https://des-sjur-recortes.fgv.br    |
| **Frontend**  | CI/CD Bamboo   | https://ci.tic.fgv.br/browse/SERDON |
| **API**       | CI/CD (a definir) | Aguardando integração pela equipe de arquitetura |

---

## 🧪 Ambiente Local - Build Manual com Docker

### 📦 API (`/api`)

#### Pré-requisitos:
- Docker instalado
- `.env` presente em `api/.env` com `DEEPSEEK_API_KEY` e demais variáveis

#### Build (a partir da raiz do projeto):
```bash
docker build -f api/Dockerfile -t sjur-api .
```

#### Execução local:
```bash
docker run -d -p 8000:8000 --name sjur-api --env-file api/.env sjur-api
```

#### Acesso:
- Swagger: http://localhost:8000/docs
- Health:  http://localhost:8000/health

---

### 🖥️ Frontend (`/frontend`)

#### Pré-requisitos:
- Docker instalado
- `app/` com módulos comuns presentes
- `frontend/.env` se necessário

#### Build:
```bash
docker build -f frontend/Dockerfile -t sjur-frontend .
```

#### Execução:
```bash
docker run -d -p 8501:8501 --name sjur-frontend sjur-frontend
```

#### Acesso:
- http://localhost:8501

---

## 🌐 Ambientes Corporativos

### ✅ Frontend

- 🔗 Ambiente disponível: [`https://des-sjur-recortes.fgv.br`](https://des-sjur-recortes.fgv.br)
- 🛠️ CI/CD via Bamboo: [`https://ci.tic.fgv.br/browse/SERDON`](https://ci.tic.fgv.br/browse/SERDON)
- O Bamboo executa o `Dockerfile` diretamente, sem uso de `docker-compose`.

### ✅ API

- 🔗 Ambiente de desenvolvimento ativo: [`https://des-sjur-recortesapi.fgv.br`](https://des-sjur-recortesapi.fgv.br)
- 🛠️ Build corporativo: **em definição pela equipe de arquitetura**
  - Quando definido, será necessário alinhar se o build usará `docker build` ou `docker-compose`.
  - Sugerido: uso de `--env-file` para controle de variáveis sensíveis (como `DEEPSEEK_API_KEY`)

---

## 📝 Observações

- Os arquivos `docker-compose.yml` estão disponíveis **apenas para uso local** e não são utilizados no Bamboo.
- Certifique-se de que o diretório `app/` está sempre incluído no contexto do build da API e do frontend.
- O Dockerfile da API já inclui suporte ao driver `ODBC` e conexão com SQL Server.

---

## ✅ Checklist de Build Local

| Etapa | Comando |
|-------|---------|
| Build API | `docker build -f api/Dockerfile -t sjur-api .` |
| Run API | `docker run -d -p 8000:8000 --env-file api/.env --name sjur-api sjur-api` |
| Build Frontend | `docker build -f frontend/Dockerfile -t sjur-frontend .` |
| Run Frontend | `docker run -d -p 8501:8501 --name sjur-frontend sjur-frontend` |

---

---

## 🔄 Recomendação Futura: Uso de `docker-compose`

Embora o projeto atualmente use `Dockerfile` diretamente para builds e execuções, recomenda-se considerar a adoção de `docker-compose` para os seguintes benefícios:

### ✅ Vantagens do `docker-compose`:

- **Orquestração simplificada**: sobe API e Frontend com um único comando (`docker-compose up`)
- **Gerenciamento de variáveis por serviço**: usando `env_file` ou `environment` por camada
- **Facilidade de integração com bancos, Redis, filas, etc.**
- **Menos repetição de comandos em ambientes de dev**
- **Simulação de produção em localhost** com múltiplos containers

### 🛠️ Sugestão de estrutura futura:

```yaml
version: "3.9"
services:
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - api/.env

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "8501:8501"
    env_file:
      - frontend/.env
```

### 🚀 Com isso, seria possível iniciar tudo com:
```bash
docker-compose up --build
```

Essa abordagem se alinha a práticas modernas de DevOps e facilita integração futura com pipelines de CI/CD mais robustos [[1]](https://docs.docker.com/compose/), [[2]](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-docker-images), [[3]](https://www.redhat.com/en/topics/devops/what-is-ci-cd).

---
