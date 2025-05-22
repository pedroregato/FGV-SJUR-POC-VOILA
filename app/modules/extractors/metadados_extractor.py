import os
import re
import json
import requests
from dotenv import load_dotenv
import logging
from typing import Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis do .env
load_dotenv()

# Configurações do LLM
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_MODEL = "deepseek-chat"
LLM_TIMEOUT = 60

DEEPSEEK_PROMPT_METADADOS = """
Extraia os seguintes campos do texto da publicação:

- orgao
- comarca
- classe
- data_publicacao
- unidade_fgv
- obrigacoes: uma lista com todas as frases que expressem ordens, determinações ou obrigações (ex: verbos no imperativo como "Recolha", "Apresente", "Cumpra-se", "Cite-se")
- justificativa_unidade_fgv: uma breve explicação textual sobre por que a unidade_fgv foi determinada.
- decisao: uma lista com todas as frases que expressem decisões por parte da autoridade judical (ex: locuções verbais como "Sentencio", "Decido", "Arquive-se", "Julgo", "Considero", "Sentencio")

⚠️ Atenção: A unidade_fgv deve ser definida como "FGV Conhecimento" **somente se** uma das palavras **exatas** — "certame", "gabarito" ou "concurso" — estiver presente no texto. 

❌ Palavras parecidas ou relacionadas (como "certidão", "certificado", "edital") **não** devem ser consideradas.

Se nenhuma dessas 3 palavras estiver presente, defina unidade_fgv como "" (vazio), e diga isso claramente na justificativa.

A data deve estar no formato YYYY-MM-DD. 
Retorne apenas JSON com os 7 campos indicados, mesmo se algum estiver em branco ou a lista estiver vazia.


Definições:
- Decisão judicial: Uma decisão judicial é a resposta oficial de um juiz ou tribunal a um processo, 
baseada nas leis, nos fatos apresentados e em precedentes jurídicos. 
Ela pode determinar direitos, resolver conflitos e estabelecer obrigações entre as partes envolvidas. 


"""


def parse_numero_processo(numero_processo: str) -> dict:
    """
    Valida e extrai informações do número de processo no formato CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
    Retorna dicionário com número formatado, UF e tribunal (nome padrão CNJ: 'TRF1', 'TJSP', etc.)
    """

    padrao = r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$"
    match = re.match(padrao, numero_processo)
    if not match:
        raise ValueError("Formato inválido. Esperado: NNNNNNN-DD.AAAA.J.TR.OOOO")

    sequencial, digito, ano, justica_id, tribunal_id, orgao_cnj = match.groups()
    uf_codigo = tribunal_id
    orgao_local = orgao_cnj[2:]  # opcional

    # Mapeamento CNJ para UF (simplificado)
    ufs = {
        "01": "AC", "02": "AL", "03": "AP", "04": "AM", "05": "BA",
        "06": "CE", "07": "DF", "08": "ES", "09": "GO", "10": "MA",
        "11": "MT", "12": "MS", "13": "MG", "14": "PA", "15": "PB",
        "16": "PR", "17": "PE", "18": "PI", "19": "RJ", "20": "RN",
        "21": "RS", "22": "RO", "23": "RR", "24": "SC", "25": "SP",
        "26": "SE", "27": "TO"
    }

    # Mapeamento unificado para tribunais
    codigos_tribunais = {
        # Justiça Federal
        "01": "TRF1", "02": "TRF2", "03": "TRF3", "04": "TRF4", "05": "TRF5", "06": "TRF6",

        # Justiça Estadual
        "14": "TJPA", "15": "TJPB", "16": "TJPR", "17": "TJPE", "18": "TJPI", "19": "TJRJ",
        "20": "TJRN", "21": "TJRS", "22": "TJRO", "23": "TJRR", "24": "TJSC", "25": "TJSP",
        "26": "TJSE", "27": "TJTO", "11": "TJMT", "12": "TJMS", "13": "TJMG", "10": "TJMA",
        "09": "TJGO", "08": "TJES", "07": "TJDFT", "06": "TJCE", "05": "TJBA", "04": "TJAL",
        "03": "TJAM", "02": "TJAC", "01": "TJAP",

        # Justiça do Trabalho
        "91": "TRT1", "92": "TRT2", "93": "TRT3", "94": "TRT4", "95": "TRT5", "96": "TRT6",
        "97": "TRT7", "98": "TRT8", "99": "TRT9", "90": "TRT10",  # exemplo extra, adaptar conforme necessidade
    }

    tribunal = codigos_tribunais.get(tribunal_id, "Desconhecido")
    uf = ufs.get(uf_codigo, "Desconhecido")

    return {
        "numero_processo": numero_processo,
        "uf": uf,
        "tribunal": tribunal
    }


