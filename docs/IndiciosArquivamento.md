# Indícios de Arquivamento — Pipeline SJUR
**Projeto:** FGV – SJUR – Coleta e Tratamento de Informações Jurídicas  
**Documento:** `IndiciosArquivamento.md`  
**Propósito:** Definir e documentar a estratégia implementada para identificar, em recortes jurídicos, indícios de que um **processo foi arquivado**, produzindo (i) uma **lista** em CSV com metadados e escore de confiança e (ii) uma **aplicação de visualização** do HTML do recorte com realce dos trechos relevantes.

---

## 1) Contexto e Objetivo
- **Cenário**: Recortes jurídicos recebidos por e-mail, contendo múltiplas publicações de Diários de Justiça, nos quais a **FGV** é parte.
- **Objetivo**: Detectar **indícios de arquivamento** (e baixa/encerramento) em cada publicação individual, classificar a força da evidência através de um escore e gerar:
  1. **Um arquivo CSV consolidado** (`arquivamento.csv`) com uma linha por recorte, contendo metadados, escore agregado e listas de processos.
  2. **Uma aplicação interativa (Streamlit)** para auditoria visual, com destaques das expressões que motivaram a classificação.
- **Saídas-alvo**:
  - `received, score, is_arquivamento, hits, subject, processos, indicios, entry_id, html_filename`.

---

## 2) Escopo e Fontes
- **Fonte primária**: Arquivos HTML extraídos de e-mails, contendo uma ou mais publicações judiciais.
- **Idioma**: PT-BR.
- **Pré-requisitos de entrada**: HTML original do recorte.

---

## 3) Estratégia Implementada — Análise Heurística por Publicação
### 3.1. Visão do Pipeline
1. **Coleta**: Um script lê e-mails de uma conta do Outlook, extraindo o corpo HTML de cada um (recorte).
2. **Divisão do Recorte**: O HTML de cada recorte é dividido em "publicações" individuais. A heurística para identificar uma publicação é a busca por tabelas (`<table>`) que contenham o marcador `<strong>Publicação:</strong>`.
3. **Análise por Publicação**: Cada publicação isolada passa pelo seguinte processo:
    a. **Normalização do Texto**: O texto da publicação é extraído e normalizado (lowercase, remoção de acentos).
    b. **Extração de CNJs**: Todos os números de processo no formato CNJ são extraídos da publicação.
    c. **Detecção de Hits e Score**: O texto é varrido em busca de termos definidos em um léxico. A presença de cada termo contribui para um **escore** daquela publicação.
    d. **Identificação de Indícios**: Se a publicação contém termos de arquivamento com peso positivo e seu escore é maior que zero, todos os CNJs encontrados nela são marcados como tendo "indício".
4. **Agregação**: Os resultados de todas as publicações de um recorte são agregados:
    a. O **score final do recorte** é a soma dos scores de cada publicação.
    b. A **lista de `processos`** contém todos os CNJs únicos encontrados em todo o recorte.
    c. A **lista de `indicios`** contém apenas os CNJs que foram marcados com indício.
5. **Geração de Saídas**:
    a. Os dados agregados de cada recorte são salvos em um arquivo `recortes_full.jsonl`.
    b. Um arquivo `arquivamento.csv` é gerado a partir do JSONL para ser usado pela aplicação de visualização.
    c. O HTML original de cada recorte é salvo para referência.

### 3.2. Dicionário de Padrões com Pesos (`LEXICON_ARQ_WEIGHTS`)
O núcleo da detecção é um dicionário Python que mapeia termos-chave para um peso inteiro.
| Termo (normalizado) | Peso |
|---|---|
| arquivamento, arquivado, arquivar | **+3** |
| trânsito em julgado, transito em julgado | **+3** |
| baixa, baixado | **+2** |
| extinção do processo, extinto o processo | **+2** |
| tjulg, preclusão, encerramento, extinção | **+1** |
| desarquivamento | **-2** |

### 3.3. Classificação (`is_arquivamento`)
Um recorte é marcado com a flag `is_arquivamento = 1` se seu **score total agregado for maior ou igual a 3**. Caso contrário, recebe `0`.

