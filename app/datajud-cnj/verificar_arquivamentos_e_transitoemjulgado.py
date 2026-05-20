"""
Verifica movimentos de transito em julgado, baixa e arquivamento
consultando a API publica DataJud para cada processo de uma planilha.

Execute diretamente pelo PyCharm (botao Run).
Edite o bloco CONFIGURACAO antes de executar.
"""

import sys
import os
import re
import time
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional

# Garante que datajud_consulta_manus seja encontrado mesmo que o
# working directory do PyCharm esteja configurado na raiz do projeto
sys.path.insert(0, str(Path(__file__).parent))
import datajud_consulta_manus

# ==============================================================
# CONFIGURACAO — edite aqui antes de executar
# ==============================================================
EXCEL_ENTRADA = Path(r"F:\FGV-SJUR\sjur-poc-voila\data_analysis\GERPRO-Ativos-2026-05-15.xlsx")
COLUNA_PROCESSOS = "B"         # Letra da coluna com os numeros de processo
LINHA_CABECALHO = 0            # 0 = primeira linha e cabecalho
PASTA_SAIDA = Path(r"F:\FGV-SJUR\resultado_transito_julgado")
DELAY_SEGUNDOS: float = 0.5   # Pausa entre consultas a API (segundos)
MAX_TENTATIVAS: int = 3        # Tentativas por processo em erro transitorio
SALVAR_CHECKPOINT: bool = True # Retomar de onde parou em caso de interrupcao
# ==============================================================