def contar_ocorrencias_igpm(texto: str) -> int:
    padrao = r"\bIGP[- ]?M\b"
    return len(re.findall(padrao, texto, flags=re.IGNORECASE))

def extrair_conteudo_publicado_regex(texto: str) -> str:
    match = re.search(r"(?i)conte[uú]do:\s*(.*)", texto)
    if match:
        return match.group(1).strip()
    return "indeterminado"

def extrair_metadados_publicacao(texto: str) -> Optional[dict]:

    if not isinstance(texto, str):
        logger.error(f"Texto inválido - não é str — :{texto} - {type(texto)}")
        return None

    if not texto.strip():
        logger.error(f"Texto inválido — não está em strip - :{texto}")
        return None

    if not DEEPSEEK_API_KEY:
        logger.error("Chave da API (DEEPSEEK_API_KEY) não configurada.")
        return None

    match = re.search(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", texto)
    numero_processo = match.group(0) if match else None

    if not numero_processo:
        logger.warning("Número do processo não encontrado no texto.")
        return None

    info_processo = parse_numero_processo(numero_processo)
    contador_igpm = contar_ocorrencias_igpm(texto)
    conteudo_publicado = extrair_conteudo_publicado_regex(texto)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": DEEPSEEK_PROMPT_METADADOS},
            {"role": "user", "content": texto[:10000]}
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=LLM_TIMEOUT
        )
        response.raise_for_status()
        resposta = response.json()

        conteudo = resposta['choices'][0]['message']['content']
        try:
            dados_llm = json.loads(conteudo)
        except json.JSONDecodeError as e:
            logger.error(f"Falha ao decodificar JSON retornado pela LLM: {e}\nConteúdo recebido:\n{conteudo}")
            return None

        resultado = {
            "numero_processo": info_processo["numero_processo"],
            "tribunal": info_processo["tribunal"],
            "uf": info_processo["uf"],
            "igpm_count": contador_igpm,
            "conteudo_publicado": conteudo_publicado,
            **dados_llm
        }

        return resultado

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.error(f"Erro na requisição ou no processamento: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        return None

if __name__ == "__main__":
    texto_exemplo = """
Publicacao Processo: 1018462-83.2025.4.01.3900 Orgao: 2ª Vara Federal Civel da SJPA Data de disponibilizacao: 20/05/2025 Tipo de comunicacao: Intimacao Meio: Diario de Justica Eletronico Nacional Inteiro teor: https://pje1g.trf1.jus.br:443/pje/Processo/ConsultaDocumento/listView.seam?x=25051912111494200000024420348 Parte: RAUL LUIZ ESTEVES DO COUTO Advogado: GUSTAVO REIS CALVO - OAB PA-40151 Conteudo: PODER JUDICIARIO JUSTICA FEDERAL Secao Judiciaria do Para 2ª Vara Federal Civel da SJPA PROCESSO: 1018462-83.2025.4.01.3900 CLASSE: MANDADO DE SEGURANCA CIVEL (120) POLO ATIVO: RAUL LUIZ ESTEVES DO COUTO REPRESENTANTES POLO ATIVO: GUSTAVO REIS CALVO - PA40151 POLO PASSIVO:CARLOS IVAN SIMONSEN LEAL - PRESIDENTE DA FUNDACAO GETULIO VARGAS - FGV e outros DECISAO Trata-se de mandado de seguranca impetrado por RAUL LUIZ ESTEVES DO COUTO contra atos atribuidos ao PRESIDENTE DA ORDEM DOS ADVOGADOS DO BRASIL - SECCIONAL PARA e ao PRESIDENTE DA FUNDACAO GETULIO VARGAS (FGV), objetivando a revisao de nota atribuida na prova pratico-profissional do 42º Exame de Ordem Unificado, com pedido de liminar para que seja determinada a correcao da nota, passando a 6,1 pontos, com inclusao do nome na lista de aprovados, O impetrante sustenta que, embora tenha sido atribuida a ele nota final de 5,5, sua resposta a questao 4.a estaria em conformidade com o gabarito oficial, sendo indevidamente desconsiderada a pontuacao de 0,6 pontos. Alega violacao a direito liquido e certo, por erro material e ausencia de fundamentacao adequada por parte da banca examinadora, mencionando os principios constitucionais da legalidade, ampla defesa, contraditorio e motivacao dos atos administrativos, bem como a Sumula 473 do STF. Requereu ainda a concessao de gratuidade da justica. DECIDO. A concessao de medida liminar, em sede de mandado de seguranca, pressupoe que se facam presentes os seguintes requisitos, a teor do art. 7º, III da Lei Federal nº 12.016/2009: a relevancia dos fundamentos (fumus boni iuris) e o risco de que do ato impugnado possa resultar a ineficacia da medida, caso seja finalmente deferida (periculum in mora). Exige-se ainda, para a concessao da tutela de urgencia nesta via processual, a presenca da prova pre-constituida dos fatos que fundamentam a pretensao de direito material, o qual devera restar de plano comprovado, sob pena de indeferimento. Em se tratando de materia relativa a aplicacao e correcao de provas de concursos/exames, a intervencao do Poder Judiciario afigura-se limitada as situacoes em que seja notoria a ilegalidade, o abuso de poder, ou o erro material presente na formulacao ou correcao das questoes, uma vez que nos termos do Tema 485 do STF "Os criterios adotados por banca examinadora de um concurso nao podem ser revistos pelo Poder Judiciario." Trata-se portanto, de intervencao excepcionalissima, uma vez que a jurisprudencia do Colendo Supremo Tribunal Federal e a do Egregio Superior Tribunal de Justica e clara ao delimitar que o Judiciario nao pode substituir a banca examinadora na avaliacao dos criterios de correcao ou na formulacao das questoes, salvo nas seguintes circunstancias: 1. Erro material na correcao da prova; 2. Incompatibilidade com o edital, onde a questao diverge das regras previamente estabelecidas; 3. Ambiguidade ou falta de clareza que prejudique a correta interpretacao da questao; e 4. Violacao a isonomia ou criterios de avaliacao inconsistentes. A autonomia das bancas examinadoras e a regra, autorizando-se o controle de legalidade pelo Judiciario tao-somente nas circunstancias ao norte citadas, e desde que comprovadas de plano. Assim, em se tratando de erro material evidente, seja na elaboracao da questao, ou na sua correcao, e cabivel a intervencao judicial, afastando-se a Tese 485 firmada pela Suprema Corte. Nesse sentido, os seguintes julgados do proprio STF: AGRAVO INTERNO. RECURSO EXTRAORDINARIO. CONCURSO PUBLICO. ANULACAO DE QUESTAO DE PROVA POR CONTA DE ERRO MATERIAL. TEMA 485 DA REPERCUSSAO GERAL. INAPLICABILIDADE. CONTROLE DE LEGALIDADE. ATO ADMINISTRATIVO. INTERVENCAO DO PODER JUDICIARIO. POSSIBILIDADE. 1. Na hipotese em exame, nao se trata da discussao sobre o Poder Judiciario substituir o examinador do certame publico na escolha dos criterios de correcao. Diversamente, trata-se de causa em que o Tribunal de origem comprovou, de forma inequivoca, a existencia de erro material no enunciado da questao considerada correta, induzindo o candidato a equivoco, uma vez que indica dispositivo legal completamente estranho ao objeto avaliado. 2. Dessa forma, sendo inconteste a existencia de erro material na questao de concurso publico, tem-se que, de fato, o Tema 485 da repercussao geral nao se aplica ao caso destes autos. 3. A jurisprudencia desta SUPREMA CORTE e firme no sentido da possibilidade de o Poder Judiciario realizar o controle de atos administrativos ilegais ou abusivos. 4. Agravo Interno a que se nega provimento. (RE 1030329 AgR; Orgao julgador: Primeira Turma; Relator(a): Min. ALEXANDRE DE MORAES; Publicacao: 14/10/2022) AGRAVO REGIMENTAL. SUSPENSAO DE LIMINAR.CONCURSO PUBLICO. ERRO MATERIAL NA CORRECAO DA PROVA. AUSENCIA DE RISCO DE LESAO A ORDEM E A ECONOMIA PUBLICAS.AGRAVO A QUE SE NEGA PROVIMENTO.I - Nao constatado o risco de lesao a ordem e a economia publicas, deve ser mantido o indeferimento da suspensao da liminar. II - A decisao que se busca suspender constatou e declarou erro material na correcao de prova de concurso publico, apos ter sido realizado o cotejo entre o gabarito e a resposta da candidata, inexistindo ofensa a ordem publica. III - Agravo regimental a que se nega provimento. (SL 799 AgR; Orgao julgador: Tribunal Pleno; Relator(a): Min. RICARDO LEWANDOWSKI (Presidente); Publicacao: 18/03/2015) Deste ultimo julgamento, extraio o seguinte trecho do voto proferido pelo Ministro Relator: Nao ha falar em ofensa a ordem publica quando ocorre controle de legalidade dos atos praticados em certame que foi objeto de decisao judicial na qual se declarou erro material na correcao da prova, apos ter sido realizado o cotejo entre o gabarito e a resposta da candidata. No caso dos autos, verifico que se encontram presentes, nos termos da jurisprudencia do STF, os requisitos autorizativos da intervencao judicial, uma vez que se trata de evidente erro material da Banca Examinadora, como passo a demonstrar. Insurge-se o impetrante quanto a ausencia de pontuacao relativa a sua resposta a questao 4.A de Direito Constitucional, na prova pratico-profissional do Exame de Ordem da OAB/PA, a qual sustenta estar em conformidade com espelho de respostas da propria FGV. Com efeito, do espelho acostado a inicial, extraio a seguinte resposta do gabarito oficial, atribuida a questao 4.A (id 2183846240 - Pag. 2): "A. Sim. O nao pagamento da divida fundada (divida publica com exigibilidade superior a doze meses), sem que haja motivo de forca maior, permite a decretacao da intervencao no Municipio (0,55), nos termos do Art. 35, inciso I, da CRFB/88 (0,10)." Ja a resposta do impetrante a questao, se encontra assim redigida (id 2813846275): "A) Sim, e cabivel decreto de intervencao para que a uniao (sic) reorganize as financas da unidade da federacao que deixar de pagar sem motivo de forca maior por mais de 2 anos consecutivos divida fundada (vide art. 35 I da CF/88)." Ora, basta um cotejo superficial entre o gabarito da FGV e a resposta acima transcrita para se concluir que de fato incorreu a Banca Examinadora em erro material ao nao conferir qualquer pontuacao ao impetrante. O gabarito da FGV aponta como resposta inicial, "sim", ao que respondeu o impetrante "sim". O gabarito oficial fixa que "O nao pagamento da divida fundada (divida publica com exigibilidade superior a doze meses), sem que haja motivo de forca maior, permite a decretacao da intervencao no Municipio...(...)" Por seu turno, respondeu o impetrante que: "e cabivel decreto de intervencao para que a uniao (sic) reorganize as financas da unidade da federacao que deixar de pagar sem motivo de forca maior por mais de 2 anos consecutivos divida fundada..." Por fim, consta do gabarito oficial o dispositivo constitucional que fundamenta a resposta: "nos termos do Art. 35, inciso I, da CRFB/88". Na resposta do impetrante menciona-se o mesmo dispositivo legal: "(vide art. 35 I da CF/88)." Nao e preciso qualquer esforco interpretativo para se verificar que a resposta do requerente a questao 4.A se encontra exatamente dentro dos parametros fixados como corretos pelo espelho de correcao da prova, quais sejam: (i) sim; (ii) nao pagamento de divida fundada; (iii) sem motivo de forca maior; (iv) permissao de decreto de intervencao; (v) Art. 35, inciso I, da CRFB/88. De outra parte, na resposta ao recurso interposto, a Banca se manifestou de forma laconica, afirmando apenas que "a resposta nao preenche os requisitos exigidos pelo espelho sendo que a mera referencia legal nao pontua. Recurso improvido" (id 2183846199). Todavia, como ja ao norte demonstrado, a resposta do examinando reproduz de forma expressa os elementos constantes do espelho de prova, ressalvando-se apenas a ausencia de mencao ao conceito de divida fundada incluido no gabarito da FGV. Todavia, ainda sob esse aspecto, afigura-se flagrante o erro material de correcao, quando presentes na resposta do impetrante os elementos necessarios ao atendimento escorreito da indagacao, na forma do espelho de resposta da examinadora. Frise-se que sob nenhum aspecto se encontra este juizo revendo os criterios de correcao adotados pela FGV. Muito pelo contrario. O erro material identificado tem por fundamento exatamente a nao observancia dos criterios de correcao do gabarito oficial, na medida em que o responsavel pela correcao do quesito deixou de aplicar o espelho da prova ao atribuir pontuacao zero a resposta em analise. Trata-se aqui do mero controle de legalidade do ato administrativo que, deixando de lado os parametros de afericao de respostas ao qual se encontrava vinculado, culminou por nao atribuir a pontuacao a que faria jus o impetrante, por forca da grade de respostas da propria FGV. Acrescente-se ainda a ausencia de motivacao adequada, uma vez que a resposta ao recurso limitou-se a afirmar que "a mera referencia legal nao pontua", nao havendo qualquer mencao aos "requisitos exigidos pelo espelho" nao atendidos na resposta. Em suma, restando devidamente comprovada a existencia de flagrante erro material na correcao da questao sub judice, verifico a presenca dos requisitos necessarios ao deferimento da medida liminar inaudita altera pars, ressaltando, quanto ao perigo da demora, que este se evidencia pela ilegal supressao ao impetrante do direito ao exercicio de sua profissao, mediante inscricao na OAB. Pela pertinencia, trago mais uma vez a colacao o julgamento proferido pelo STF, ja ao norte transcrito, no qual se reconhece a ausencia de ilegalidade da intervencao judicial, em se tratando de flagrante erro material em correcao de prova. Confira-se: Nao ha falar em ofensa a ordem publica quando ocorre controle de legalidade dos atos praticados em certame que foi objeto de decisao judicial na qual se declarou erro material na correcao da prova, apos ter sido realizado o cotejo entre o gabarito e a resposta da candidata. (SL 799 AgR; Orgao julgador: Tribunal Pleno; Relator(a): Min. RICARDO LEWANDOWSKI (Presidente); Publicacao: 18/03/2015) Diante do exposto: 1. DEFIRO O PEDIDO DE LIMINAR para determinar a autoridade impetrada que proceda a atribuicao, ao impetrante RAUL LUIZ ESTEVES DO COUTO, da integralidade da pontuacao de 0,65, referente a Questao 4.A, Direito Constitucional, da prova pratico-profissional do 42º EXAME DE ORDEM UNIFICADO - 2ª FASE, Seccional OAB/PA, a qual devera ser somada a nota ja obtida pelo impetrante na referida prova para todos os fins de direito, ai incluida sua aprovacao na segunda fase do exame, caso obtenha pontuacao suficiente, bem como a respectiva inscricao nos quadros da OAB; 2. DEFIRO os beneficios da justica gratuita; 3. Considerando que a FGV e mera executora do exame, determino a exclusao de seu Presidente do polo passivo da lide e, por conseguinte, da propria Fundacao. Retifique-se a autuacao nestes termos; 4. Notifiquem-se as autoridades impetradas a fim de que preste as informacoes necessarias; 5. Cientifique-se a OAB/PA e e o Conselho Federal para os fins do inciso II do art. 7º da Lei n. 12.016/2009; 6. Vista ao MPF; 7. Por fim, conclusos para sentenca; Intime-se. Belem, data e assinatura eletronicas. HIND GHASSAN KAYATH Juiza Federal |comunicacao_id: 274080876|

"""

    metadados = extrair_metadados_publicacao(texto_exemplo)
    print(json.dumps(metadados, indent=2, ensure_ascii=False))
