import requests
from typing import Optional

BASE_URL = "https://datajud.cnj.jus.br/api/public/processos"


def consultar_datajud(numero_processo: str) -> Optional[dict]:
    """
    Consulta a API pública do DataJud usando o número do processo CNJ.
    Retorna os dados brutos do processo, ou None se não encontrado.
    """
    try:
        params = {"numeroProcesso": numero_processo}
        response = requests.get(BASE_URL, params=params, timeout=10)

        if response.status_code == 200:
            resultados = response.json()
            if isinstance(resultados, list) and resultados:
                return resultados[0]  # Primeiro processo encontrado
            elif isinstance(resultados, dict):
                return resultados
            return None
        else:
            print(f"⚠️ Erro ao consultar DataJud: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Erro na requisição ao DataJud: {str(e)}")
        return None


def enriquecer_metadados(numero_processo: str) -> Optional[dict]:
    """
    Enriquecimento de metadados com base na consulta ao DataJud.
    Retorna dicionário com UF, tribunal, classe, assunto principal, partes e datas.
    """
    dados = consultar_datajud(numero_processo)
    if not dados:
        return None

    try:
        return {
            "numero_processo": numero_processo,
            "tribunal": dados.get("tribunal", {}).get("nome"),
            "classe": dados.get("classe", {}).get("nome"),
            "assunto": dados.get("assuntos", [{}])[0].get("nome"),
            "orgao_julgador": dados.get("orgaoJulgador", {}).get("nome"),
            "unidade_judiciaria": dados.get("unidadeJudiciaria", {}).get("nome"),
            "data_distribuicao": dados.get("dataDistribuicao"),
            "data_transito_julgado": dados.get("dataTransitoJulgado"),
            "partes": [
                {
                    "nome": parte.get("nome"),
                    "tipo": parte.get("tipo"),
                    "polo": parte.get("polo")
                }
                for parte in dados.get("partes", [])
            ]
        }
    except Exception as e:
        print(f"❌ Erro ao processar dados do DataJud: {str(e)}")
        return None


# 🔍 Teste manual
if __name__ == "__main__":
    from pprint import pprint

    processo_exemplo = "0105200-95.2005.5.21.0006"
    print(f"🔎 Consultando processo {processo_exemplo} no DataJud...")

    resultado = enriquecer_metadados(processo_exemplo)

    if resultado:
        print("✅ Metadados enriquecidos:")
        pprint(resultado)
    else:
        print("❌ Processo não encontrado ou erro na consulta.")