# Codigos TPU/CNJ monitorados: codigo -> (nome_legivel, sufixo_coluna)
ALVOS_TPU: dict = {
    848: ("Transito em Julgado",              "transito_em_julgado"),
    22:  ("Baixa Definitiva",                 "baixa_definitiva"),
    246: ("Arquivamento Definitivo",          "arquivamento_definitivo"),
    472: ("Arquivamento sumarissimo CLT",     "arquivamento_sumarissimo"),
    473: ("Arquivamento ausencia reclamante", "ausencia_reclamante"),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Auxiliares
# ------------------------------------------------------------------

def _primeira_data_mov(mov_list: list, codigo: int) -> str:
    """
    Retorna a data da ocorrencia mais antiga do codigo de movimentacao.
    Ordena por data_hora (ISO) antes de escolher, garantindo consistencia
    independente da ordem retornada pela API.
    Retorna string vazia se nao encontrado.
    """
    candidatas = [m for m in mov_list if m.get("codigo") == codigo]
    if not candidatas:
        return ""
    mais_antiga = min(candidatas, key=lambda m: m.get("data_hora") or "")
    return mais_antiga.get("data_formatada") or mais_antiga.get("data") or ""


def _consultar_com_retry(consulta, numero: str) -> dict:
    """Consulta o processo com backoff exponencial em falhas transitorias."""
    ultimo_erro: Exception = RuntimeError("Sem tentativas")
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            return consulta.consultar_processo_enriquecido(numero)
        except Exception as exc:
            ultimo_erro = exc
            if tentativa < MAX_TENTATIVAS:
                espera = DELAY_SEGUNDOS * (2 ** tentativa)
                log.warning(
                    f"  Tentativa {tentativa}/{MAX_TENTATIVAS} falhou: {exc}. "
                    f"Aguardando {espera:.1f}s..."
                )
                time.sleep(espera)
    raise RuntimeError(f"Falha apos {MAX_TENTATIVAS} tentativas") from ultimo_erro


def _carregar_checkpoint(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        log.info(f"Checkpoint encontrado: {len(dados)} processo(s) ja processado(s). Retomando...")
        return dados
    return {}


def _salvar_checkpoint(path: Path, dados: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _linha_nao_encontrado(numero: str) -> dict:
    row: dict = {
        "numero_processo":   numero,
        "encontrado_na_api": "Nao",
        "status":            "nao_encontrado",
        "movimentos_detectados": "",
    }
    for _, col in ALVOS_TPU.values():
        row[f"tem_{col}"]  = "N/A"
        row[f"data_{col}"] = ""
    return row


def _linha_erro(numero: str, exc: Exception) -> dict:
    row: dict = {
        "numero_processo":   numero,
        "encontrado_na_api": "Erro",
        "status":            str(exc),
        "movimentos_detectados": "",
    }
    for _, col in ALVOS_TPU.values():
        row[f"tem_{col}"]  = "Erro"
        row[f"data_{col}"] = ""
    return row


# ------------------------------------------------------------------
# Funcao principal
# ------------------------------------------------------------------

def verificar_baixa_arquivamento_transito(
    excel_path: Path = EXCEL_ENTRADA,
    coluna: str = COLUNA_PROCESSOS,
    pasta_saida: Path = PASTA_SAIDA,
) -> Optional[pd.DataFrame]:
    """
    Le uma planilha Excel, consulta cada processo no DataJud e detecta
    movimentos de transito em julgado, baixa definitiva e arquivamentos.

    Args:
        excel_path:  Caminho da planilha de entrada.
        coluna:      Letra da coluna com os numeros de processo.
        pasta_saida: Pasta onde a planilha de resultado sera salva.

    Returns:
        DataFrame com os resultados, ou None em caso de falha critica.
    """
    # Validacao da API Key antes de qualquer processamento
    if not os.getenv("DATAJUD_API_KEY"):
        log.error(
            "DATAJUD_API_KEY nao encontrada. "
            "Configure a variavel no arquivo .env e tente novamente."
        )
        return None

    # --- Leitura da planilha ---
    log.info(f"Carregando planilha: {excel_path}")
    try:
        df_entrada = pd.read_excel(excel_path, usecols=coluna, header=LINHA_CABECALHO)
    except Exception as exc:
        log.error(f"Erro ao ler planilha: {exc}")
        return None

    processos_brutos = df_entrada.iloc[:, 0].dropna().astype(str).tolist()

    # Normalizacao e validacao do formato CNJ (20 digitos)
    processos_validos = []
    for p in processos_brutos:
        limpo = re.sub(r"[^\d]", "", p)
        if len(limpo) == 20:
            processos_validos.append(limpo)
        else:
            log.warning(f"Ignorado (formato invalido): {p!r}")

    # Deduplicacao preservando a ordem original
    processos_unicos = list(dict.fromkeys(processos_validos))
    duplicatas = len(processos_validos) - len(processos_unicos)
    if duplicatas:
        log.info(f"{duplicatas} duplicata(s) removida(s).")
    log.info(f"{len(processos_unicos)} processo(s) unico(s) para consulta.")

    # --- Checkpoint ---
    pasta_saida.mkdir(parents=True, exist_ok=True)
    checkpoint_path = pasta_saida / f"checkpoint_{excel_path.stem}.json"
    checkpoint = _carregar_checkpoint(checkpoint_path) if SALVAR_CHECKPOINT else {}

    resultados: list = list(checkpoint.values())
    pendentes = [p for p in processos_unicos if p not in checkpoint]
    if checkpoint:
        log.info(f"Pendentes: {len(pendentes)}")

    # --- Loop de consultas ---
    consulta = datajud_consulta_manus.DatajudConsultaEnriquecida()

    for i, numero in enumerate(pendentes, start=1):
        log.info(f"[{i}/{len(pendentes)}] {numero}")
        info: dict

        try:
            resultado = _consultar_com_retry(consulta, numero)

            if resultado["sucesso"]:
                proc = resultado["processo"]
                movs_wrap = proc.get("movimentacoes") or {}
                movs = movs_wrap.get("movimentacoes") or []
                assuntos = proc["classificacao"].get("assuntos") or []

                multiplos = proc.get("multiplos_graus") or {}
                graus_lista = multiplos.get("graus") or []
                total_graus = multiplos.get("total_encontrado", 1)

                info = {
                    "numero_processo":     numero,
                    "encontrado_na_api":   "Sim",
                    "status":              "ok",
                    "tribunal":            proc["identificacao"]["tribunal"],
                    "grau":                proc["identificacao"]["grau"],
                    "em_multiplos_graus":  "Sim" if total_graus > 1 else "Nao",
                    "total_graus":         total_graus,
                    "graus":               ", ".join(str(g) for g in graus_lista),
                    "classe":              proc["classificacao"]["classe"].get("nome", "N/A"),
                    "assunto_principal":   assuntos[0].get("nome", "N/A") if assuntos else "N/A",
                    "data_ajuizamento":    proc["timestamps"]["data_ajuizamento_formatada"],
                    "orgao_julgador":      proc["orgao_julgador"]["nome"],
                    "municipio":           proc["orgao_julgador"]["municipio"]["nome"],
                    "total_movimentacoes": movs_wrap.get("total", 0),
                    "ultima_atualizacao":  proc["timestamps"]["ultima_atualizacao_formatada"],
                }

                detectados = []
                for codigo, (nome, col) in ALVOS_TPU.items():
                    data = _primeira_data_mov(movs, codigo)
                    info[f"tem_{col}"]  = "Sim" if data else "Nao"
                    info[f"data_{col}"] = data
                    if data:
                        detectados.append(f"{nome} @ {data}")

                info["movimentos_detectados"] = " | ".join(detectados)

                if detectados:
                    log.info(f"  Encontrado: {' | '.join(d.split(' @ ')[0] for d in detectados)}")
                else:
                    log.info("  Sem alvos detectados")

            else:
                log.warning("  Nao encontrado na API")
                info = _linha_nao_encontrado(numero)

        except Exception as exc:
            log.error(f"  Erro apos {MAX_TENTATIVAS} tentativas: {exc}")
            info = _linha_erro(numero, exc)

        resultados.append(info)

        if SALVAR_CHECKPOINT:
            checkpoint[numero] = info
            _salvar_checkpoint(checkpoint_path, checkpoint)

        time.sleep(DELAY_SEGUNDOS)

    # --- Exportacao ---
    if not resultados:
        log.warning("Nenhum resultado para exportar.")
        return None

    df_resultado = pd.DataFrame(resultados)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saida = pasta_saida / f"resultado_datajud_{timestamp}.xlsx"

    with pd.ExcelWriter(saida, engine="openpyxl") as writer:
        df_resultado.to_excel(writer, index=False, sheet_name="Resultados")
        ws = writer.sheets["Resultados"]
        for col in ws.columns:
            largura = max((len(str(c.value or "")) for c in col), default=0)
            ws.column_dimensions[col[0].column_letter].width = min(largura + 2, 50)

    log.info(f"Planilha salva em: {saida}")

    if SALVAR_CHECKPOINT and checkpoint_path.exists():
        checkpoint_path.unlink()
        log.info("Checkpoint removido.")

    _exibir_resumo(df_resultado, len(processos_unicos))
    return df_resultado


def _exibir_resumo(df: pd.DataFrame, total_entrada: int) -> None:
    encontrados     = (df["encontrado_na_api"] == "Sim").sum()
    nao_encontrados = (df["encontrado_na_api"] == "Nao").sum()
    erros           = (df["encontrado_na_api"] == "Erro").sum()

    log.info("=" * 52)
    log.info(f"Processos na entrada   : {total_entrada}")
    log.info(f"Encontrados na API     : {encontrados}")
    log.info(f"Nao encontrados        : {nao_encontrados}")
    log.info(f"Erros                  : {erros}")
    for _, (nome, col) in ALVOS_TPU.items():
        n = (df.get(f"tem_{col}") == "Sim").sum()
        if n:
            log.info(f"  {nome:<42}: {n}")
    log.info("=" * 52)


# ------------------------------------------------------------------
# Ponto de entrada — executar diretamente pelo PyCharm (botao Run)
# ------------------------------------------------------------------

if __name__ == "__main__":
    verificar_baixa_arquivamento_transito()
