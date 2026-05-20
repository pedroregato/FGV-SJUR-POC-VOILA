## Diretriz: Data de Ajuizamento em Consultas ao DataJud

### Contexto

A API pública do DataJud (CNJ) pode retornar **múltiplos hits** para um mesmo
número de processo quando ele tramita em mais de um grau de jurisdição (ex: 1º e
2º grau indexados separadamente). Cada hit possui seu próprio campo
`dataAjuizamento`.

### Problema

Selecionar o **primeiro hit** retornado pelo Elasticsearch como registro base do
processo não garante que a data de ajuizamento corresponda à instância de origem.
A ordem dos hits é determinada pelo score de relevância do Elasticsearch, não pela
cronologia do processo.

### Diretriz

Ao consolidar múltiplos hits de um mesmo processo, **eleger como registro base
aquele com o menor `dataAjuizamento`** entre todos os hits retornados.

Essa abordagem garante que a data de ajuizamento sempre reflita a instância de
origem do processo, independente da ordem de retorno da API.

### Implementação de referência (Python)

```python
hit_base = hits[0]
for hit in hits:
    data_atual = hit.get('_source', {}).get('dataAjuizamento') or ''
    data_base  = hit_base.get('_source', {}).get('dataAjuizamento') or ''
    if data_atual and (not data_base or data_atual < data_base):
        hit_base = hit

processo_base = extrair_detalhes_processo(hit_base)
```

> **Nota:** A comparação `data_atual < data_base` funciona diretamente com strings
> no formato ISO 8601 (`YYYY-MM-DD` ou `YYYY-MM-DDTHH:MM:SS`), que são
> ordenáveis lexicograficamente.

### O que NÃO fazer

```python
# Errado: usa o primeiro hit sem critério de seleção
if not processos_por_grau:
    processo_base = extrair_detalhes_processo(hits[0])
```

### Campos consolidados à parte

A seleção do hit base se aplica apenas aos **metadados do processo** (identificação,
classificação, órgão julgador, timestamps). As **movimentações** devem continuar
sendo consolidadas de **todos os hits**, pois cada grau pode ter movimentos
relevantes:

```python
todas_movimentacoes = []
for hit in hits:
    todas_movimentacoes.extend(hit.get('_source', {}).get('movimentos', []))

processo_base['movimentacoes'] = analisar_movimentacoes(todas_movimentacoes)
```

---

## Colunas de saída da planilha

### Colunas de identificação e metadados

| Coluna | Descrição |
|---|---|
| `numero_processo` | Número CNJ do processo (20 dígitos) |
| `encontrado_na_api` | `Sim`, `Nao` ou `Erro` |
| `status` | `ok`, `nao_encontrado` ou descrição do erro |
| `tribunal` | Nome do tribunal retornado pela API |
| `grau` | Grau de jurisdição do hit base (ex: `G1`, `G2`) |
| `em_multiplos_graus` | `Sim` se o processo foi encontrado em mais de um grau |
| `total_graus` | Quantidade de graus encontrados na API |
| `graus` | Lista dos graus encontrados separados por vírgula (ex: `G1, G2`) |
| `classe` | Classe processual (ex: Reclamação Trabalhista) |
| `assunto_principal` | Primeiro assunto listado na classificação |
| `data_ajuizamento` | Data de ajuizamento do hit mais antigo (ver diretriz acima) |
| `orgao_julgador` | Nome do órgão julgador do hit base |
| `municipio` | Município do órgão julgador |
| `total_movimentacoes` | Total de movimentos consolidados de todos os graus |
| `ultima_atualizacao` | Data/hora da última atualização do hit base |
| `movimentos_detectados` | Resumo dos alvos TPU encontrados com datas |

### Colunas por alvo TPU

Para cada código de movimentação monitorado são geradas duas colunas:

| Coluna | Descrição |
|---|---|
| `tem_transito_em_julgado` | `Sim` / `Nao` / `N/A` / `Erro` |
| `data_transito_em_julgado` | Data da ocorrência mais antiga (formato `DD/MM/YYYY HH:MM`) |
| `tem_baixa_definitiva` | `Sim` / `Nao` / `N/A` / `Erro` |
| `data_baixa_definitiva` | Data da ocorrência mais antiga |
| `tem_arquivamento_definitivo` | `Sim` / `Nao` / `N/A` / `Erro` |
| `data_arquivamento_definitivo` | Data da ocorrência mais antiga |
| `tem_arquivamento_sumarissimo` | `Sim` / `Nao` / `N/A` / `Erro` |
| `data_arquivamento_sumarissimo` | Data da ocorrência mais antiga |
| `tem_ausencia_reclamante` | `Sim` / `Nao` / `N/A` / `Erro` |
| `data_ausencia_reclamante` | Data da ocorrência mais antiga |

> **Nota sobre datas de movimentação:** a data retornada é sempre a ocorrência
> **mais antiga** do código TPU entre todos os movimentos consolidados de todos
> os graus, ordenados por `dataHora` ISO antes da seleção.

### Valores especiais

| Valor | Significado |
|---|---|
| `Sim` / `Nao` | Processo encontrado na API |
| `N/A` | Processo não encontrado na API (sem dados para avaliar) |
| `Erro` | Falha na consulta após todas as tentativas de retry |
