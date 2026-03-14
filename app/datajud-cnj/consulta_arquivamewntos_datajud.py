import pandas as pd
import json
from datetime import datetime
import os
import re
import datajud_consulta_manus


def verificar_processos_arquivados():
    """
    Lê o dashboard_data.json, consulta processos no Datajud e verifica se têm
    movimentações de Baixa Definitiva ou Arquivamento Definitivo
    """

    # Caminho do arquivo JSON
    json_path = "F:/FGV-SJUR/resultado_arquivamento/json/dashboard_data.json"

    # Verifica se o arquivo existe
    if not os.path.exists(json_path):
        print(f"❌ Arquivo não encontrado: {json_path}")
        return None

    try:
        # Carrega os dados do dashboard
        with open(json_path, 'r', encoding='utf-8') as f:
            dashboard_data = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar JSON: {e}")
        return None

    # Extrai todos os processos únicos (arquivamento + não arquivamento)
    processos_unicos = set()
    processos_unicos.update(dashboard_data.get('unique_archival_processes', []))
    processos_unicos.update(dashboard_data.get('unique_non_archival_processes', []))

    print(f"📊 Total de processos únicos encontrados: {len(processos_unicos)}")

    # Filtra apenas processos com formato CNJ válido (20 dígitos)
    processos_cnj_validos = []
    for processo in processos_unicos:
        # Remove caracteres não numéricos e verifica se tem 20 dígitos
        numero_limpo = re.sub(r'[^\d]', '', str(processo))
        if len(numero_limpo) == 20:
            processos_cnj_validos.append(numero_limpo)
        else:
            print(f"⚠️  Processo ignorado (formato inválido): {processo}")

    print(f"✅ Processos CNJ válidos para consulta: {len(processos_cnj_validos)}")

    # Inicializa a classe de consulta Datajud
    consulta = datajud_consulta_manus.DatajudConsultaEnriquecida()

    # Lista para armazenar resultados
    resultados = []

    # Consulta cada processo
    for i, numero_processo in enumerate(processos_cnj_validos, 1):
        print(f"🔍 Consultando processo {i}/{len(processos_cnj_validos)}: {numero_processo}")

        try:
            # Consulta o processo na API Datajud
            resultado = consulta.consultar_processo_enriquecido(numero_processo)

            if resultado["sucesso"]:
                processo_data = resultado["processo"]
                movimentacoes = processo_data["movimentacoes"]

                # Verifica se tem movimentações de interesse (Baixa Definitiva ou Arquivamento Definitivo)
                tem_baixa_definitiva = False
                tem_arquivamento_definitivo = False
                datas_movimentacoes = []

                # Analisa cada movimentação
                for mov in movimentacoes.get('movimentacoes', []):
                    codigo = mov.get('codigo')
                    if codigo == 22:  # Baixa Definitiva
                        tem_baixa_definitiva = True
                        datas_movimentacoes.append({
                            'tipo': 'Baixa Definitiva',
                            'data': mov.get('data_formatada', ''),
                            'data_iso': mov.get('data_hora', '')
                        })
                    elif codigo == 10456:  # Arquivamento Definitivo
                        tem_arquivamento_definitivo = True
                        datas_movimentacoes.append({
                            'tipo': 'Arquivamento Definitivo',
                            'data': mov.get('data_formatada', ''),
                            'data_iso': mov.get('data_hora', '')
                        })
                    elif codigo == 848:  # Arquivamento Definitivo
                        tem_arquivamento_definitivo = True
                        datas_movimentacoes.append({
                            'tipo': 'Trânsito em Julgado',
                            'data': mov.get('data_formatada', ''),
                            'data_iso': mov.get('data_hora', '')
                        })

                # Só inclui no resultado se tiver pelo menos uma das movimentações desejadas
                if tem_baixa_definitiva or tem_arquivamento_definitivo:
                    # Extrai informações básicas do processo
                    info_processo = {
                        'numero_processo': processo_data['identificacao']['numero_processo'],
                        'tribunal': processo_data['identificacao']['tribunal'],
                        'grau': processo_data['identificacao']['grau'],
                        'classe': processo_data['classificacao']['classe'].get('nome', 'N/A'),
                        'assunto_principal': processo_data['classificacao']['assuntos'][0].get('nome', 'N/A') if
                        processo_data['classificacao']['assuntos'] else 'N/A',
                        'data_ajuizamento': processo_data['timestamps']['data_ajuizamento_formatada'],
                        'orgao_julgador': processo_data['orgao_julgador']['nome'],
                        'municipio': processo_data['orgao_julgador']['municipio']['nome'],
                        'tem_baixa_definitiva': 'Sim' if tem_baixa_definitiva else 'Não',
                        'tem_arquivamento_definitivo': 'Sim' if tem_arquivamento_definitivo else 'Não',
                        'total_movimentacoes': movimentacoes.get('total', 0),
                        'ultima_atualizacao': processo_data['timestamps']['ultima_atualizacao_formatada']
                    }

                    # Adiciona informações das movimentações específicas
                    if datas_movimentacoes:
                        # Ordena por data (mais recente primeiro)
                        datas_movimentacoes.sort(key=lambda x: x['data_iso'] or '', reverse=True)
                        info_processo['ultima_movimentacao_arquivamento'] = datas_movimentacoes[0]['data']
                        info_processo['tipo_ultima_movimentacao'] = datas_movimentacoes[0]['tipo']

                    resultados.append(info_processo)
                    print(f"✅ Processo {numero_processo} - ENCONTRADO movimentações de arquivamento")
                else:
                    print(f"⚠️  Processo {numero_processo} - SEM movimentações de arquivamento")
            else:
                print(f"❌ Erro na consulta do processo {numero_processo}: {resultado['erro']}")

        except Exception as e:
            print(f"❌ Erro ao processar processo {numero_processo}: {e}")

        # Pequena pausa para não sobrecarregar a API
        import time
        time.sleep(0.5)

    # Gera planilha Excel se houver resultados
    if resultados:
        # Cria DataFrame
        df = pd.DataFrame(resultados)

        # Ordena por data da última movimentação (mais recente primeiro)
        if 'ultima_movimentacao_arquivamento' in df.columns:
            df = df.sort_values('ultima_movimentacao_arquivamento', ascending=False)

        # Nome do arquivo Excel com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"processos_arquivados_{timestamp}.xlsx"
        excel_path = f"F:/FGV-SJUR/resultado_arquivamento/{excel_filename}"

        # Garante que o diretório existe
        os.makedirs(os.path.dirname(excel_path), exist_ok=True)

        # Salva em Excel
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Processos Arquivados', index=False)

            # Formatação da planilha
            workbook = writer.book
            worksheet = writer.sheets['Processos Arquivados']

            # Ajusta largura das colunas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        print(f"📊 Planilha gerada com {len(resultados)} processos arquivados")
        print(f"💾 Arquivo salvo em: {excel_path}")

        # Exibe resumo
        print("\n" + "=" * 60)
        print("📈 RESUMO DA ANÁLISE:")
        print(f"Total de processos analisados: {len(processos_cnj_validos)}")
        print(f"Processos com movimentações de arquivamento: {len(resultados)}")
        print(f"Com Baixa Definitiva: {len([r for r in resultados if r['tem_baixa_definitiva'] == 'Sim'])}")
        print(
            f"Com Arquivamento Definitivo: {len([r for r in resultados if r['tem_arquivamento_definitivo'] == 'Sim'])}")
        print("=" * 60)

        return df
    else:
        print("📭 Nenhum processo com movimentações de arquivamento encontrado")
        return None


# Função principal para executar a análise
def main():
    """
    Função principal que orquestra toda a análise
    """
    print("=" * 70)
    print("🔍 ANALISADOR DE PROCESSOS ARQUIVADOS - DATAJUD")
    print("=" * 70)

    # Verifica se a API key está configurada
    if not os.getenv('DATAJUD_API_KEY'):
        os.environ['DATAJUD_API_KEY'] = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
        print("✅ API Key configurada")

    # Executa a análise
    resultados = verificar_processos_arquivados()

    if resultados is not None:
        # Exibe preview dos dados
        print("\n📋 PREVIEW DOS RESULTADOS:")
        print(resultados.head().to_string(index=False))

    return resultados


if __name__ == "__main__":
    # Executa a análise quando o script é rodado diretamente
    main()