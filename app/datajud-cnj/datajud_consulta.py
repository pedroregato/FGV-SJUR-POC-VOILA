# datajud_consulta.py

from datetime import datetime
import requests
from collections import defaultdict
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
load_dotenv()



API_DOC_URL = "https://datajud-wiki.cnj.jus.br/api-publica/acesso"

# Mapeamento completo de todos os endpoints da DataJud
TRIBUNAIS = {
    # Tribunais Superiores
    "TST": "https://api-publica.datajud.cnj.jus.br/api_publica_tst/_search",
    "TSE": "https://api-publica.datajud.cnj.jus.br/api_publica_tse/_search",
    "STJ": "https://api-publica.datajud.cnj.jus.br/api_publica_stj/_search",
    "STM": "https://api-publica.datajud.cnj.jus.br/api_publica_stm/_search",

    # Tribunais Regionais Federais
    "TRF1": "https://api-publica.datajud.cnj.jus.br/api_publica_trf1/_search",
    "TRF2": "https://api-publica.datajud.cnj.jus.br/api_publica_trf2/_search",
    "TRF3": "https://api-publica.datajud.cnj.jus.br/api_publica_trf3/_search",
    "TRF4": "https://api-publica.datajud.cnj.jus.br/api_publica_trf4/_search",
    "TRF5": "https://api-publica.datajud.cnj.jus.br/api_publica_trf5/_search",
    "TRF6": "https://api-publica.datajud.cnj.jus.br/api_publica_trf6/_search",

    # Tribunais de Justiça Estaduais
    "TJAC": "https://api-publica.datajud.cnj.jus.br/api_publica_tjac/_search",
    "TJAL": "https://api-publica.datajud.cnj.jus.br/api_publica_tjal/_search",
    "TJAM": "https://api-publica.datajud.cnj.jus.br/api_publica_tjam/_search",
    "TJAP": "https://api-publica.datajud.cnj.jus.br/api_publica_tjap/_search",
    "TJBA": "https://api-publica.datajud.cnj.jus.br/api_publica_tjba/_search",
    "TJCE": "https://api-publica.datajud.cnj.jus.br/api_publica_tjce/_search",
    "TJDFT": "https://api-publica.datajud.cnj.jus.br/api_publica_tjdft/_search",
    "TJES": "https://api-publica.datajud.cnj.jus.br/api_publica_tjes/_search",
    "TJGO": "https://api-publica.datajud.cnj.jus.br/api_publica_tjgo/_search",
    "TJMA": "https://api-publica.datajud.cnj.jus.br/api_publica_tjma/_search",
    "TJMG": "https://api-publica.datajud.cnj.jus.br/api_publica_tjmg/_search",
    "TJMS": "https://api-publica.datajud.cnj.jus.br/api_publica_tjms/_search",
    "TJMT": "https://api-publica.datajud.cnj.jus.br/api_publica_tjmt/_search",
    "TJPA": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpa/_search",
    "TJPB": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpb/_search",
    "TJPE": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpe/_search",
    "TJPI": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpi/_search",
    "TJPR": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpr/_search",
    "TJRJ": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search",
    "TJRN": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrn/_search",
    "TJRO": "https://api-publica.datajud.cnj.jus.br/api_publica_tjro/_search",
    "TJRR": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrr/_search",
    "TJRS": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrs/_search",
    "TJSC": "https://api-publica.datajud.cnj.jus.br/api_publica_tjsc/_search",
    "TJSE": "https://api-publica.datajud.cnj.jus.br/api_publica_tjse/_search",
    "TJSP": "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search",
    "TJTO": "https://api-publica.datajud.cnj.jus.br/api_publica_tjto/_search",

    # Tribunais Regionais do Trabalho
    "TRT1": "https://api-publica.datajud.cnj.jus.br/api_publica_trt1/_search",
    "TRT2": "https://api-publica.datajud.cnj.jus.br/api_publica_trt2/_search",
    "TRT3": "https://api-publica.datajud.cnj.jus.br/api_publica_trt3/_search",
    "TRT4": "https://api-publica.datajud.cnj.jus.br/api_publica_trt4/_search",
    "TRT5": "https://api-publica.datajud.cnj.jus.br/api_publica_trt5/_search",
    "TRT6": "https://api-publica.datajud.cnj.jus.br/api_publica_trt6/_search",
    "TRT7": "https://api-publica.datajud.cnj.jus.br/api_publica_trt7/_search",
    "TRT8": "https://api-publica.datajud.cnj.jus.br/api_publica_trt8/_search",
    "TRT9": "https://api-publica.datajud.cnj.jus.br/api_publica_trt9/_search",
    "TRT10": "https://api-publica.datajud.cnj.jus.br/api_publica_trt10/_search",
    "TRT11": "https://api-publica.datajud.cnj.jus.br/api_publica_trt11/_search",
    "TRT12": "https://api-publica.datajud.cnj.jus.br/api_publica_trt12/_search",
    "TRT13": "https://api-publica.datajud.cnj.jus.br/api_publica_trt13/_search",
    "TRT14": "https://api-publica.datajud.cnj.jus.br/api_publica_trt14/_search",
    "TRT15": "https://api-publica.datajud.cnj.jus.br/api_publica_trt15/_search",
    "TRT16": "https://api-publica.datajud.cnj.jus.br/api_publica_trt16/_search",
    "TRT17": "https://api-publica.datajud.cnj.jus.br/api_publica_trt17/_search",
    "TRT18": "https://api-publica.datajud.cnj.jus.br/api_publica_trt18/_search",
    "TRT19": "https://api-publica.datajud.cnj.jus.br/api_publica_trt19/_search",
    "TRT20": "https://api-publica.datajud.cnj.jus.br/api_publica_trt20/_search",
    "TRT21": "https://api-publica.datajud.cnj.jus.br/api_publica_trt21/_search",
    "TRT22": "https://api-publica.datajud.cnj.jus.br/api_publica_trt22/_search",
    "TRT23": "https://api-publica.datajud.cnj.jus.br/api_publica_trt23/_search",
    "TRT24": "https://api-publica.datajud.cnj.jus.br/api_publica_trt24/_search"
}

