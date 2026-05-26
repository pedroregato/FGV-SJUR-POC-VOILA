import pandas as pd
import os
import re
from datetime import datetime
import time
import datajud_consulta_manus  # sua classe de consulta já existente


def verificar_transito_em_julgado(excel_path):
    """
    Lê planilha Excel com processos (coluna B), consulta no Datajud
    e verifica se houve movimentação de Trânsito em Julgado.
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

    # Consulta cada processo
    for i, numero_processo in enumerate(processos_cnj_validos, 1):
        print(f"🔍 Consultando processo {i}/{len(processos_cnj_validos)}: {numero_processo}")

        try:
            resultado = consulta.consultar_processo_enriquecido(numero_processo)

            if resultado["sucesso"]:
                processo_data = resultado["processo"]
                movimentacoes = processo_data["movimentacoes"]

                tem_transito = False
                data_transito = None

                # Analisa movimentações
                for mov in movimentacoes.get("movimentacoes", []):
                    codigo = mov.get("codigo")
                    if codigo == 848:  # Trânsito em Julgado
                        tem_transito = True
                        data_transito = mov.get("data_formatada", "")
                        break

                info_processo = {
                    "numero_processo": processo_data["identificacao"]["numero_processo"],
                    "tribunal": processo_data["identificacao"]["tribunal"],
                    "grau": processo_data["identificacao"]["grau"],
                    "classe": processo_data["classificacao"]["classe"].get("nome", "N/A"),
                    "assunto_principal": processo_data["classificacao"]["assuntos"][0].get("nome", "N/A")
                        if processo_data["classificacao"]["assuntos"] else "N/A",
                    "data_ajuizamento": processo_data["timestamps"]["data_ajuizamento_formatada"],
                    "orgao_julgador": processo_data["orgao_julgador"]["nome"],
                    "municipio": processo_data["orgao_julgador"]["municipio"]["nome"],
                    "tem_transito_em_julgado": "Sim" if tem_transito else "Não",
                    "data_transito_em_julgado": data_transito or "",
                    "total_movimentacoes": movimentacoes.get("total", 0),
                    "ultima_atualizacao": processo_data["timestamps"]["ultima_atualizacao_formatada"],
                    "encontrado_na_api": "Sim"
                }

                resultados.append(info_processo)

                if tem_transito:
                    print(f"✅ Processo {numero_processo} - TRÂNSITO EM JULGADO encontrado")
                else:
                    print(f"⚠️ Processo {numero_processo} - SEM trânsito em julgado")
            else:
                print(f"❌ Processo {numero_processo} não encontrado na API")
                resultados.append({
                    "numero_processo": numero_processo,
                    "encontrado_na_api": "Não",
                    "tem_transito_em_julgado": "N/A",
                    "data_transito_em_julgado": ""
                })

        except Exception as e:
            print(f"❌ Erro ao processar processo {numero_processo}: {e}")

        time.sleep(0.5)  # evita sobrecarga na API

    # Gera planilha Excel com os resultados
    if resultados:
        df_resultados = pd.DataFrame(resultados)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"processos_transito_julgado_{timestamp}.xlsx"
        excel_path = os.path.join("F:/FGV-SJUR/resultado_transito_julgado", excel_filename)

        os.makedirs(os.path.dirname(excel_path), exist_ok=True)

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_resultados.to_excel(writer, sheet_name="Resultados", index=False)

        print(f"📊 Planilha gerada com {len(resultados)} processos")
        print(f"💾 Arquivo salvo em: {excel_path}")

        return df_resultados
    else:
        print("📭 Nenhum resultado gerado")
        return None


def main():
    print("=" * 70)
    print("🔍 VERIFICAÇÃO DE TRÂNSITO EM JULGADO - DATAJUD")
    print("=" * 70)

    if not os.getenv("DATAJUD_API_KEY"):
        os.environ["DATAJUD_API_KEY"] = "COLOQUE_SUA_CHAVE_AQUI"
        print("✅ API Key configurada")

    excel_path = r"F:\FGV-SJUR\sjur-poc-voila\data_analysis\Gerpro_Processos_Ativos_2025-09-26-20h39m.xlsx"
    resultados = verificar_transito_em_julgado(excel_path)

    if resultados is not None:
        print("\n📋 PREVIEW DOS RESULTADOS:")
        print(resultados.head().to_string(index=False))


if __name__ == "__main__":
    main()