### 3.4. Extração de Metadados
- **CNJ**: `\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b`
- **Outros metadados** (Órgão, Data, etc.) são extraídos do e-mail (Assunto, Data de Recebimento) ou podem ser extraídos do HTML da publicação em futuras versões.

### 3.5. Saída Estruturada (linha do CSV)
O `arquivamento.csv` contém as seguintes colunas:
- `received`: Data/hora de recebimento do e-mail.
- `score`: Escore total do recorte.
- `is_arquivamento`: `1` ou `0`.
- `hits`: String com os termos e pesos encontrados (ex: `+3:arquivado,-2:desarquivamento`).
- `subject`: Assunto do e-mail.
- `processos`: Lista de todos os CNJs no recorte, separados por "; ".
- `indicios`: Lista de CNJs com indícios de arquivamento, separados por "; ".
- `entry_id`: Identificador único do e-mail no Outlook.
- `html_filename`: Nome do arquivo HTML salvo.

### 3.6. Aplicação de Visualização (Streamlit)
A aplicação `app_arquivamento_streamlit.py` lê o CSV e apresenta:
- **Tabela de Resultados**: Uma tabela filtrável e ordenável com os dados dos recortes. As colunas `processos` e `indicios` são exibidas em células roláveis para melhor legibilidade.
- **Visualizador de HTML**: Ao clicar em um item, o HTML original é exibido com destaques visuais:
  - 🟡 **Hits de Arquivamento**: Termos do léxico.
  - 🔴 **CNJs com Indício**: Processos da coluna `indicios`.
  - 🔵 **Outros CNJs**: Processos que não estão na coluna `indicios`.
  - 🟢 **FGV**: Menções à "Fundação Getulio Vargas" ou "FGV".
  - 🟦 **Prazos/Intimações**: Termos como "prazo", "intimação", "citação", etc.

### 3.7. Pseudocódigo da Lógica Central
```text
recorte_final = { score: 0, processos: set(), indicios: set(), hits: set() }
html_recorte = ler_html_do_email()
lista_de_publicacoes = dividir_html_em_publicacoes(html_recorte)

for pub_html in lista_de_publicacoes:
    pub_texto = extrair_texto(pub_html)
    cnjs_na_pub = encontrar_cnjs(pub_texto)
    recorte_final.processos.update(cnjs_na_pub)

    score_pub = 0
    hits_na_pub = set()
    tem_indicio_positivo = False

    for termo, peso in LEXICO:
        if termo in pub_texto:
            score_pub += peso
            hits_na_pub.add(termo)
            if peso > 0:
                tem_indicio_positivo = True
    
    if score_pub > 0 and tem_indicio_positivo:
        recorte_final.indicios.update(cnjs_na_pub)
    
    recorte_final.score += score_pub
    recorte_final.hits.update(hits_na_pub)

emitir_csv(recorte_final)

```
---

## 4) Estratégia 2 — LLM via API (Classificador Explicável)
### 4.1. Quando usar
- **Casos limítrofes** (heurística entre 0.60–0.89).  
- **Textos ruidosos** (OCR), variações regionais, terminologia incomum.  
- **Auditoria/explicabilidade**: exigir **rationale** e **trechos citados**.

### 4.2. Rótulos e Política de Corte
- `ARCHIVE_STRONG` (evidência dispositiva explícita).  
- `ARCHIVE_LIKELY` (sinais consistentes porém menos explícitos).  
- `NOT_ARCHIVED` (ausência de sinais ou menções genéricas/indiretas).
- **Gating híbrido**:  
  - Heurística ≥ 0.90 → **aceita** sem LLM.  
  - 0.60–0.89 → **envia ao LLM**.  
  - < 0.60 → **descarta** (ou amostra para QA).

### 4.3. Esquema de Resposta (JSON)
```json
{
  "label": "ARCHIVE_STRONG | ARCHIVE_LIKELY | NOT_ARCHIVED",
  "confidence": 0.0_to_1.0,
  "rationale": "Explicação curta citando trechos.",
  "quotes": [
    {"text": "… arquivem-se …", "start": 1234, "end": 1245},
    {"text": "… trânsito em julgado …", "start": 980, "end": 1005}
  ],
  "extracted": {
    "processo": "…",
    "orgao": "…",
    "data_disponibilizacao": "…",
    "tipo_comunicacao": "…",
    "link_inteiro_teor": "…"
  }
}
```

