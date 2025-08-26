# Consulta API Datajud - Projeto de Integração

Este projeto implementa uma solução completa para consulta de processos judiciais brasileiros através da API Pública do Datajud (CNJ).

## 📋 Funcionalidades

- ✅ **Validação automática** do formato de número de processo CNJ
- ✅ **Extração inteligente** dos segmentos do número (ramo da justiça, tribunal)
- ✅ **Mapeamento automático** para o endpoint correto da API
- ✅ **Tratamento robusto de erros** e diferentes cenários de resposta
- ✅ **Suporte a múltiplos formatos** de entrada (com/sem formatação)
- ✅ **Cobertura completa** dos 91 tribunais brasileiros

## 🏗️ Arquitetura

### Fase 1: Análise do Número do Processo ✅
- Validação do formato CNJ (20 dígitos)
- Extração dos segmentos J (ramo) e TR (tribunal)
- Mapeamento para endpoint da API

### Fase 2: Consulta à API ✅
- Autenticação via Basic Auth
- Construção da query JSON
- Tratamento de respostas e erros

### Fase 3: Processamento dos Dados (Próxima)
- Estruturação dos dados retornados
- Extração de informações relevantes
- Formatação para uso posterior

## 🚀 Como Usar

### 1. Configurar Credenciais

```bash
# Opção 1: Variáveis de ambiente (RECOMENDADO)
export DATAJUD_USUARIO="seu_usuario"
export DATAJUD_SENHA="sua_senha"
```

```python
# Opção 2: Diretamente no código
consulta = DatajudConsulta(usuario="seu_usuario", senha="sua_senha")
```

### 2. Consultar um Processo

```python
from datajud_consulta import DatajudConsulta

# Inicializar
consulta = DatajudConsulta()

# Consultar processo
numero = "0000832-35.2018.4.01.3202"
resultado = consulta.consultar_processo(numero)

if resultado["sucesso"]:
    print("Processo encontrado!")
    dados = resultado["dados_brutos"]
    print(f"Tribunal: {dados['tribunal']}")
    print(f"Data: {dados['dataAjuizamento']}")
else:
    print(f"Erro: {resultado['erro']}")
```

## 📊 Estrutura dos Dados Retornados

### Sucesso
```json
{
  "sucesso": true,
  "numero_processo": "00008323520184013202",
  "ramo_justica": "4",
  "codigo_tribunal": "01", 
  "endpoint_usado": "https://api-publica.datajud.cnj.jus.br/api_publica_trf1/_search",
  "dados_brutos": {
    "tribunal": "TRF1",
    "dataAjuizamento": "2018-01-15T10:30:00",
    "grau": "G1",
    "classe": {"codigo": "319", "nome": "Procedimento Comum Cível"},
    "assuntos": [...],
    "movimentos": [...],
    "orgaoJulgador": {...}
  },
  "timestamp_consulta": "2024-01-15T14:30:00"
}
```

### Erro
```json
{
  "sucesso": false,
  "erro": "Processo não encontrado",
  "detalhes": "O processo pode ser sigiloso, muito recente ou não estar indexado",
  "numero_processo": "00008323520184013202",
  "endpoint_usado": "https://..."
}
```

## 🗺️ Mapeamento de Tribunais

O sistema suporta todos os 91 tribunais brasileiros:

| Ramo | Código | Tribunal | Alias API |
|------|--------|----------|-----------|
| 1 | 00 | STF | `stf` |
| 2 | 00 | STJ | `stj` |
| 4 | 01-06 | TRF1-TRF6 | `trf1`-`trf6` |
| 5 | 00 | TST | `tst` |
| 5 | 01-24 | TRT1-TRT24 | `trt1`-`trt24` |
| 6 | 00 | TSE | `tse` |
| 6 | XX | TREs | `treXX` |
| 7 | 00 | STM | `stm` |
| 8 | XX | TJs | `tjXX` |

## 🔍 Formatos Suportados

O sistema aceita números de processo em diversos formatos:

- `0000832-35.2018.4.01.3202` (formato padrão)
- `00008323520184013202` (sem formatação)
- `832-35.2018.4.01.3202` (sem zeros à esquerda)
- `0000832.35.2018.4.01.3202` (pontos em vez de hífen)

## ⚠️ Tratamento de Erros

### Tipos de Erro Cobertos:
- **Formato inválido**: Número não segue padrão CNJ
- **Tribunal não mapeado**: Código de tribunal não reconhecido
- **Credenciais inválidas**: Usuário/senha incorretos
- **Processo não encontrado**: Pode ser sigiloso ou não indexado
- **Timeout**: API demorou para responder
- **Erro de conexão**: Problemas de rede

## 📁 Arquivos do Projeto

- `datajud_consulta.py` - Classe principal de consulta
- `exemplo_configuracao.py` - Exemplos de uso e configuração
- `README.md` - Esta documentação

## 🔄 Próximos Passos

1. **Fase 3**: Implementar processamento estruturado dos dados
2. **Otimizações**: Cache de consultas, rate limiting
3. **Expansão**: Suporte a consultas em lote
4. **Interface**: CLI ou web interface

## 📚 Referências

- [Documentação Oficial API Datajud](https://datajud.cnj.jus.br/)
- [Padrão de Numeração CNJ](https://www.cnj.jus.br/programas-e-acoes/numeracao-unica/)
- [Tutorial API Pública Datajud Beta](tutorial-api-publica-datajud-beta.pdf)

---

**Desenvolvido para maximizar a extração de informações processuais via API Datajud**