# Códigos de movimentação de interesse
MOVIMENTACOES_INTERESSE = {
    22: "Baixa Definitiva",
    26: "Distribuição",
    380: "Citação",
    384: "Intimação",
    581: "Documento",
    848: "Trânsito em Julgado",
    861: "Arquivamento",
    981: "Recebimento",
    982: "Remessa",
    1051: "Decurso de Prazo",
    10456: "Arquivamento Definitivo",
    12284: "Citação",
    12286: "Citação Eletrônica",
    12289: "Cancelamento"
}

# Mapeamento de códigos de tribunal para detecção automática
CODIGOS_TRIBUNAIS = {
    # Justiça Federal (J = 4)
    '4': {
        '01': 'TRF1', '02': 'TRF2', '03': 'TRF3', '04': 'TRF4', '05': 'TRF5', '06': 'TRF6',
    },
    # Justiça do Trabalho (J = 5)
    '5': {
        '01': 'TRT1', '02': 'TRT2', '03': 'TRT3', '04': 'TRT4', '05': 'TRT5', '06': 'TRT6',
        '07': 'TRT7', '08': 'TRT8', '09': 'TRT9', '10': 'TRT10', '11': 'TRT11', '12': 'TRT12',
        '13': 'TRT13', '14': 'TRT14', '15': 'TRT15', '16': 'TRT16', '17': 'TRT17', '18': 'TRT18',
        '19': 'TRT19', '20': 'TRT20', '21': 'TRT21', '22': 'TRT22', '23': 'TRT23', '24': 'TRT24',
    },
    # Justiça Estadual (J = 8)
    '8': {
        '01': 'TJAP', '02': 'TJAC', '03': 'TJAM', '04': 'TJAL', '05': 'TJBA', '06': 'TJCE',
        '07': 'TJDFT', '08': 'TJES', '09': 'TJMT', '10': 'TJGO', '11': 'TJMG', '12': 'TJMS',
        '13': 'TJMA', '14': 'TJPA', '15': 'TJPB', '16': 'TJPR', '17': 'TJPE', '18': 'TJPI',
        '19': 'TJRJ', '20': 'TJRN', '21': 'TJRS', '22': 'TJRO', '23': 'TJRR', '24': 'TJSC',
        '25': 'TJSE', '26': 'TJSP', '27': 'TJTO',
    },
    # Exemplo para outros ramos, se necessário:
    '1': {'90': 'TST', '91': 'STM'},  # STF
    '2': {},  # CNJ
    '3': {'00': 'STJ'},  # Exemplo
    '6': {},  # Justiça Eleitoral
    '7': {},  # Justiça Militar da União
    '9': {},  # Justiça Militar Estadual
}