### 4.4. Template de Prompt (sugestão)
```
Você é um examinador jurídico. Classifique o texto abaixo quanto a indícios de arquivamento do processo.

Regras:
- ARCHIVE_STRONG: há comando claro tipo “arquive-se/arquivem-se”, “baixa na distribuição/definitiva”, “após o trânsito em julgado, arquivem-se”, “extinção do feito” no dispositivo/fecho.
- ARCHIVE_LIKELY: múltiplos sinais consistentes, mas sem comando inequívoco.
- NOT_ARCHIVED: ausência de indícios ou menções genéricas (p.ex., citação jurisprudencial).

Responda em JSON no esquema fornecido. Cite trechos literais (quotes). Seja sucinto.

=== TEXTO ===
{trecho_alvo}
```

**Boas práticas**:  
- **Cortar o texto** ao **DISPOSITIVO/fecho** quando possível → menor custo e maior precisão.  
- **Temperature** baixa (0–0.2), `max_tokens` controlado.  
- **Redações sensíveis**: respeitar LGPD e políticas de segurança (PII).

### 4.5. Observabilidade e Custos
- **Cache** por hash do texto.  
- **Rate limiting** e **retries exponenciais**.  
- Métricas: **hit-ratio do cache**, **tempo médio** por item, **$ por 1k recortes**.

### 4.6. Integração Híbrida (resumo)
1. Executar **Heurística** sobre o lote.  
2. Encaminhar **borderlines** ao **LLM**.  
3. **Fundir** resultados: se LLM divergir, seguir **política** (ex.: priorizar LLM quando confiança ≥ 0.8).  
4. Persistir rationale/quotes para auditoria.

---

## 5) Plano de Testes e Qualidade
1. **Amostragem**: coletar ≥ 150 recortes variados (múltiplos tribunais).  
2. **Rotulagem** por dupla de revisores (consenso).  
3. **Métricas**: Precisão, Recall, F1 por classe; AUC pr/roc (binário forte vs. resto).  
4. **Metas iniciais** (ajustáveis):  
   - Forte: **Precisão ≥ 0.92**, Recall ≥ 0.85  
   - Provável: Precisão ≥ 0.85, Recall ≥ 0.80  
5. **Ajustes**: recalibrar pesos/limiares; ampliar dicionário por tribunal.  
6. **Regressão**: suíte mínima de testes unitários em cada alteração de regras.

---

## 6) Integração no SJUR (sugestão de endpoints)
- `POST /archival/scan` → recebe lote, retorna lista com escore e HTML realçado.  
- `GET /archival/preview/{id}` → serve o HTML do recorte classificado.  
- `GET /archival/export?format=csv|json` → exporta a lista filtrada.  
- **Storage**: manter **versão** do dicionário/thresholds e **artefatos** (HTMLs) para auditoria.  
- **Segurança**: RBAC, logs, mascaramento de PII quando necessário.

---

## 7) Riscos e Mitigações
- **Falsos positivos com “arquivo(s)”** (file) → usar sentinel `ARQFILE`.  
- **Citações jurisprudenciais** sem decisão do caso → exigir **núcleo** + **contexto** (DISPOSITIVO).  
- **Variação regional** de termos → manter **dicionários por tribunal** e **telemetria** de novos padrões.  
- **Ruído de OCR** → normalização agressiva + regras mais tolerantes.  
- **Codificação/acentos** → unificar Unicode NFKD antes de varrer.

---

## 8) Roadmap
- **MVP Heurístico** (versão 1.0): pesos/limiares básicos + logging.  
- **Híbrido com LLM** (versão 1.1): gating 0.60–0.89 + prompt padronizado.  
- **Afinação contínua**: dicionários por tribunal, proximidade semântica leve (word windows).  
- **Dataset rotulado interno** para validação e regressão.  

---

