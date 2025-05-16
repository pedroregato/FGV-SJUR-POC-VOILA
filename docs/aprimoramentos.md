
# Aprimoramentos Sugeridos - Projeto POC SJUR

## Introdução

Este documento registra as ideias de evolução e melhorias para a POC SJUR – Análise de Citações Judiciais. As sugestões visam tornar o sistema ainda mais robusto, organizado e pronto para operação em ambiente de produção.

---

## 🔐 1. Registro de Histórico de Execuções

- Implementar salva de histórico em um arquivo `.csv`.
- Dados a serem armazenados:
  - Timestamp da execução
  - Texto de entrada
  - Modelo utilizado (Regex, DeepSeek, GPT-3.5)
  - Classificação retornada
  - Avaliação (Sim/Não) e Observação
- Benefício: permite auditoria e análise estatística de performance.

---

## 📦 2. Exportação do Projeto para `.py`

- Gerar uma versão do notebook como script `.py`, organizando por seções:
  - Inicialização e imports
  - Definição de widgets
  - Lógicas de processamento
  - Montagem do layout
- Benefício: prepara o projeto para uso autônomo com `Voilà` ou integração com outros sistemas.

---

## 🚀 3. Implantação como Microserviço Web

- Utilizar FastAPI ou Flask para criar endpoints:
  - `/classify` para classificar documentos
  - `/history` para consultar registros
- Benefício: torna a solução acessível via APIs REST, podendo ser consumida por outros sistemas.

---

## 👤 4. Melhorias de Interface

- Exibir confirmações elegantes usando widgets de alerta.
- Destacar visualmente as respostas (citação/intimação/fora de contexto).
- Melhorar responsividade da interface para melhor uso no `Voilà`.

---

## 📝 5. Gerenciamento de Modelos e Chaves Dinâmico

- Permitir que o usuário selecione o modelo a ser usado no momento da classificação.
- Permitir atualização dinâmica de chaves de API.

---

## 🌐 6. Publicação em Ambiente Cloud (Futuro)

- Hospedar a solução em servidor cloud seguro.
- Opções: AWS, Azure, GCP, ou ambiente interno da FGV.
- Benefício: acesso seguro e controlado para diversas áreas usuárias.

---

## 📅 7. Roadmap Futuro

- Implementar dashboard de relatórios.
- Adicionar suporte para novos LLMs nacionais ou locais.
- Criar painel de análise de performance dos classificadores.

---

## Encerramento

Estas ideias fornecem um caminho claro para evoluir a POC de uma ferramenta de experimentação para um produto de alta qualidade, pronto para uso institucional.

**Próximos passos sugeridos:** priorizar o registro de histórico e a exportação do projeto para `.py`, que abrirão o caminho para as demais evoluções.