def carregar_api_key():
    return os.getenv("DATAJUD_API_KEY")

def atualizar_api_key_via_scraping():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        }
        resp = requests.get("https://datajud-wiki.cnj.jus.br/api-publica/acesso", headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        code_tags = soup.find_all("code")
        for tag in code_tags:
            if "APIKey" in tag.text:
                return tag.text.strip().split("APIKey ")[-1]
        print("⚠️ Tag <code> com APIKey não encontrada.")
    except Exception as e:
        print(f"❌ Falha ao tentar recuperar API Key do site: {e}")
    return None


def construir_headers(chave=None):
    if chave is None:
        chave = carregar_api_key()
    return {
        "Authorization": f"APIKey {chave}",
        "Content-Type": "application/json"
    }


def formatar_data(data_iso):
    """Formata data ISO para formato mais legível"""
    try:
        dt = datetime.fromisoformat(data_iso.replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return data_iso


def formatar_numero_cnj(numero_sem_mascara):
    """
    Formata o número do processo para o padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
    Exemplo: "10034691720244013400" -> "1003469-17.2024.4.01.3400"
    """
    if not numero_sem_mascara.isdigit() or len(numero_sem_mascara) != 20:
        raise ValueError("Número do processo deve ter 20 dígitos.")

    return (f"{numero_sem_mascara[:7]}-{numero_sem_mascara[7:9]}."
            f"{numero_sem_mascara[9:13]}.{numero_sem_mascara[13:14]}."
            f"{numero_sem_mascara[14:16]}.{numero_sem_mascara[16:]}")


def detectar_tribunal(numero_processo):
    """
    Detecta o tribunal a partir do número do processo no padrão CNJ (20 dígitos)
    Considera os campos J (justiça) e TR (tribunal)
    """
    numero_limpo = ''.join(filter(str.isdigit, numero_processo))
    if len(numero_limpo) < 16:
        return None

    justica = numero_limpo[13]
    codigo_tribunal = numero_limpo[14:16]

    return CODIGOS_TRIBUNAIS.get(justica, {}).get(codigo_tribunal)

def buscar_processo(numero_processo, tribunal=None):
    """
    Consulta a API DataJud e retorna o processo pelo número.
    Se o tribunal não for especificado, tenta detectar automaticamente.
    """
    if tribunal is None:
        tribunal = detectar_tribunal(numero_processo)
        if tribunal is None:
            print("❌ Não foi possível detectar o tribunal automaticamente.")
            return None

    if tribunal not in TRIBUNAIS:
        print(f"❌ Tribunal {tribunal} não suportado.")
        return None

    try:
        # Tenta com o número original (sem formatação)
        payload_original = {
            "query": {
                "match_phrase": {
                    "numeroProcesso": numero_processo
                }
            }
        }

        response = requests.post(
            TRIBUNAIS[tribunal],
            json=payload_original,
            headers=construir_headers(),
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Se não encontrar, tenta com o formato CNJ
        if data.get("hits", {}).get("total", {}).get("value", 0) == 0:
            numero_limpo = "".join(filter(str.isdigit, numero_processo))
            if len(numero_limpo) == 20:
                numero_cnj = formatar_numero_cnj(numero_limpo)
                payload_cnj = {
                    "query": {
                        "match_phrase": {
                            "numeroProcesso": numero_cnj
                        }
                    }
                }
                response = requests.post(
                    TRIBUNAIS[tribunal],
                    json=payload_cnj,
                    headers=construir_headers(),
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

        if data.get("hits", {}).get("total", {}).get("value", 0) > 0:
            return data["hits"]["hits"][0]["_source"]
        else:
            print("⚠️ Processo não encontrado (tentado ambos os formatos).")
            return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [401, 403]:
            print(f"❌ Erro de autenticação (HTTP {e.response.status_code}).")
            print("🔑 Verifique se sua API Key está correta.")
            print("📎 Você pode obter a nova chave em: https://datajud-wiki.cnj.jus.br/api-publica/acesso")
        else:
            print(f"❌ Erro HTTP: {e}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
        return None

    except ValueError as e:
        print(f"❌ Erro no formato do número: {e}")
        return None

def filtrar_movimentacoes(processo, agrupar=True, data_inicio=None, data_fim=None):
    """
    Filtra movimentações de interesse e opcionalmente as agrupa.
    """
    if not processo or "movimentos" not in processo:
        return None

    movimentos = processo["movimentos"]


    # Filtra por código de interesse
    movs_filtradas = [
        mov for mov in movimentos
        if mov["codigo"] in MOVIMENTACOES_INTERESSE
    ]

    # Filtra por data se fornecido
    if data_inicio or data_fim:
        try:
            dt_inicio = datetime.fromisoformat(data_inicio) if data_inicio else None
            dt_fim = datetime.fromisoformat(data_fim) if data_fim else None
        except ValueError:
            print("❌ Formato de data inválido. Use YYYY-MM-DD.")
            return None

        movs_filtradas = [
            mov for mov in movs_filtradas
            if (not dt_inicio or mov["dataHora"] >= dt_inicio.isoformat()) and
               (not dt_fim or mov["dataHora"] <= dt_fim.isoformat())
        ]

    if not agrupar:
        return movs_filtradas

    # Agrupa movimentações por tipo
    movs_agrupadas = defaultdict(list)
    print(movs_agrupadas)
    for mov in movs_filtradas:
        descricao = MOVIMENTACOES_INTERESSE[mov["codigo"]]
        movs_agrupadas[descricao].append({
            "data": mov["dataHora"],
            "nome": mov.get("nome", "")
        })

    return movs_agrupadas


def formatar_valor_monetario(valor):
    """
    Formata valores monetários de diferentes formatos para um padrão
    """
    if valor is None:
        return None

    if isinstance(valor, (int, float)):
        return valor

    if isinstance(valor, str):
        # Remove símbolos e formatação
        valor_limpo = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(valor_limpo)
        except ValueError:
            return None

    return None


def obter_valor_causa(processo):
    """
    Extrai e formata o valor da causa do processo com tratamento robusto
    """
    if not processo:
        return None

    # Padrão 1 - Valor direto no objeto principal
    if 'valorCausa' in processo:
        valor = formatar_valor_monetario(processo['valorCausa'])
        moeda = processo.get('moeda', 'BRL')
        return {'valor': valor, 'moeda': moeda} if valor is not None else None

    # Padrão 2 - Objeto aninhado em dadosProcesso
    if 'dadosProcesso' in processo and 'valorCausa' in processo['dadosProcesso']:
        valor = formatar_valor_monetario(processo['dadosProcesso']['valorCausa'])
        moeda = processo['dadosProcesso'].get('moeda', 'BRL')
        return {'valor': valor, 'moeda': moeda} if valor is not None else None

    # Padrão 3 - Em campos alternativos
    campos_alternativos = ['valorAcao', 'valorOriginal', 'valorAtualizado']
    for campo in campos_alternativos:
        if campo in processo:
            valor = formatar_valor_monetario(processo[campo])
            if valor is not None:
                return {'valor': valor, 'moeda': processo.get('moeda', 'BRL')}

    return None


def formatar_valor_para_exibicao(valor_info):
    """
    Formata o valor para exibição amigável
    """
    if not valor_info or valor_info.get('valor') is None:
        return "Não informado"

    valor = valor_info['valor']
    moeda = valor_info.get('moeda', 'BRL')

    try:
        # Formata como moeda brasileira por padrão
        if moeda.upper() == 'BRL':
            return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"{valor:,.2f} {moeda}"
    except:
        return str(valor)


def exibir_resultados(processo, limite_movs=10, data_inicio=None, data_fim=None):
    """
    Exibe os dados do processo e movimentações formatadas.
    """
    if not processo:
        return

    print(f"\n📄 Processo: {processo.get('numeroProcesso', 'N/A')}")
    print(f"🏛️ Tribunal: {processo.get('tribunal', 'N/A')}")
    print(f"📌 Classe: {processo.get('classe', {}).get('nome', 'N/A')}")
    # Exibir valor da causa
    valor_causa = obter_valor_causa(processo)
    print(f"💰 Valor da causa: {formatar_valor_para_exibicao(valor_causa)}")
    print(f"📅 Data de Ajuizamento: {formatar_data(processo.get('dataAjuizamento', 'N/A'))}")

    movs_agrupadas = filtrar_movimentacoes(
        processo,
        agrupar=True,
        data_inicio=data_inicio,
        data_fim=data_fim
    )

    if not movs_agrupadas:
        print("\n❌ Nenhuma movimentação de interesse encontrada.")
        return

    print("\n🔍 Movimentações de interesse:")
    for descricao, eventos in movs_agrupadas.items():
        print(f"\n  {descricao} ({len(eventos)} ocorrências):")
        for evento in eventos[:limite_movs]:
            print(f"    - {formatar_data(evento['data'])}")
            if evento['nome']:
                print(f"      {evento['nome']}")
        if len(eventos) > limite_movs:
            print(f"    ... ({len(eventos) - limite_movs} ocultas)")

def exibir_detalhes_adicionais(processo):
    if not processo:
        print("❌ Nenhum dado disponível para exibir detalhes adicionais.")
        return

    print("\n📘 Detalhes adicionais:")

    # Sistema
    sistema = processo.get('sistema', {}).get('nome', 'N/A')
    print(f"💻 Sistema de tramitação: {sistema}")

    # Formato
    formato = processo.get('formato', {}).get('nome', 'N/A')
    print(f"📁 Formato do processo: {formato}")

    # Grau
    grau = processo.get('grau', 'N/A')
    print(f"📈 Grau de jurisdição: {grau}")

    # Órgão julgador
    orgao = processo.get('orgaoJulgador', {}).get('nome', 'N/A')
    print(f"⚖️ Órgão julgador: {orgao}")

    # Sigilo
    sigilo = processo.get('nivelSigilo', 0)
    visibilidade = 'Público' if sigilo == 0 else f'Sigiloso (nível {sigilo})'
    print(f"🔐 Nível de sigilo: {visibilidade}")

    # Assuntos
    assuntos = processo.get('assuntos', [])
    if assuntos:
        print("🧾 Assuntos:")
        for a in assuntos:
            print(f"  - {a['nome']} (código: {a['codigo']})")

    # Exibir partes
    print("\n👥 Partes do processo:")
    polo_ativo = processo.get('poloAtivo', [])
    polo_passivo = processo.get('poloPassivo', [])

    if polo_ativo:
        print("  🔷 Ativo(s):")
        for parte in polo_ativo:
            print(f"    - {parte.get('nome', 'N/A')}")

    if polo_passivo:
        print("  🔶 Passivo(s):")
        for parte in polo_passivo:
            print(f"    - {parte.get('nome', 'N/A')}")

    if not polo_ativo and not polo_passivo:
        print("  ❌ Nenhuma parte identificada.")



if __name__ == "__main__":
    # numero_teste = "10081440420254010000"
    # numero_teste = "08439288620258190001"
    # numero_teste = "08117584020258190202"
    # numero_teste = "08557333620258190001"
    numero_teste = "08319230620248190021"

    print("\n🔍 Buscando com tribunal automático...")
    processo = buscar_processo(numero_teste)
    exibir_resultados(processo, limite_movs=150)
    exibir_detalhes_adicionais(processo)  # agora está seguro mesmo se processo=None