## 9) Ideia de Aplicativo Streamlit (prévia)
**Objetivo**: revisão rápida e elegante dos recortes classificados, com filtros e auditoria visual.

**Páginas sugeridas**:
- **Upload & Scan**: seleção de lote, exibição de progresso e KPIs (processados, fortes, prováveis).  
- **Review**: tabela com filtros (processo, score, tribunal), **preview HTML** com destaques side-by-side.  
- **Detalhes**: “explicabilidade” (matches, spans/quotes do LLM, rationale).  
- **Exportar**: CSV/JSON dos itens selecionados; **ZIP com HTMLs**.  
- **Configurações**: thresholds, toggles (usar LLM em borderline), dicionário por tribunal.  

**UI/UX**:
- Temas claro/escuro; **badges** por nível (forte/provável); **chips** de tribunal/órgão; busca por CNJ.  
- Métricas em cards: precisão de amostra, taxa de arquivamento por tribunal, tempo médio por item.

---

## 10) Apêndice A — Padrões (regex) consolidado
```text
# Núcleo
\b arquiv (e|em) -se \b
\b arquivament \w+ \b
\b baixa (definitiva | na distribuic \w* | com baixa) \b
\b transito em julgado \b
\b extin(g|c) \w* do feito \b | \b extingo o processo \b

# Reforços de contexto
\b sentenc \w* \b | \b dispositivo \b | \b isto posto \b | \b ante o exposto \b | \b publiqu \w* -se \b | \b intimem \w* -se \b

# Moderados (não isolam)
\b improcedent \w* \b | \b procedent \w* \b
\b desist \w* \b
\b deneg \w* a seguranc \w* \b

# Negações
\b n \w* arquivar \b | \b n \w* arquivament \w* \b | \b sem arquivament \w* \b | \b desarquiv \w* \b
```

> **Notas de implementação**: aplicar **normalização** (lowercase + remover acentos + normalizar espaços) **antes** de executar as regex; proteger “arquivo(s)” → `ARQFILE` sentinel.

---

## 11) Exemplos (resumo de classificação esperado)
- **Texto 001 (MA)**: “transito em julgado” + “arquivem-se” no fecho → **Arquivamento forte** (score alto).  
- **Texto 002 (PA)**: “apos o transito em julgado, arquivem-se … com as devidas baixas” → **Arquivamento forte**.  
- **Texto 003 (JF/PE)**: “denegar a segurança” + “arquive-se com baixa na distribuição” → **Arquivamento forte**.

---

### Conclusão
A estratégia **heurística** fornece rapidez, baixo custo e boa **explicabilidade** por regras transparentes; a estratégia com **LLM** acrescenta **robustez** nos casos limítrofes e heterogêneos, mantendo governança via **política híbrida** (gating por escore). Ambas se integram bem ao **SJUR**, com registros de auditoria, relatórios e uma UI amigável em **Streamlit** para revisão.


---

## 12) Léxico (glossário de termos para o público de negócio)

**Amostragem** — seleção de um subconjunto de itens (recortes) para análise e testes, representando o todo com custo menor.  

**Baixa na distribuição** — lançamento administrativo que registra o encerramento/arquivamento do processo no sistema de distribuição. Em muitos diários aparece junto de “arquivem-se”.  

**Boost (reforço de contexto)** — incremento proposital no escore quando uma condição reforçadora ocorre (ex.: o termo aparece no **DISPOSITIVO** da sentença).  

**Cache** — armazenamento temporário de resultados (ex.: resposta de um LLM) para evitar custo e latência em reprocessamentos do mesmo texto.  

**CNJ (número CNJ)** — padrão nacional de numeração de processos: `NNNNNNN-DD.AAAA.J.TR.OOOO`.  

**Confiança (confidence score)** — valor de 0 a 1 (ou 0% a 100%) que expressa quão seguro está um modelo/algoritmo sobre sua classificação.  

**Cutoff / Limiar (threshold)** — ponto de corte do escore usado para decidir a classe final (ex.: ≥ 0,90 = “Arquivamento forte”).  

