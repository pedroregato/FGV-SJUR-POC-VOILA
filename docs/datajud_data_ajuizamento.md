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
