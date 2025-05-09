# Projeto: SJUR - POC de Análise de Citações Judiciais via Voilà

Esta POC demonstra a detecção de citações judiciais em e-mails recebidos pela FGV, utilizando um ambiente leve e portátil baseado em Jupyter + Voilà, empacotado em Docker.

## 🎯 Objetivo

- Classificar se o texto representa uma citação judicial.
- Extrair metadados principais (como número do processo).
- Permitir que o avaliador registre se concorda ou não com a classificação.
- Salvar as avaliações em uma base local (`avaliacoes/`).

## 📁 Estrutura do Projeto

```
sjur-poc-voila/
│
├── app/
│   ├── seu_notebook.ipynb
│   └── exemplos.csv (opcional)
│
├── avaliacoes/
│   └── (pasta onde os registros de avaliações serão armazenados)
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
```

## 🚀 Como Rodar Localmente

### Pré-requisitos
- Docker instalado na máquina.

### Passos:

1. Clone ou copie este repositório.

2. Na raiz do projeto, abra o terminal e execute:

```bash
docker compose up --build
```

*(ou, se preferir sem docker-compose:)*

```bash
docker build -t sjur-poc-voila .
docker run -p 8866:8866 sjur-poc-voila
```

3. Acesse no navegador:

```
http://localhost:8866
```

A aplicação Voilà abrirá mostrando a interface para inserção de texto, processamento e avaliação.

## 📦 Tecnologias Utilizadas

- Python 3.11
- Jupyter Notebook
- Voilà
- Pandas
- Ipywidgets
- Docker

## ✍️ Observações

- O ambiente é **100% local** e **não requer conexão com a internet** para funcionar após a construção da imagem.
- As avaliações são salvas em formato CSV dentro da pasta `avaliacoes/`.
- O Dockerfile e docker-compose.yml já estão configurados para facilitar a execução.

## 📄 Licença

Este projeto é interno e restrito à FGV para fins de demonstração no Projeto SJUR.
