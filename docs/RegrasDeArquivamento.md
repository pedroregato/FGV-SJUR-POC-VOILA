# Documentação das Regras Heurísticas para Detecção de Arquivamento

**Projeto:** FGV – SJUR – Coleta e Tratamento de Informações Jurídicas  
**Documento:** `RegrasDeArquivamento.md`  
**Versão das Regras:** 1.4.0  
**Propósito:** Detalhar a metodologia, a estrutura e os critérios utilizados pelo classificador heurístico para identificar indícios de arquivamento de processos em publicações jurídicas.

---

## 1. Visão Geral e Metodologia

O classificador heurístico opera sobre o texto extraído das publicações jurídicas para calcular um **escore de arquivamento (`score`)**. Este escore é gerado através de um sistema de **regras ponderadas**, onde diferentes termos e contextos recebem pesos positivos ou negativos.

O processo segue três etapas principais:

1.  **Normalização do Texto:** O texto original é padronizado (minúsculas, remoção de acentos) para garantir a consistência da análise.
2.  **Análise por Padrões (Regex):** O sistema varre o texto em busca de padrões textuais (expressões regulares) definidos no arquivo `archival_heuristic_rules.json`. Cada padrão encontrado contribui com seu peso para o escore total.
3.  **Classificação por Limiares:** O escore numérico final é traduzido em uma classificação categórica (ex: "Arquivamento forte"), facilitando a interpretação pelo usuário.

Esta abordagem é transparente, auditável e permite que as regras de negócio sejam refinadas de forma centralizada, sem a necessidade de alterar o código-fonte da aplicação.

---

## 2. Estrutura do Arquivo de Regras (`archival_heuristic_rules.json`)

O arquivo de regras é o "cérebro" do classificador. Ele é dividido em seções lógicas, cada uma com um propósito específico.

-   **`sentinel_rules`**: Previne falsos positivos ao substituir termos ambíguos (ex: "arquivo") por marcadores antes da análise.
-   **`patterns`**: O coração do sistema, contendo as categorias de regras e seus respectivos pesos.
-   **`context_rules`**: Aplica lógica contextual, como aumentar o escore se dois termos importantes aparecerem próximos.
-   **`thresholds`**: Define os pontos de corte para traduzir o escore numérico em um nível de confiança.

---

## 3. Detalhamento das Categorias de Padrões

As regras são organizadas em categorias semânticas para refletir a natureza e a força de cada indício.

### 3.1. Categoria: `nucleo`

**Função:** Contém os sinais mais fortes e diretos de arquivamento, baixa ou extinção. A presença de um termo desta categoria é um indicador de alta confiança.

| Regra (Descrição) | Peso | Exemplo de Expressão Capturada |
| :------------------ | :--- | :------------------------------ |
| **Comando de Arquivamento** | `1.00` | `arquive-se`, `arquivem-se` |
| **Arquivamento Definitivo** | `1.00` | `arquivamento definitivo`, `arquivado definitivamente` |
| **Baixa com Contexto de Arquivamento** | `0.90` | `baixa e posterior arquivamento` |
| **Baixa Definitiva** | `0.80` | `baixa definitiva` |
| **Comando de Extinção** | `0.75` | `extinto o processo`, `extinção do feito` |
| **Arquivamento (Genérico)** | `0.70` | `determino o arquivamento` |
| **Baixa na Distribuição** | `0.60` | `baixa na distribuição` |
| **Arquivamento Provisório** | `0.50` | `arquivamento provisório` |

### 3.2. Categoria: `adicional`

**Função:** Contém eventos processuais que, embora não sejam o ato de arquivamento em si, são fortes indicadores de que o processo está em sua fase final.

| Regra (Descrição) | Peso | Exemplo de Expressão Capturada |
| :------------------ | :--- | :------------------------------ |
| **Trânsito em Julgado** | `0.65` | `transitada em julgado`, `transitado o feito em julgado` |
| **Desistência da Ação** | `0.50` | `homologo a desistência` |
| **Decisão de Mérito (Julgamento)** | `0.45` | `julgo improcedente o pedido`, `julgar procedente a ação` |
| **Decisão em Mandado de Segurança** | `0.45` | `concedo a segurança`, `denegar a segurança` |
| **Revelia** | `0.35` | `decreto a revelia`, `não apresentou contestação` |

### 3.3. Categoria: `reforco`

**Função:** Contém termos que indicam o contexto de uma decisão final. Sozinhos, têm baixo impacto, mas aumentam a confiança quando combinados com regras das categorias `nucleo` ou `adicional`.

| Regra (Descrição) | Peso | Exemplo de Expressão Capturada |
| :------------------ | :--- | :------------------------------ |
| **Termos de Fecho/Dispositivo** | `0.20` | `sentença`, `dispositivo`, `isto posto`, `ante o exposto` |

### 3.4. Categoria: `negacao`

**Função:** Contém termos que indicam o oposto de um arquivamento. A presença de um destes termos aplica uma penalidade severa ao escore, ajudando a evitar falsos positivos.

| Regra (Descrição) | Peso | Exemplo de Expressão Capturada |
| :------------------ | :---- | :------------------------------ |
| **Negação ou Desarquivamento** | `-1.00` | `desarquive-se`, `não é caso de arquivamento` |

---

## 4. Regras de Contexto e Classificação Final

### 4.1. Boost de Proximidade

Para aumentar a precisão, uma pontuação bônus (`boost`) é aplicada se certos termos aparecerem próximos no texto.

-   **Condição:** A expressão "trânsito em julgado" (e suas variações) aparece a até 300 caracteres de distância do comando "arquive-se" (ou "arquivem-se").
-   **Efeito:** Adiciona `+0.20` ao escore final.
-   **Justificativa:** Esta combinação representa o fluxo processual mais clássico e confiável para o arquivamento.

### 4.2. Limiares de Classificação (`thresholds`)

Após o cálculo final do escore, o sistema o converte em um nível de confiança legível:

| Nível de Confiança | Condição de Escore | Descrição |
| :----------------- | :----------------- | :---------- |
| **Arquivamento forte** | `score ≥ 0.90` | A publicação contém indícios explícitos e de alta confiança de que o processo foi encerrado. |
| **Arquivamento provável** | `0.60 ≤ score < 0.90` | A publicação contém múltiplos indícios consistentes, mas sem um comando direto e inequívoco. |
| **Não identificado** | `score < 0.60` | A publicação não apresenta indícios suficientes para uma classificação positiva. |

