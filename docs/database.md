# 📚 Documentação da Camada de Banco de Dados

Este documento descreve a estrutura e funcionamento da camada de banco de dados do projeto **SJUR - Coleta e Tratamento de Informações Jurídicas**.

## 🗂 Estrutura Geral

A camada de banco está localizada em `app/database/` e é composta por três arquivos principais:

* `db_connection.py`: Gerencia a conexão com o banco de dados SQLite.
* `db_schema.py`: Cria as tabelas necessárias na base.
* `db_operations.py`: Implementa funções de leitura e escrita de dados nas tabelas.

O banco utilizado é o **SQLite**, armazenado em:

```
<raiz do projeto>/data/sjur_recortes.db
```

## 🧱 Estrutura das Tabelas

### 1. `emails`

Armazena os dados gerais de cada e-mail processado.

| Coluna                  | Tipo | Descrição                                 |
| ----------------------- | ---- | ----------------------------------------- |
| `id_email`              | TEXT | Identificador interno (UUID, por exemplo) |
| `message_id`            | TEXT | ID original da mensagem no Outlook        |
| `data_recebimento`      | TEXT | Data/hora de recebimento do e-mail        |
| `assunto`               | TEXT | Assunto do e-mail                         |
| `remetente`             | TEXT | Remetente                                 |
| `escritorio`            | TEXT | Escritório relacionado à mensagem         |
| `codigo`                | TEXT | Código do escritório                      |
| `area`                  | TEXT | Área interna                              |
| `jornal`                | TEXT | Nome do jornal                            |
| `data_disponibilizacao` | TEXT | Data de disponibilização das publicações  |

---

### 2. `recortes`

Armazena cada publicação (recorte) contida nos e-mails.

| Coluna                    | Tipo    | Descrição                                     |
| ------------------------- | ------- | --------------------------------------------- |
| `id_recorte`              | INTEGER | Identificador do recorte (auto incremento)    |
| `id_email`                | TEXT    | FK para tabela `emails`                       |
| `nome_pesquisado`         | TEXT    | Nome pesquisado                               |
| `tribunal`                | TEXT    | Tribunal                                      |
| `secretaria`              | TEXT    | Secretaria                                    |
| `data_publicacao`         | TEXT    | Data da publicação                            |
| `publicacao`              | TEXT    | Texto integral da publicação                  |
| `identificador_documento` | TEXT    | Identificador único da publicação (se houver) |

---

### 3. `metadados_citacoes_fgv`

Metadados extraídos de publicações que envolvem a Fundação Getúlio Vargas como ré.

| Coluna               | Tipo    | Descrição                              |
| -------------------- | ------- | -------------------------------------- |
| `id_metadado`        | INTEGER | ID do registro                         |
| `id_recorte`         | INTEGER | FK para `recortes`                     |
| `numero_processo`    | TEXT    | Número do processo                     |
| `tribunal`           | TEXT    | Tribunal                               |
| `uf`                 | TEXT    | Unidade federativa                     |
| `orgao`              | TEXT    | Órgão                                  |
| `comarca`            | TEXT    | Comarca                                |
| `classe`             | TEXT    | Classe processual                      |
| `unidade_fgv`        | TEXT    | Unidade interna da FGV (se aplicável)  |
| `obrigacoes`         | TEXT    | Termos de obrigação identificados      |
| `conteudo_publicado` | TEXT    | Texto original da publicação           |
| `igpm_count`         | INTEGER | Contador de menções a IGP-M (opcional) |
| `classificacao`      | TEXT    | Classificação (ex: "citação")          |
| `url_email`          | TEXT    | Link direto para o e-mail no Outlook   |
| `data_publicacao`    | TEXT    | Data da publicação                     |

---

### 4. `emails_processados`

Registra os e-mails que já foram totalmente processados, para evitar retrabalho.

| Coluna               | Tipo | Descrição                                |
| -------------------- | ---- | ---------------------------------------- |
| `message_id`         | TEXT | ID original da mensagem no Outlook       |
| `data_processamento` | TEXT | Data/hora em que o processamento ocorreu |

## 🔁 Fluxo de Processamento

1. Ler todos os e-mails disponíveis.
2. Verificar se `message_id` já está em `emails_processados`.
3. Se não estiver:

   * Armazenar o e-mail em `emails`
   * Armazenar os recortes em `recortes`
   * Para cada recorte:

     * Verificar se é uma citação
     * Verificar se há FGV entre os réus
     * Extrair e armazenar metadados em `metadados_citacoes_fgv`
   * Registrar `message_id` em `emails_processados`

## 🧪 Testes e Utilitários

* A função `criar_tabelas()` em `db_schema.py` pode ser chamada para inicializar ou garantir que a base esteja pronta.
* As operações estão centralizadas em `db_operations.py` para facilitar testes e reuso.

---

Este módulo garante persistência e integridade dos dados processados durante a coleta e análise de citações judiciais envolvendo a FGV.
