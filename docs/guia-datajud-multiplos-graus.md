# Guia: Consulta ao DataJud com suporte a múltiplos graus de jurisdição

Este guia orienta a implementação de um módulo de consulta à API pública do
DataJud (CNJ) que trata corretamente processos tramitando em mais de um grau
de jurisdição.

---

## Contexto

A API pública do DataJud é baseada em Elasticsearch. Ao consultar um número de
processo, ela pode retornar **múltiplos hits** — um por grau de jurisdição em
que o processo tramita (ex: 1º grau, 2º grau, TST).

Sem tratamento adequado, isso causa dois problemas:

1. **Data de ajuizamento incorreta** — o primeiro hit retornado não é
   necessariamente o mais antigo.
2. **Movimentações incompletas** — cada grau tem seus próprios movimentos;
   usar apenas um hit omite eventos relevantes.

---

## Fluxo esperado

```
Planilha Excel (números de processo)
        ↓
Detectar tribunal pelo número CNJ
        ↓
POST para endpoint DataJud do tribunal
        ↓
Receber lista de hits (um por grau)
        ↓
┌─────────────────────────────────────────────┐
│  Para metadados: eleger hit com menor       │
│  dataAjuizamento como base                  │
├─────────────────────────────────────────────┤
│  Para movimentações: consolidar de TODOS    │
│  os hits                                    │
└─────────────────────────────────────────────┘
        ↓
Exportar planilha com colunas de resultado
```

---

## 1. Detecção automática do tribunal

O número CNJ tem 20 dígitos no formato `NNNNNNN-DD.AAAA.J.TR.OOOO`.
Os campos `J` (posição 14) e `TR` (posições 15-16) identificam o tribunal.

```python
def detectar_tribunal(numero: str) -> str:
    limpo = re.sub(r'[^\d]', '', numero)
    ramo  = limpo[13]      # J
    tr    = limpo[14:16]   # TR
    return MAPEAMENTO_TRIBUNAIS.get((ramo, tr))
```

### Mapeamento correto (J=8, Justiça Estadual)

Use os códigos abaixo conforme a **Resolução 65 do CNJ**. Dicionários Python
não admitem chaves duplicadas — qualquer repetição silencia o tribunal errado.

```python
MAPEAMENTO_TRIBUNAIS = {
    # Superiores
    ('1', '00'): 'stf',  ('2', '00'): 'stj',
    ('4', '01'): 'trf1', ('4', '02'): 'trf2', ('4', '03'): 'trf3',
    ('4', '04'): 'trf4', ('4', '05'): 'trf5', ('4', '06'): 'trf6',
    ('5', '00'): 'tst',
    ('5', '01'): 'trt1',  ('5', '02'): 'trt2',  ('5', '03'): 'trt3',
    ('5', '04'): 'trt4',  ('5', '05'): 'trt5',  ('5', '06'): 'trt6',
    ('5', '07'): 'trt7',  ('5', '08'): 'trt8',  ('5', '09'): 'trt9',
    ('5', '10'): 'trt10', ('5', '11'): 'trt11', ('5', '12'): 'trt12',
    ('5', '13'): 'trt13', ('5', '14'): 'trt14', ('5', '15'): 'trt15',
    ('5', '16'): 'trt16', ('5', '17'): 'trt17', ('5', '18'): 'trt18',
    ('5', '19'): 'trt19', ('5', '20'): 'trt20', ('5', '21'): 'trt21',
    ('5', '22'): 'trt22', ('5', '23'): 'trt23', ('5', '24'): 'trt24',
    ('6', '00'): 'tse',  ('7', '00'): 'stm',
    # Justiça Estadual — Resolução 65 CNJ (sem duplicatas)
    ('8', '01'): 'tjap', ('8', '02'): 'tjac', ('8', '03'): 'tjam',
    ('8', '04'): 'tjal', ('8', '05'): 'tjba', ('8', '06'): 'tjce',
    ('8', '07'): 'tjdft', ('8', '08'): 'tjes', ('8', '09'): 'tjmt',
    ('8', '10'): 'tjgo', ('8', '11'): 'tjmg', ('8', '12'): 'tjms',
    ('8', '13'): 'tjma', ('8', '14'): 'tjpa', ('8', '15'): 'tjpb',
    ('8', '16'): 'tjpr', ('8', '17'): 'tjpe', ('8', '18'): 'tjpi',
    ('8', '19'): 'tjrj', ('8', '20'): 'tjrn', ('8', '21'): 'tjrs',
    ('8', '22'): 'tjro', ('8', '23'): 'tjrr', ('8', '24'): 'tjsc',
    ('8', '25'): 'tjse', ('8', '26'): 'tjsp', ('8', '27'): 'tjto',
}
```

