"""
Inspeciona todas as movimentacoes de um processo no DataJud.

Util para comparar resultados entre aplicacoes diferentes.
Execute diretamente pelo PyCharm (botao Run).
Edite o bloco CONFIGURACAO antes de executar.
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import datajud_consulta_manus

# ==============================================================
# CONFIGURACAO — edite aqui antes de executar
# ==============================================================
NUMERO_PROCESSO = "08319230620248190021"   # numero CNJ (com ou sem mascara)
SALVAR_JSON     = True                     # salva resposta bruta em arquivo
PASTA_SAIDA     = Path(r"F:\FGV-SJUR\resultado_transito_julgado\inspecoes")
# ==============================================================


def formatar_numero(numero: str) -> str:
    limpo = re.sub(r"[^\d]", "", numero)
    if len(limpo) == 20:
        return f"{limpo[0:7]}-{limpo[7:9]}.{limpo[9:13]}.{limpo[13]}.{limpo[14:16]}.{limpo[16:]}"
    return numero


def inspecionar(numero: str) -> None:
    if not os.getenv("DATAJUD_API_KEY"):
        print("ERRO: DATAJUD_API_KEY nao encontrada. Configure no .env.")
        return

    limpo = re.sub(r"[^\d]", "", numero)
    if len(limpo) != 20:
        print(f"ERRO: numero invalido ({numero!r}). Esperado: 20 digitos.")
        return

    numero_formatado = formatar_numero(limpo)
    print("=" * 70)
    print(f"Processo : {numero_formatado}")
    print("=" * 70)

    consulta = datajud_consulta_manus.DatajudConsultaEnriquecida()
    resultado = consulta.consultar_processo_enriquecido(limpo)

    if not resultado["sucesso"]:
        print(f"\nNao encontrado: {resultado.get('erro')} — {resultado.get('detalhes')}")
        return

    proc      = resultado["processo"]
    movs_wrap = proc.get("movimentacoes") or {}
    movs      = movs_wrap.get("movimentacoes") or []
    multiplos = proc.get("multiplos_graus") or {}
    graus     = multiplos.get("graus") or [proc["identificacao"].get("grau", "?")]

    # --- Cabecalho do processo ---
    print(f"Tribunal  : {proc['identificacao']['tribunal']}")
    print(f"Grau(s)   : {', '.join(str(g) for g in graus)}")
    print(f"Classe    : {proc['classificacao']['classe'].get('nome', 'N/A')}")
    assuntos = proc["classificacao"].get("assuntos") or []
    print(f"Assunto   : {assuntos[0].get('nome', 'N/A') if assuntos else 'N/A'}")
    print(f"Ajuizamento : {proc['timestamps']['data_ajuizamento_formatada']}")
    print(f"Ult. atualiz.: {proc['timestamps']['ultima_atualizacao_formatada']}")
    print(f"Total movimentos (todos os graus): {movs_wrap.get('total', len(movs))}")

    if multiplos.get("total_encontrado", 1) > 1:
        print(f"\n*** ATENCAO: processo encontrado em {multiplos['total_encontrado']} graus ***")

    # --- Movimentacoes ordenadas por data ---
    movs_ordenados = sorted(movs, key=lambda m: m.get("data_hora") or "")

    print(f"\n{'─' * 70}")
    print(f"{'#':<5} {'Data':<18} {'Codigo':<8} {'Movimentacao'}")
    print(f"{'─' * 70}")

    for i, mov in enumerate(movs_ordenados, start=1):
        data    = mov.get("data_formatada") or mov.get("data_hora") or "?"
        codigo  = str(mov.get("codigo") or "?")
        nome    = mov.get("nome") or mov.get("descricao_interesse") or "?"
        print(f"{i:<5} {data:<18} {codigo:<8} {nome}")

        complementos = mov.get("complementos_tabelados") or []
        for comp in complementos:
            descricao = comp.get("descricao") or comp.get("nome") or ""
            valor     = comp.get("valor") or ""
            detalhe   = f"{descricao}: {valor}".strip(": ")
            if detalhe:
                print(f"{'':5} {'':18} {'':8}   >> {detalhe}")

    print(f"{'─' * 70}")
    print(f"Total exibido: {len(movs_ordenados)} movimentos")

    # --- Salvar JSON bruto ---
    if SALVAR_JSON:
        PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino  = PASTA_SAIDA / f"inspecao_{limpo}_{ts}.json"
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print(f"\nJSON completo salvo em: {destino}")

    print("=" * 70)


if __name__ == "__main__":
    inspecionar(NUMERO_PROCESSO)
