import pandas as pd
import datetime
import os

ARQUIVO_AVALIACOES = 'avaliacoes/avaliacoes_poc.csv'

def inicializar_base_avaliacoes():
    if not os.path.exists('avaliacoes'):
        os.makedirs('avaliacoes')
    if not os.path.exists(ARQUIVO_AVALIACOES):
        df_init = pd.DataFrame(columns=['Data', 'Texto', 'Classificacao', 'Metadados', 'Avaliador_Concorda', 'Observacao'])
        df_init.to_csv(ARQUIVO_AVALIACOES, index=False)

def registrar_avaliacao(texto, classificacao, metadados, concorda, observacao):
    df = pd.read_csv(ARQUIVO_AVALIACOES)
    nova_linha = {
        'Data': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Texto': texto,
        'Classificacao': classificacao,
        'Metadados': str(metadados),
        'Avaliador_Concorda': concorda,
        'Observacao': observacao
    }
    df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
    df.to_csv(ARQUIVO_AVALIACOES, index=False)