O endpoint para cada tribunal segue o padrão:
```
https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search
```

---

## 2. Consolidação dos hits

### 2.1 Data de ajuizamento — eleger o hit mais antigo

```python
# Elege o hit com menor dataAjuizamento como base dos metadados
hit_base = hits[0]
for hit in hits:
    data_atual = hit.get('_source', {}).get('dataAjuizamento') or ''
    data_base  = hit_base.get('_source', {}).get('dataAjuizamento') or ''
    if data_atual and (not data_base or data_atual < data_base):
        hit_base = hit

processo_base = extrair_detalhes_processo(hit_base)
```

> A comparação `data_atual < data_base` funciona com strings ISO 8601
> (`YYYY-MM-DD` ou `YYYY-MM-DDTHH:MM:SS`), que são ordenáveis
> lexicograficamente.

### 2.2 Movimentações — consolidar de todos os hits

```python
todas_movimentacoes = []
for hit in hits:
    todas_movimentacoes.extend(
        hit.get('_source', {}).get('movimentos', [])
    )

processo_base['movimentacoes'] = analisar_movimentacoes(todas_movimentacoes)
```

### 2.3 Expor informação de múltiplos graus

```python
processo_base['multiplos_graus'] = {
    'total_encontrado': len(hits),
    'graus': [hit['_source'].get('grau', '') for hit in hits],
}
```

---

## 3. Data de movimentação por código TPU

Ao buscar a data de um movimento específico (ex: Trânsito em Julgado = código
`848`), **ordene por `dataHora` antes de retornar** para garantir consistência
independente da ordem da API:

```python
def primeira_data_mov(mov_list: list, codigo: int) -> str:
    candidatas = [m for m in mov_list if m.get('codigo') == codigo]
    if not candidatas:
        return ''
    mais_antiga = min(candidatas, key=lambda m: m.get('dataHora') or '')
    return mais_antiga.get('dataFormatada') or mais_antiga.get('dataHora') or ''
```

---

## 4. Colunas recomendadas na planilha de saída

### Identificação e metadados

| Coluna | Descrição |
|---|---|
| `numero_processo` | Número CNJ (20 dígitos) |
| `encontrado_na_api` | `Sim`, `Nao` ou `Erro` |
| `tribunal` | Nome do tribunal |
| `grau` | Grau do hit base (ex: `G1`) |
| `em_multiplos_graus` | `Sim` se `total_encontrado > 1` |
| `total_graus` | Quantidade de graus encontrados |
| `graus` | Lista separada por vírgula (ex: `G1, G2`) |
| `data_ajuizamento` | Data do hit mais antigo |
| `total_movimentacoes` | Total consolidado de todos os graus |

### Por alvo TPU

Para cada código monitorado, gerar duas colunas:

| Coluna | Descrição |
|---|---|
| `tem_{alvo}` | `Sim` / `Nao` / `N/A` / `Erro` |
| `data_{alvo}` | Data da ocorrência mais antiga |

Valores especiais:
- `N/A` — processo não encontrado na API
- `Erro` — falha após todas as tentativas de retry

---

## 5. Boas práticas operacionais

### Retry com backoff exponencial

```python
for tentativa in range(1, MAX_TENTATIVAS + 1):
    try:
        return consultar(numero)
    except Exception as exc:
        if tentativa < MAX_TENTATIVAS:
            time.sleep(DELAY * (2 ** tentativa))
        else:
            raise
```

### Checkpoint para retomada

Salvar um JSON `{numero_processo: resultado}` após cada processo permite
retomar execuções interrompidas sem reprocessar o que já foi consultado.

### Validação da API Key antes do loop

```python
if not os.getenv('DATAJUD_API_KEY'):
    raise RuntimeError('DATAJUD_API_KEY não configurada.')
```

### Deduplicação preservando ordem

```python
processos_unicos = list(dict.fromkeys(processos_validos))
```
