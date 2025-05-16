# Operações - POC SJUR: Análise de Citações Judiciais

Este documento orienta como utilizar corretamente a POC SJUR para análise de citações judiciais em e-mails recebidos.

---

## 📢 Iniciando a POC

1. Execute o notebook `poc_coleta_sjur.ipynb`.
2. Certifique-se de que o arquivo `.env` está presente com as seguintes variáveis:
   - `DEEPSEEK_API_KEY`
   - `OPENAI_API_KEY`
   - `GOOGLE_API_KEY`
3. O ambiente carrega automaticamente todos os classificadores disponíveis.

---

## 💡 Como Executar o Notebook

### Executar no Jupyter Notebook

1. Abra o terminal na pasta do projeto.
2. Execute:
   ```bash
   jupyter notebook poc_coleta_sjur.ipynb
   ```
3. O Jupyter abrirá no navegador. Clique no notebook para iniciar a interação.

### Executar com Voilà

1. Instale o Voilà, se ainda não tiver:
   ```bash
   pip install voila
   ```
2. No terminal, execute:
   ```bash
   voila poc_coleta_sjur.ipynb
   ```
3. O Voilà abrirá automaticamente no navegador, exibindo apenas a interface de usuário (sem código).

---

## 📂 Fluxo de Trabalho

### 1. Inserir o Texto para Análise
- Cole o conteúdo do e-mail no campo "Texto do e-mail a ser analisado".

### 2. Escolher um Classificador
- **Regex**: utiliza expressões regulares.
- **DeepSeek**: modelo LLM DeepSeek.
- **GPT-3.5**: modelo da OpenAI.
- **Gemini**: modelo da Google.

### 3. (Opcional) Buscar Termos no Texto
- Na aba "Busca":
  - Informe termos separados por ponto-e-vírgula `;`
  - Clique em **Buscar** para destacar e contar as ocorrências no texto.

### 4. (Opcional) Testar Expressão Regular
- Na aba "Regex":
  - Digite uma expressão regex.
  - Forneça um texto.
  - Clique em **Testar Regex** para verificar se há correspondências.

### 5. Avaliar a Classificação
- Na aba "Avaliação":
  - Indique se concorda com a classificação.
  - Insira uma observação opcional.
  - Clique em **Registrar Avaliação**.

---

## 🛠️ Edição Dinâmica de Prompt

### 1. Acessar a área "⚙️ Edição e Atualização do Prompt"
- Localizada ao final do notebook.

### 2. Ações disponíveis:
- **Editar o prompt**: Utilize o campo de texto.
- **💾 Salvar Alterações**: Grava o conteúdo no arquivo `prompt_custom.txt`.
- **♻️ Restaurar Padrão**: Restaura o conteúdo original do sistema.
- **🔄 Recarregar Classificadores**: Recarrega as instâncias dos modelos LLM para que utilizem o novo prompt.

> É **obrigatório clicar em 🔄 Recarregar Classificadores** após salvar ou restaurar o prompt.

---

## 📌 Observações

- Priorize sempre textos completos de decisões judiciais.
- Classificadores diferentes podem ser comparados rapidamente.
- O prompt pode ser customizado e ajustado conforme os padrões jurídicos da FGV.

---

## ✅ Requisitos Técnicos

- Python 3.10+
- Pacotes necessários:
  - `ipywidgets`, `voila`, `openai`, `requests`, `google-generativeai`, etc.

---

**Pronto! Agora você pode utilizar a POC de forma segura, organizada e eficiente.**