import pandas as pd
import os
import re
from datetime import datetime
import time
import datajud_consulta_manus  # sua classe de consulta já existente

# ---------------------------------------------
# Códigos-alvo (TPU/CNJ)
# ---------------------------------------------
ALVOS_TPU = {
    848: "Trânsito em Julgado",                                  # já havia no seu código
    22:  "Baixa definitiva",                                     # baixa
    246: "Arquivados os autos definitivamente (Arquivamento definitivo)",  # arquivamento definitivo
    472: "Arquivamento (rito sumaríssimo, art. 852-B, §1º, CLT)",          # JT
    473: "Arquivamento por ausência do reclamante",                         # JT
}

def _primeira_data_mov(mov_list, codigo):
    """
    Retorna a primeira data_formatada (string) para o 'codigo' na lista de movimentos do processo.
    Se não houver, retorna ''.
    """
    for mov in mov_list:
        if mov.get("codigo") == codigo:
            # tenta pegar 'data_formatada' (se sua classe já devolve neste campo)
            dt = mov.get("data_formatada") or mov.get("data")
            return dt or ""
    return ""

def verificar_baixa_arquivamento_transito(excel_path):
    """
    Lê planilha Excel com processos (coluna B), consulta no DataJud
    e verifica ocorrências de:
      - Trânsito em Julgado (848)
      - Baixa definitiva (22)
      - Arquivamento definitivo (246)
      - Arquivamento sumaríssimo CLT (472)
      - Arquivamento por ausência do reclamante (473)
    Gera planilha Excel com indicadores por processo.
    """

    # Carrega a planilha
    try:
        df = pd.read_excel(excel_path, usecols="B", header=0)
    except Exception as e:
        print(f"❌ Erro ao carregar Excel: {e}")
        return None

    # Extrai valores da coluna B
    processos = df.iloc[:, 0].dropna().astype(str).tolist()
    print(f"📊 Total de processos lidos: {len(processos)}")

    # Filtra apenas CNJs válidos (20 dígitos)
    processos_cnj_validos = []
    for processo in processos:
        numero_limpo = re.sub(r"[^\d]", "", processo)
        if len(numero_limpo) == 20:
            processos_cnj_validos.append(numero_limpo)
        else:
            print(f"⚠️ Processo ignorado (formato inválido): {processo}")

    print(f"✅ Processos CNJ válidos para consulta: {len(processos_cnj_validos)}")

    # Inicializa consulta Datajud
    consulta = datajud_consulta_manus.DatajudConsultaEnriquecida()

    resultados = []

    for i, numero_processo in enumerate(processos_cnj_validos, 1):
        print(f"🔍 Consultando processo {i}/{len(processos_cnj_validos)}: {numero_processo}")

        try:
            resultado = consulta.consultar_processo_enriquecido(numero_processo)

            if resultado["sucesso"]:
                proc = resultado["processo"]
                movs_wrap = proc.get("movimentacoes", {}) or {}
                movs = movs_wrap.get("movimentacoes", []) or []

                # mapa: codigo -> (bool encontrado, primeira_data)
                flags = {}
                for codigo, rotulo in ALVOS_TPU.items():
                    dt = _primeira_data_mov(movs, codigo)
                    flags[codigo] = (bool(dt), dt)

                # resumo dos movimentos detectados (para auditoria/depuração)
                detectados = []
                for codigo, (ok, dt) in flags.items():
                    if ok:
                        detectados.append(f"{codigo} - {ALVOS_TPU[codigo]} @ {dt}")
                resumo_detectados = " | ".join(detectados) if detectados else ""

                info = {
                    "numero_processo": proc["identificacao"]["numero_processo"],
                    "tribunal": proc["identificacao"]["tribunal"],
                    "grau": proc["identificacao"]["grau"],
                    "classe": proc["classificacao"]["classe"].get("nome", "N/A"),
                    "assunto_principal": proc["classificacao"]["assuntos"][0].get("nome", "N/A")
                        if proc["classificacao"]["assuntos"] else "N/A",
                    "data_ajuizamento": proc["timestamps"]["data_ajuizamento_formatada"],
                    "orgao_julgador": proc["orgao_julgador"]["nome"],
                    "municipio": proc["orgao_julgador"]["municipio"]["nome"],
                    "total_movimentacoes": movs_wrap.get("total", 0),
                    "ultima_atualizacao": proc["timestamps"]["ultima_atualizacao_formatada"],
                    "encontrado_na_api": "Sim",
                    # campos antigos para compatibilidade:
                    "tem_transito_em_julgado": "Sim" if flags.get(848, (False, ""))[0] else "Não",
                    "data_transito_em_julgado": flags.get(848, (False, ""))[1] or "",
                    # novos campos por código:
                    "tem_baixa_definitiva_22": "Sim" if flags.get(22, (False, ""))[0] else "Não",
                    "data_baixa_definitiva_22": flags.get(22, (False, ""))[1] or "",
                    "tem_arquivamento_definitivo_246": "Sim" if flags.get(246, (False, ""))[0] else "Não",
                    "data_arquivamento_definitivo_246": flags.get(246, (False, ""))[1] or "",
                    "tem_arquivamento_sumarissimo_472": "Sim" if flags.get(472, (False, ""))[0] else "Não",
                    "data_arquivamento_sumarissimo_472": flags.get(472, (False, ""))[1] or "",
                    "tem_ausencia_reclamante_473": "Sim" if flags.get(473, (False, ""))[0] else "Não",
                    "data_ausencia_reclamante_473": flags.get(473, (False, ""))[1] or "",
                    # campo consolidado
                    "movimentos_detectados": resumo_detectados
                }

                resultados.append(info)

                if flags.get(848, (False, ""))[0]:
                    print(f"✅ {numero_processo} - TRÂNSITO EM JULGADO")
                if any(flags[c][0] for c in (22, 246, 472, 473)):
                    print(f"📁 {numero_processo} - Algum ARQUIVAMENTO/BAIXA encontrado")
                if not (flags.get(848, (False, ""))[0] or any(flags[c][0] for c in (22, 246, 472, 473))):
                    print(f"🚫 {numero_processo} - Sem trânsito/arquivamentos-alvo")

            else:
                print(f"❌ Processo {numero_processo} não encontrado na API")
                resultados.append({
                    "numero_processo": numero_processo,
                    "encontrado_na_api": "Não",
                    "tem_transito_em_julgado": "N/A",
                    "data_transito_em_julgado": "",
                    "tem_baixa_definitiva_22": "N/A",
                    "data_baixa_definitiva_22": "",
                    "tem_arquivamento_definitivo_246": "N/A",
                    "data_arquivamento_definitivo_246": "",
                    "tem_arquivamento_sumarissimo_472": "N/A",
                    "data_arquivamento_sumarissimo_472": "",
                    "tem_ausencia_reclamante_473": "N/A",
                    "data_ausencia_reclamante_473": "",
                    "movimentos_detectados": ""
                })

        except Exception as e:
            print(f"❌ Erro ao processar processo {numero_processo}: {e}")

        time.sleep(0.5)  # evita sobrecarga na API

    # Gera planilha Excel com os resultados
    if resultados:
        df_resultados = pd.DataFrame(resultados)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"processos_transito_baixa_arquivamento_{timestamp}.xlsx"
        excel_out_path = os.path.join("F:/FGV-SJUR/resultado_transito_julgado", excel_filename)

        os.makedirs(os.path.dirname(excel_out_path), exist_ok=True)

        with pd.ExcelWriter(excel_out_path, engine="openpyxl") as writer:
            df_resultados.to_excel(writer, sheet_name="Resultados", index=False)

        print(f"📊 Planilha gerada com {len(resultados)} processos")
        print(f"💾 Arquivo salvo em: {excel_out_path}")

        return df_resultados
    else:
        print("📭 Nenhum resultado gerado")
        return None


def main():
    print("=" * 70)
    print("🔍 VERIFICAÇÃO DE TRÂNSITO/BAIXA/ARQUIVAMENTO - DATAJUD")
    print("=" * 70)

    if not os.getenv("DATAJUD_API_KEY"):
        os.environ["DATAJUD_API_KEY"] = "COLOQUE_SUA_CHAVE_AQUI"
        print("✅ API Key configurada")

    ## excel_path = r"F:\FGV-SJUR\sjur-poc-voila\data_analysis\Gerpro_Processos_Ativos_2025-09-26-20h39m.xlsx"
    excel_path = r"F:\FGV-SJUR\sjur-poc-voila\data_analysis\GERPRO-Ativos-2026-02-25.xlsx"
    resultados = verificar_baixa_arquivamento_transito(excel_path)

    if resultados is not None:
        print("\n📋 PREVIEW DOS RESULTADOS:")
        print(resultados.head().to_string(index=False))


if __name__ == "__main__":
    main()
