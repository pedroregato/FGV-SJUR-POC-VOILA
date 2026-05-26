"""
Verifica processos com Baixa Definitiva (codigo TPU 22)
consultando a API publica DataJud a partir de uma planilha Excel.

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

sys.path.insert(0, str(Path(__file__).parent))
import datajud_consulta_manus

# ==============================================================
# CONFIGURACAO — edite aqui antes de executar
# ==============================================================
EXCEL_ENTRADA = Path(r"F:\FGV-SJUR\sjur-poc-voila\data_analysis\GERPRO-Ativos-2026-05-15.xlsx")
COLUNA_PROCESSOS = "B"         # Letra da coluna com os numeros de processo
LINHA_CABECALHO  = 0           # 0 = primeira linha e cabecalho
PASTA_SAIDA      = Path(r"F:\FGV-SJUR\resultado_baixa_definitiva")
DELAY_SEGUNDOS: float = 0.5   # Pausa entre consultas a API (segundos)
MAX_TENTATIVAS: int   = 3      # Tentativas por processo em erro transitorio
SALVAR_CHECKPOINT: bool = True # Retomar de onde parou em caso de interrupcao
# ==============================================================

CODIGO_ALVO = 22
NOME_ALVO   = "Baixa Definitiva"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Auxiliares
# ------------------------------------------------------------------

def _data_mais_antiga(mov_list: list, codigo: int) -> str:
    """Retorna a data da ocorrencia mais antiga do codigo. '' se ausente."""
    candidatas = [m for m in mov_list if m.get("codigo") == codigo]
    if not candidatas:
        return ""
    mais_antiga = min(candidatas, key=lambda m: m.get("data_hora") or "")
    return mais_antiga.get("data_formatada") or mais_antiga.get("data") or ""


def _consultar_com_retry(consulta, numero: str) -> dict:
    ultimo_erro: Exception = RuntimeError("Sem tentativas")
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            return consulta.consultar_processo_enriquecido(numero)
        except Exception as exc:
            ultimo_erro = exc
            if tentativa < MAX_TENTATIVAS:
                espera = DELAY_SEGUNDOS * (2 ** tentativa)
                log.warning(f"  Tentativa {tentativa}/{MAX_TENTATIVAS} falhou: {exc}. Aguardando {espera:.1f}s...")
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


# ------------------------------------------------------------------
# Funcao principal
# ------------------------------------------------------------------

def verificar_baixa_definitiva(
    excel_path: Path = EXCEL_ENTRADA,
    coluna: str = COLUNA_PROCESSOS,
    pasta_saida: Path = PASTA_SAIDA,
) -> Optional[pd.DataFrame]:
    """
    Le uma planilha Excel e verifica quais processos possuem
    Baixa Definitiva (codigo TPU 22) no DataJud.

    Args:
        excel_path:  Caminho da planilha de entrada.
        coluna:      Letra da coluna com os numeros de processo.
        pasta_saida: Pasta onde a planilha de resultado sera salva.

    Returns:
        DataFrame com os resultados, ou None em caso de falha critica.
    """
    if not os.getenv("DATAJUD_API_KEY"):
        log.error("DATAJUD_API_KEY nao encontrada. Configure no .env e tente novamente.")
        return None

    # --- Leitura da planilha ---
    log.info(f"Carregando planilha: {excel_path}")
    try:
        df_entrada = pd.read_excel(excel_path, usecols=coluna, header=LINHA_CABECALHO)
    except Exception as exc:
        log.error(f"Erro ao ler planilha: {exc}")
        return None

    processos_brutos = df_entrada.iloc[:, 0].dropna().astype(str).tolist()

    processos_validos = []
    for p in processos_brutos:
        limpo = re.sub(r"[^\d]", "", p)
        if len(limpo) == 20:
            processos_validos.append(limpo)
        else:
            log.warning(f"Ignorado (formato invalido): {p!r}")

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
                proc      = resultado["processo"]
                movs_wrap = proc.get("movimentacoes") or {}
                movs      = movs_wrap.get("movimentacoes") or []
                assuntos  = proc["classificacao"].get("assuntos") or []
                multiplos = proc.get("multiplos_graus") or {}
                graus     = multiplos.get("graus") or [proc["identificacao"].get("grau", "")]
                total_graus = multiplos.get("total_encontrado", 1)

                data_baixa = _data_mais_antiga(movs, CODIGO_ALVO)

                info = {
                    "numero_processo":    numero,
                    "encontrado_na_api":  "Sim",
                    "status":             "ok",
                    "tem_baixa_definitiva":  "Sim" if data_baixa else "Nao",
                    "data_baixa_definitiva": data_baixa,
                    "tribunal":           proc["identificacao"]["tribunal"],
                    "grau":               proc["identificacao"]["grau"],
                    "em_multiplos_graus": "Sim" if total_graus > 1 else "Nao",
                    "total_graus":        total_graus,
                    "graus":              ", ".join(str(g) for g in graus),
                    "classe":             proc["classificacao"]["classe"].get("nome", "N/A"),
                    "assunto_principal":  assuntos[0].get("nome", "N/A") if assuntos else "N/A",
                    "data_ajuizamento":   proc["timestamps"]["data_ajuizamento_formatada"],
                    "orgao_julgador":     proc["orgao_julgador"]["nome"],
                    "municipio":          proc["orgao_julgador"]["municipio"]["nome"],
                    "total_movimentacoes": movs_wrap.get("total", 0),
                    "ultima_atualizacao": proc["timestamps"]["ultima_atualizacao_formatada"],
                }

                if data_baixa:
                    log.info(f"  Encontrado: {NOME_ALVO} @ {data_baixa}")
                else:
                    log.info("  Sem baixa definitiva")

            else:
                log.warning("  Nao encontrado na API")
                info = {
                    "numero_processo":       numero,
                    "encontrado_na_api":     "Nao",
                    "status":                "nao_encontrado",
                    "tem_baixa_definitiva":  "N/A",
                    "data_baixa_definitiva": "",
                }

        except Exception as exc:
            log.error(f"  Erro apos {MAX_TENTATIVAS} tentativas: {exc}")
            info = {
                "numero_processo":       numero,
                "encontrado_na_api":     "Erro",
                "status":                str(exc),
                "tem_baixa_definitiva":  "Erro",
                "data_baixa_definitiva": "",
            }

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
    saida = pasta_saida / f"baixa_definitiva_{timestamp}.xlsx"

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
    com_baixa       = (df.get("tem_baixa_definitiva") == "Sim").sum()

    log.info("=" * 52)
    log.info(f"Processos na entrada   : {total_entrada}")
    log.info(f"Encontrados na API     : {encontrados}")
    log.info(f"Nao encontrados        : {nao_encontrados}")
    log.info(f"Erros                  : {erros}")
    log.info(f"Com Baixa Definitiva   : {com_baixa}")
    log.info("=" * 52)


# ------------------------------------------------------------------
# Ponto de entrada — executar diretamente pelo PyCharm (botao Run)
# ------------------------------------------------------------------

if __name__ == "__main__":
    verificar_baixa_definitiva()