**Device/Dispositivo (parte dispositiva)** — seção final da decisão judicial, onde o(a) juiz(a) **determina** comandos (“arquivem-se”, “julgo improcedente”, etc.). Costuma ser o sinal mais confiável.  

**Drift (deriva)** — mudança gradual no padrão dos textos (ex.: novos termos usados por um tribunal) que pode reduzir a eficácia das regras se não houver atualização.  

**FGV (Fundação Getulio Vargas)** — parte interessada nos processos monitorados pelo SJUR neste projeto.  

**Falso positivo (FP)** — caso classificado como “arquivado” mas que **não** estava arquivado de fato.  
**Falso negativo (FN)** — caso **arquivado** que o sistema **não** identificou como tal.  

**Gating (política de triagem)** — regra híbrida que decide quando confiar na heurística e quando escalar para um LLM (ex.: somente entre 0,60 e 0,89).  

**Heurística** — abordagem baseada em **regras simples e transparentes** (padrões de texto, pesos, limiares), rápida e barata de executar.  

**HTML com destaque** — a visualização do recorte com trechos relevantes marcados via `<mark>…</mark>` para facilitar a auditoria humana.  

**Janelas de proximidade (window)** — distância máxima entre dois termos para considerá-los relacionados (ex.: “trânsito em julgado” até **300 caracteres** antes de “arquive-se”).  

**LLM (Large Language Model)** — modelo de linguagem de grande porte (ex.: GPT) utilizado via API para interpretar textos e dar classificações/explicações.  

**Logging & Auditoria** — registros persistentes (escore, padrões acionados, versão das regras) para rastreabilidade, compliance e reprocessamento.  

**Métricas** — indicadores de qualidade do classificador:  
- **Precisão (Precision)** = VP / (VP + FP) → “dos que marquei como arquivados, quantos realmente eram?”  
- **Recall (Cobertura/Sensibilidade)** = VP / (VP + FN) → “dos arquivados reais, quantos eu encontrei?”  
- **F1-score** = 2 × (Precisão × Recall) / (Precisão + Recall) → equilíbrio entre precisão e recall.  
- **AUC (PR/ROC)** — área sob a curva; mede desempenho global em diferentes limiares.  

**Núcleo (no dicionário de padrões)** — conjunto de **sinais fortes e diretos** de arquivamento (ex.: “arquivem-se”, “baixa na distribuição”, “extinção do feito”).  

**Normalização (de texto)** — padronizações para reduzir ruídos: `lowercase`, remoção de acentos, padronização de espaços, entre outras.  

**OCR (Reconhecimento Óptico de Caracteres)** — tecnologia que “lê” texto em imagens/PDFs escaneados; pode introduzir ruído/erros de caracteres.  

**Pipeline** — sequência de etapas do processamento (entrada → normalização → regras/LLM → classificação → saída/HTML).  

**Proximidade (ver “Janelas de proximidade”)** — relacionamento por distância entre termos.  

**Rationale (justificativa)** — explicação curta, idealmente com **citações literais**, de por que o texto foi classificado de uma certa forma.  

**RBAC (Role-Based Access Control)** — controle de acesso por papéis (ex.: revisor, advogado, administrador).  

**Regex (expressão regular)** — mini‑linguagem para **descrever padrões textuais** e localizar trechos específicos. Ex.: `\btransito em julgado\b`.  

**Rotulagem (labeling / ground truth)** — atividade humana de marcar exemplos como “Arquivamento forte/provável/não”, para treinar/avaliar os métodos.  

**Sentinel (marcador sentinela)** — marcador temporário para “proteger” palavras ambíguas durante a varredura. Ex.: substituir **“arquivo(s)”** (file) por `ARQFILE` para não confundir com **“arquivamento”**.  

**SERDON** — serviço de recortes/monitoramento de publicações dos diários oficiais usado pela FGV.  

**Snippet (trecho)** — pequeno fragmento do texto que mostra a evidência principal; usado em listas e pré-visualizações.  

**Trânsito em julgado** — fase em que não cabem mais recursos e a decisão se torna **definitiva**; comumente seguida de “arquivem-se”.  

**Window (janela)** — ver “Janelas de proximidade”.  
