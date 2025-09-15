# SJUR Coletor — Guia Rápido

Pacote de coleta de e-mails do Outlook com UI em Streamlit e modo CLI, preparado para identificar publicações e aplicar heurísticas de arquivamento.

## Conteúdo do pacote
- `app_coletor.py` — UI Streamlit (frontend para operar a coleta)
- `coletar_emails_para_outputs.py` — Núcleo da coleta + `main()` (CLI)
- `archival_rules.py` — Motor de heurísticas
- `archival_heuristic_rules.json` — Regras/regex e limiares
- `README.md` — Este guia

## Pré‑requisitos
- **Windows** com Microsoft **Outlook** configurado (perfil/logado).  
- **Python 3.8+** (recomendado 3.10/3.11).  
- Arquitetura **coerente**: Python e Office ambos 64‑bit (ou ambos 32‑bit).

Instalação de dependências:
```bash
pip install streamlit pywin32 beautifulsoup4 lxml
```

> Se usar um ambiente virtual:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # (opcional; ou instale os pacotes acima)
```

## Como executar (UI)
```bash
streamlit run app_coletor.py
```
Na UI:
1. Selecione **Conta/Pasta** (deixe conta vazia para usar a padrão da máquina).
2. Escolha a **Janela de datas**: _Tudo_, _Hoje_, _Últimos 7 dias_ ou _Período_ (com início/fim).
3. **Limite de e‑mails** (0 = sem limite) e **Limpar pasta de saída** (opcional).
4. Clique **Executar Coleta**.

## Como executar (CLI)
Exemplos:
```bash
# Hoje, limite 5
python coletar_emails_para_outputs.py --mode hoje --limit 5 --folder "Inbox\SERDON"

# Últimos 7 dias, sem limite e limpando a saída
python coletar_emails_para_outputs.py --mode ultimos7 --limit 0 --reset-out

# Período customizado
python coletar_emails_para_outputs.py --mode periodo --start-date 2025-09-01 --end-date 2025-09-07
```
Parâmetros úteis:
- `--account` SMTP da conta (opcional)
- `--folder` pasta (ex.: `Inbox\SERDON`)
- `--limit` número máximo (0 = sem limite)
- `--output-dir` diretório de saída (padrão `outputs`)
- `--reset-out` apagar saída antes
- `--mode` `tudo|hoje|ultimos7|periodo`
- `--start-date` / `--end-date` (para `periodo`). Aceita `YYYY-MM-DD` ou `DD/MM/YYYY`.

## Saídas geradas
Estrutura em `outputs/` (criada na primeira execução):
- `html/` — `email_0000.html`, `email_0001.html`, ...
- `json/` — `email_0000.json`, `email_0001.json`, ...
- `arquivamento.csv` — uma linha por **publicação** com `cnjs`, `score`, `level`
- `emails.jsonl` — um **e‑mail por linha** (JSON)

## Regras e heurísticas
- Padrões/regex no `archival_heuristic_rules.json` (inclui CNJ e gatilhos de arquivamento).
- Escore agregado normalizado em 0..1 → níveis: **fraco**, **provavel**, **forte**.
- Ajuste `thresholds.forte` e `thresholds.provavel` conforme seu domínio.

## Detalhes importantes
- O filtro de datas do Outlook usa **mm/dd/yyyy HH:MM** (formato exigido pelo MAPI).
- Para as janelas de data, o coletor faz **uma única cláusula** `Restrict(...)` e
  percorre por ordem decrescente de `ReceivedTime` até o limite.

## Agendamento (Task Scheduler)
Crie um `.bat` como exemplo:
```bat
@echo off
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"
REM Ativar venv se houver: call .venv\Scripts\activate
python coletar_emails_para_outputs.py --mode ultimos7 --limit 5 --output-dir outputs --reset-out
```
Agende no **Agendador de Tarefas** (iniciar numa pasta que contenha os arquivos).

## Solução de problemas
- **`Unresolved reference 'Optional'`**: verifique se não existe arquivo local `typing.py` na pasta do projeto; isso “sombra” a lib padrão. Confirme Python 3.8+ e salve o arquivo após corrigir barras invertidas `\`.
- **Erro COM / `Class not registered`**: geralmente é **mismatch de arquitetura** (Python x Office). Instale a versão do Python que corresponda ao Office (x64 ↔ x64).
- **Sem progresso aparente**: a Fase 1 agora emite progresso incremental; se a UI parecer parada, confira logs no painel direito.
- **Falha ao gravar saídas**: use a opção **Limpar pasta de saída** ou garanta permissões no diretório alvo.
- **Sem e‑mails retornados**: confirme a pasta e a janela de datas. Lembre-se do formato mm/dd/yyyy no `Restrict`.

---
Gerado em 2025-09-12 00:06:14.