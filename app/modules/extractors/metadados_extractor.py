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

Os campos tribunal, número do processo, UF e conteudo_publicado já foram extraídos por outros meios e não precisam ser retornados.
A data deve estar no formato YYYY-MM-DD. Se o texto contiver "certame", "gabarito" ou "concurso", a unidade_fgv deve ser "FGV Conhecimento".

Retorne apenas JSON com os 6 campos indicados, mesmo se algum estiver em branco ou a lista estiver vazia.
"""

def parse_numero_processo(numero_processo: str) -> dict:
    padrao = r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$"
    match = re.match(padrao, numero_processo)
    if not match:
        raise ValueError("Formato inválido. Esperado: NNNNNNN-DD.AAAA.J.TR.OOOO")

    sequencial, digito, ano, justica_id, tribunal_id, orgao_cnj = match.groups()
    uf_codigo = tribunal_id
    orgao_local = orgao_cnj[2:]

    ufs = {
        "01": "AC", "02": "AL", "03": "AP", "04": "AM", "05": "BA",
        "06": "CE", "07": "DF", "08": "ES", "09": "GO", "10": "MA",
        "11": "MT", "12": "MS", "13": "MG", "14": "PA", "15": "PB",
        "16": "PR", "17": "PE", "18": "PI", "19": "RJ", "20": "RN",
        "21": "RS", "22": "RO", "23": "RR", "24": "SC", "25": "SP",
        "26": "SP", "27": "SE", "28": "TO"
    }

    tribunais = {
        "07": "TRF1", "08": "TRF2", "09": "TRF3", "10": "TRF4", "11": "TRF5",
        "12": "TRF6", "13": "TRT1", "14": "TRT2", "15": "TRT3", "16": "TRT4",
        "17": "TRT5", "18": "TRT6", "19": "TJ-RJ", "20": "TJ-RN", "21": "TJ-RS",
        "22": "TJ-RO", "23": "TJ-RR", "24": "TJ-SC", "25": "TJ-SP", "26": "TJ-SE",
        "27": "TJ-TO", "28": "TJ-BA"
    }

    return {
        "numero_processo": numero_processo,
        "uf": ufs.get(uf_codigo, "Desconhecido"),
        "tribunal": tribunais.get(tribunal_id, "Desconhecido")
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
    Sr. Advogado, JUIZO DE DIREITO DA 1ª VARA CIVEL EDITAL DE INTIMACAO DE PARTES E ADVOGADOS RELACAO Nº 0268/2025 0000 - 
Processo 1007695-19.2023.8.26.0604 - Procedimento Comum Civel - Interpretacao / Revisao de Contrato - Eliana Lima de Castro - 
Viva Vista Solar Empreendimentos Imobiliarios Ltda - Vistos, Trata-se de acao proposta por ELIANA LIMA DE CASTRO em face de VIVA VISTA SOLAR 
SPE EMPREENDIMENTOS IMOBILIARIOS LTDA, pretendendo a revisao de contrato de compra e venda de imovel, 
com alienacao fiduciaria em garantia e financiamento imobiliario direto com construtora/incorporadora, pelo Sistema Financeiro Imobiliario (SFI). 
Relatou que, em 18/08/2020, firmou com a re instrumento particular de compromisso de venda e compra de unidade autonoma e outras avencas de nº 33, 
referente ao apartamento 33, tipo A2, localizado no 4º pavimento (3º andar), do bloco A, situado na Avenida A, nº 475, lote 1, quadra E,
 no loteamento Residencial Viva Vista, pelo preco de R$ 232.920,04, dividido em 240 parcelas mensais de R$ 1.857,68, com correcao monetaria mensal pelo IGP-M, 
 mais o valor de R$ 31.900,95, o qual foi diluido em 12 parcelas anuais no valor de R$ 4.624,41, com correcao monetaria anual tambem pelo IGP-M,
 alem do valor de R$ 2.462,06 a titulo de entrada. Alegou que, segundo promessas dos corretores, o reajuste anual de no maximo R$ 20,00, 
 razao pela qual acreditou que arcaria com parcelas de aproximadamente R$ 1.800,00, o que nunca ocorreu. Disse que, em razao do IGPM elevado, 
 as parcelas duplicaram de valor, com media entre R$ 2.700,00 e R$ 3.000,00, tornando impossivel o pagamento, pois aufere uma renda media mensal 
 de R$ 4.000,00 e ainda possui uma filha de dois anos, sendo a unica responsavel pela subsistencia de sua familia. Asseverou que, alem da correcao 
 monetaria mensal pelo indice IGP-M, ha a incidencia de juros remuneratorios de 10% ao ano, calculados pela Tabela Price, 
 conforme clausulas 9.3, 11, 11.1 e 11.2 do referido contrato. Sustentou que ocorreu grave omissao de informacoes, principalmente sobre a capitalizacao de juros, 
 comprovado atraves de pericia contabil, o que torna o contrato imprevisivel. Impugnou a capitalizacao dos juros, assim como a utilizacao da tabela 
 Price pela re, ja que nao integra o Sistema Financeiro Nacional (SFN). Destacou que, embora o contrato estabeleca o percentual de juros e o sistema de 
 amortizacao, nao se vislumbra qualquer mencao a capitalizacao, tornando o contrato imprevisivel e excessivamente oneroso. 
 Acrescentou que a correcao monetaria nao deve ser mensal, mas sim anual. Requereu a concessao de tutela de urgencia, para autorizar o deposito do valor 
 incontroverso das parcelas vencidas e vincendas, bem como para determinar a suspensao do processo extrajudicial de consolidacao da propriedade do imovel e dos
 efeitos do leilao. Ainda em sede de tutela de urgencia, postulou a suspensao do reajuste de 10% previsto nas clausulas 2.2, 9.1 e 11.2 do contrato firmado
 entre as partes. De forma definitiva, pediu a confirmacao da tutela de urgencia, com a revisao das clausulas 2.2, 9.1 e 11.2 do referido contrato, para se
 reconhecer a diferenca entre as parcelas pactuadas e as parcelas recalculadas, que correspondem a R$ 1.225,92 mensais e R$ 3.743,22 anuais, entre 21/05/2022 
 a 21/10/2040, com a substituicao do indice IGP-M pelo IPCA, sem capitalizacao, de modo que o valor devido e real para ser quitacao no final do contrato e 
 de R$ 292.192,29, reconhecendo-se, ainda, as abusividades contratuais acima expostas, inclusive a repeticao do indebito na quantia de R$ 45.338,50. 
 Pleiteou a condenacao da re ao pagamento de indenizacao por danos morais, no valor de R$ 45.338,50. Reclamou pelos beneficios da justica gratuita. 
 Juntou documentos (fls. 32/124). As fls. 152, foi-lhe concedida a gratuidade judiciaria e indeferido o pedido de tutela provisoria. 
 Citada as fls. 157, a re ofertou contestacao tempestiva as fls. 158/187, sustentando qua o imovel poderia ser adquirido atraves de financiamento bancario
 junto as instituicoes financeiras, no entanto, a requerente optou pelo financiamento direto, concordando expressamente com a aplicacao de juros calculados 
 de acordo com a tabela Price e correcao monetaria mensal pelo IGP-M. Aduziu que o pacto realizado nao se trata de financiamento bancario e que a legislacao permite a
 aplicacao de juros capitalizados, com reajuste pactuado em contrato. Alegou que a correcao monetaria nada mais e que mera atualizacao do capital com base na 
 inflacao, com objetivo unico de manter intacto o poder da moeda, destacando que que todos os indices foram corretamente aplicados e negando a ocorrencia de anatocismo. 
 Asseverou nao ha qualquer capitalizacao de juros ou somatoria sobre outros juros no presente caso, visto que tratou apenas de aplicar juros e corrigir monetariamente
 as parcelas pactuadas com a requerente, sem qualquer infracao a qualquer legislacao aplicavel ao mercado imobiliario. Disse que nao ha como prosperar a alegacao de 
 onerosidade excessiva, visto que as clausulas contratuais foram claras no sentido da incidencia do indice de correcao mensal pelo IGP-M e juros. 
 Mencionou que pactuou com a autora aditivo para substituicao do indice IGP-M pelo IPCA. Juntou documentos (fls. 188/310). Concedido PRAZO para replica e 
 especificacao de provas a produzir (fls. 311), a autora replicou a contestacao e se manifestou pela producao de todas as provas em direito admitidas (fls. 314/321),
 ao passo que a re pugnou pelo julgamento imediato do feito (fls. 322/327). E o RELATORIO. FUNDAMENTO e DECIDO. O caso e de julgamento conforme o estado do processo,
 nos termos do art. 355, I, do Codigo de Processo Civil, dada a preclusao do direito probatorio das partes, visto que a re expressamente requereu o julgamento imediato 
 do feito e a autora se limitou a expressar, de forma generica, o direito a “producao de todas as provas em direito admitidas, na amplitude dos artigos 369 e 
 seguintes do CPC, em especial documental superveniente, testemunhal, pericial e depoimento pessoal da parte contraria”, deixando de apontar a relevancia e pertinencia das referidas provas, assim como a materia controvertida que pretendia provar, conforme determinado as fls. 311. Trata-se, portanto, de pedido generico de provas, que conduz a preclusao. Nesse sentido: EMBARGOS A EXECUCAO. PRESTACAO DE SERVICOS. CONTRATO DE HONORARIOS ADVOCATICIOS. Embargante que pretende obstar a execucao de titulo executivo extrajudicial, consubstanciado em contrato de honorarios advocaticios, em razao de sua incapacidade a epoca dos fatos . Sentenca de improcedencia. Apelo do embargante. 1. Preliminar de cerceamento de defesa . Indeferimento de prova pericial complementar. Partes intimadas para especificar e justificar objetivamente eventuais provas. Pedido generico de pericia complementar, formulado sem fundamentacao habil. Preclusao do direito de produzir novas provas durante a instrucao do feito. Ausencia de intimacao das partes para apresentacao de alegacoes finais. Memoriais que possuem carater facultativo e complementar, sendo vedado arguir inovacoes. Ausencia de alegacoes finais que nao configura ofensa ao contraditorio e ampla defesa. Apelante que sequer comprovou efetivo prejuizo em razao da ausencia de intimacao para apresentacao de memoriais . Precedentes. Cerceamento de defesa nao configurado. Preliminar afastada. 2 . Merito. Controversia atinente a capacidade civil do requerente a epoca da assinatura do contrato de honorarios. Capacidade civil plena que goza de presuncao “iuris tantum”, tendo em vista que o estado de incapacidade configura verdadeira excecao ao exercicio de direitos e deveres. Onus do autor em demonstrar os fatos constitutivos do direito postulado, nos termos do art . 373, inciso I, do CPC. Interdicao provisoria do requerente que ocorreu no ano de 2018, por meio de decisao judicial. Decreto judicial de interdicao que goza de efeitos ex nunc. Precedente do E . STJ. Ademais, autor que nao comprovou o alegado estado de vulnerabilidade no ato da assinatura do contrato de honorarios, ou eventual prejuizo decorrente da contratacao dos servicos advocaticios. Laudo pericial produzido nos autos da acao de interdicao que foi inconclusivo em relacao a eventual incapacidade do requerente na epoca em que o contrato foi entabulado. Contratacao que se mostrou proveitosa ao autor, que obteve beneficio economico decorrente da atuacao efetiva dos patronos constituidos . Elementos nos autos que permitem concluir que o autor nao se encontrava incapacitado para o exercicio da vida civil. Nao obstante, preclusao do direito processual do requerente em produzir outras provas. Incapacidade civil e/ou excessiva onerosidade ao autor nao demonstrados. Improcedencia dos embargos a execucao . Sentenca mantida. 3. Recurso nao provido. (TJ-SP - Apelacao Civel: 1125220-55 .2018.8.26.0100 Sao Paulo, Relator.: Mary Grun, Data de Julgamento: 08/02/2024, 32ª Camara de Direito Privado, Data de Publicacao: 09/02/2024, grifo nosso). ACAO DE IMISSAO NA POSSE JULGADA PROCEDENTE. INCONFORMISMO. APELO DA PARTE RE. DESCABIMENTO DA ALEGACAO DE CERCEAMENTO DE DEFESA, TENDO EM VISTA QUE A PARTE RE FORMULOU PEDIDO GENERICO DE REALIZACAO DE PERICIA, OU SEJA, SEM ESPECIFICAR A UTILIDADE DA PRODUCAO DA PROVA PARA O DESLINDE DESTE FEITO. ALEM DISSO, A ANALISE CONJUNTA DOS ARGUMENTOS DAS PARTES E DOS DOCUMENTOS JUNTADOS NOS AUTOS SE REVELA SUFICIENTE PARA A SOLUCAO DO MERITO. PLEITO DE NULIDADE DA ARREMATACAO POR PRECO VIL. AUTOR QUE DEIXOU DE IMPUGNAR A AVALIACAO EM MOMENTO OPORTUNO. PRECLUSAO . TENTATIVA DE UTILIZAR A ACAO DE IMISSAO DE POSSE COMO SUCEDANEO DE EMBARGOS A ARREMATACAO. REDISCUSSAO DE MATERIA PRECLUSA E ACOBERTADA PELA COISA JULGADA, ANTE O TRANSITO EM JULGADO DO ACORDAO QUE ENFRENTOU AS MESMAS QUESTOES SUSCITADAS NESTA APELACAO. SENTENCA BEM FUNDAMENTADA. RECURSO DESPROVIDO. (TJ-SP - Apelacao Civel: 1001713-84.2022.8.26 .0369 Monte Aprazivel, Relator.: Alberto Gosson, Data de Julgamento: 28/05/2024, 1ª Camara de Direito Privado, Data de Publicacao: 29/05/2024, grifo nosso). De inicio, nao se vislumbrainteressedeagircom relacao ao pedido de substituicao do indice IGP-M pelo IPCA nas parcelas vencidas a partir de marco/2021, tendo em vista que a referida substituicao foi pactuada pelas partes no aditivo de fls. 276/281, cuja autenticidade nao foi impugnada pela autora. Nesse ponto, o feito tambem deve ser extinto sem resolucao do merito, nos termos do art. 485, VI, do CPC. No mais, o pedido e improcedente. A controversia reside na legalidade de correcao monetaria mensal e de juros remuneratorios a taxa de 10% ao ano, bem como na ocorrencia de capitalizacao dos juros e na configuracao de onerosidade excessiva, com fundamento na teoria da imprevisao, de modo a recalcular as parcelas com a utilizacao do indice IPCA. Inicialmente, anoto que a relacao que se firmou entre as partes e de consumo, porquanto a autora se enquadra no conceito de consumidor, constante do artigo 2º do Codigo de Defesa do Consumidor e a re, por sua vez, no conceito de fornecedor, constante do artigo 3º do mesmo estatuto legal. Apesar da relacao consumerista, nao se verifica hipossuficiencia tecnica a justificar ainversao do onus da prova, nos termos do art. 6º, VIII, do CDC. A proposito: PROCESSO CIVIL. APELACAO. ACAO DE COBRANCA. CONTRATO BANCARIO . CARTAO DE CREDITO CAIXA. APLICABILIDADE DO CODIGO DE DEFESA DO CONSUMIDOR. INVERSAO DO ONUS DA PROVA. CAPITALIZACAO DOS JUROS . ABUSIVIDADE DA COBRANCA DE JUROS. HONORARIOS MAJORADOS. POSSIBILIDADE. RECURSO NAO PROVIDO. (...) 6. Conquanto o caso se enquadre nas relacoes regidas pela legislacao consumerista, a inversao do onus da prova, disciplinada no art. 6º, VIII, da Lei nº . 8.078/90, nao e automatica. Como regra de julgamento ela fica a criterio do Juizo, bem como condicionada a presenca de determinados requisitos legais. Precedentes . 7. De fato, a inversao do onus da prova prevista no artigo 6º, inciso VIII, do Codigo de Defesa do Consumidor tem por lastro a assimetria tecnica e informacional existente entre as partes em litigio. 8. Assim, a distribuicao do onus da prova na forma ordinaria do artigo 333, incisos I e II, do Codigo de Processo Civil somente deve ser excepcionada se restar comprovada a vulnerabilidade do consumidor, a ponto de, em razao dessa circunstancia, nao conseguir comprovar os fatos que alega, ao mesmo tempo em que a parte contraria apresenta informacao e meios tecnicos habeis a producao da prova necessaria ao deslinde do feito. Precedentes. (...) 15. Apelacao nao provida. (TRF-3 - ApCiv: 50269305120184036100 SP, Relator.: Desembargador Federal HELIO EGYDIO DE MATOS NOGUEIRA, Data de Julgamento: 03/04/2020, 1ª Turma, Data de Publicacao: e - DJF3 Judicial 1 DATA: 07/04/2020, grifo nosso). Outrossim, o fato de o contrato celebrado entre as partes ter natureza adesiva nao acarreta, por si so, a sua invalidacao ou revisao ex officio, na medida em que nao resta suprimida a liberdade de contratar do aderente, a quem cabe o direito de optar ou nao por firmar a avenca, anuindo as condicoes estabelecidas. A autora alega que a obrigacao se tornou excessivamente onerosa em razao da atualizacao monetaria pelo indice IGP-M no periodo de pandemia da Covid-19. Assim, pretende a substituicao do indice IGP-M, expressamente previsto no contrato firmado entre as partes para fins de correcao monetaria anual, pelo indice IPCA, ao argumento de que seria menos oneroso. Por sua vez, a re defende que todas as informacoes se encontram expressas no instrumento contratual, de forma clara, incluindo o sistema de amortizacao, o indice de correcao monetaria e a taxa de juros. O contrato tem forca obrigatoria e faz lei entre as partes, que livremente pactuaram a aplicacao de do indice de reajuste das prestacoes mensais. Ademais, a autora possui capacidade juridica plena, sendo certo que competia a ela ler e tomar ciencia dos termos contratuais antes de exarar o seu consentimento. Por sua vez, o Poder Judiciario nao deve interferir na seara privada sem que haja alguma razao substancial para tanto. Dito isso, a alegacao de necessidade de troca dos indices por conta dos efeitos da pandemia de Covid-19 e demasiadamente generica, limitando-se a relatar a elevacao do valor das parcelas, sem apresentacao de qualquer prova documental. Evidente e notorio que a pandemia de Covid-19 impactou a vida de todas as pessoas, o que nao dispensava os autores de, no minimo, descrever com exatidao os fatos proprios seus, demonstrando eventual declinio de suas financas, para entao extrair as conclusoes a justificar a intervencao judicial. A proposito: APELACAO. Promessa de compra e venda de lote de terreno. Acao de revisao de clausula contratual, julgada improcedente. Recurso dos autores . Pretensao a substituicao do indice de correcao monetaria IGP-M/FGV pelo IPCA. Impossibilidade. 
 Inexistencia de ilegalidade ou abusividade na adocao do IGP-M medido pela FUNDACAO GETULIO VARGAS (FGV), 
 que registra a inflacao de precos desde materias-primas agricolas e industriais ate bens e servicos finais, sendo normalmente aceito e 
 utilizado nos contratos imobiliarios, refletindo a inflacao do periodo. Precedentes do C . STJ. 
 Substituicao significaria alteracao do pactuado entre as partes. Impossibilidade da imposicao de prejuizos apenas a parte re, o que ensejaria a 
 quebra da isonomia contratual. Pedido alternativo, de reconhecimento de erro na aplicacao do IGP-M, com devolucao, em dobro, do pagamento a maior .
 Impossibilidade. Laudo tecnico produzido unilateralmente pelos autores, sem o crivo do contraditorio e da ampla defesa, que nao pode ser tomado como prova 
 absoluta de suas argumentacoes, sob pena de violacao de principios constitucionais (art. 5º, LV da CF). Autores que, na fase de especificacao de provas,
 pugnaram pelo julgamento antecipado da lide . Preclusa a producao da prova pericial, nao ha razao para a aplicacao da norma do art. 938, § 3º, do CPC. Sentenca mantida. RECURSO DESPROVIDO, majorados os honorarios advocaticios devidos pela autora, com base no art . 85, § 11, do CPC, com a ressalva do art. 98, § 3º, do mesmo estatuto processual civil em vigor. (TJ-SP - Apelacao Civel: 1006085-37.2023 .8.26.0597 Sertaozinho, Relator.: Sergio Alfieri, Data de Julgamento: 26/04/2024, 27ª Camara de Direito Privado, Data de Publicacao: 26/04/2024). COMPRA E VENDA Revisao contratual - Sentenca de improcedencia APELACAO DO AUTOR Principio da dialeticidade recursal observado - Contrato com ajuste de correcao pelo IGPM - Pretensao do reconhecimento de onerosidade excessiva em razao da Pandemia da Covid-19 e substituicao do indexador pelo IPCA ou INCC - Ausencia de demonstracao de declinio na capacidade financeira do autor ao ponto de justificar a revisao do pacto - Indice utilizado no mercado imobiliario - Aplicacao do principio “pacta sunt servanda” - Jurisprudencia deste E. Tribunal de Justica - Sentenca mantida Sucumbencia recursal Art. 85, § 11, do CPC - RECURSO DESPROVIDO. (TJ-SP - Apelacao Civel: 1000063-90 .2022.8.26.0372 Monte Mor, Relator.: Fabio Podesta, Data de Julgamento: 17/10/2023, 21ª Camara de Direito Privado, Data de Publicacao: 17/10/2023) Apelacao Civel Compra e venda - Acao de revisao contratual Alegacao de reajuste abusivo pela incidencia do IGP-M como indexador, pretendendo sua substituicao pelo IPCA Improcedencia Inconformismo da autora Simples indice superior ao do IPCA no periodo que nao implica na nulidade da clausula nem autoriza sua mudanca Tese ja apreciada por este Tribunal que se posiciona pela regularidade da utilizacao do IGP-M no periodo pandemico Ausencia, ainda, de demonstracao por intermedio de calculo ou planilha, nao trazida aos autos Sentenca mantida Recurso desprovido (TJ-SP - Apelacao Civel: 1138991-95.2021.8.26 .0100 Sao Paulo, Relator.: Silverio da Silva, Data de Julgamento: 22/11/2023, 8ª Camara de Direito Privado, Data de Publicacao: 23/11/2023). Frise-se que a prova mencionada e documental e de facil producao pela autora, razao pela qual deveria ter acompanhado a peticao inicial, por inteligencia dos arts. 434 e 435, do CPC. Assim, compreende-se que a autora nao logrou comprovar a onerosidade excessiva da obrigacao, a teor do art. 373, I, do CPC. Demais disso, a Lei nº 9.514/97, que regula o Sistema Financeiro Imobiliario, estabelece que as partes poderao pactuar a capitalizacao dos juros, assim como a forma de correcao monetaria, conforme disposto no seu artigo 5º, I e III, in verbis: Art. 5º As operacoes de financiamento imobiliario em geral, no ambito do SFI, serao livremente pactuadas pelas partes, observadas as seguintes condicoes essenciais: I - reposicao integral do valor emprestado e respectivo reajuste; II - remuneracao do capital emprestado as taxas convencionadas no contrato; III - capitalizacao dos juros; IV - contratacao, pelos tomadores de financiamento, de seguros contra os riscos de morte e invalidez permanente. Assim, nao ha abusividade na aplicacao de correcao monetaria mensal, que foi expressamente pactuada pelas partes (fls. 225/248). Nesse sentido: APELACAO - ACAO REVISIONAL DE CONTRATO DE FINANCIAMENTO IMOBILIARIO - SENTENCA DE IMPROCEDENCIA. CERCEAMENTO DE DEFESA - Inocorrencia - Prova pericial contabil - Desnecessidade - Materia unicamente de direito - Correto o julgamento antecipado - Prestacao jurisdicional suficiente a resolver os limites da lide. FINANCIAMENTO IMOBILIARIO - Argumentos dos apelantes que nao convencem - Encargos contratuais - Ausencia de abusividade - Higidez das cobrancas efetuadas pela instituicao financeira - Capitalizacao dos juros - Admissibilidade - Contrato celebrado por instituicao financeira posteriormente a edicao da MP 1.963-17/00, reeditada sob o nº 2 .170-36/01 - Possibilidade de capitalizacao composta de juros em periodo inferior a um ano - Possibilidade de cobranca de juros sobre juros expressamente prevista pela Lei nº 9.514/1997 (artigo 5º, inciso III) - Permitida a previsao de correcao monetaria mensal - Art. 5º, I, da lei 9.514/97 expressamente dispoe que haveria previsao contratual de reajuste monetario do financiamento, cabendo as partes (§ 1º) estabelecer os seus criterios. SENTENCA MANTIDA - RECURSO DESPROVIDO. (TJ-SP - Apelacao Civel: 1013035-45.2021.8 .26.0011 Sao Paulo, Relator.: Sergio Gomes, Data de Julgamento: 19/10/2023, 18ª Camara de Direito Privado, Data de Publicacao: 19/10/2023, grifo nosso). Quanto a capitalizacao dos juros, a unica prova apresentada se trata de calculo efetuado a partir da alteracao do sistema de amortizacao e sem valor probatorio, por se tratar de documento produzido de forma unilateral. Nesse contexto, vale lembrar que o criterio da tabela Price consiste apenas em cobrar juros mensal sobre o saldo devedor mediante formula que obtem parcelas fixas, com as quais o autor anuiu. Com efeito, a adocao da Tabela Price, por si so, nao induz anatocismo, porque, se pagas todas as prestacoes de forma adequada, o pagamento de juros e mensal, dentro da parcela, calculados sobre o saldo devedor que nao recebe juros, senao correcao monetaria e amortizacao. O pagamento da prestacao mensal se refere a amortizacao e juros sobre o saldo devedor e mais outros consectarios contratuais. Nao ha consolidacao de juros no saldo devedor, se cumprido corretamente o contrato, nao havendo que se falar em capitalizacao de juros pela simples utilizacao do referido sistema de amortizacao. Sobre o tema, ja decidiu o e. TJSP: APELACAO CIVEL - APELACAO CIVEL - ACAO REVISIONAL DE CONTRATO DE COMPRA E VENDA DE IMOVEL - IGP-M COMO INDICE DE CORRECAO MONETARIA - PANDEMIA NAO CONFIGURA FATO IMPREVISIVEL - TABELA PRICE - LEGALIDADE DA CAPITALIZACAO DE JUROS - COBRANCA DE PARCELAS RESIDUAIS INDEVIDA. IGP -M como Indice de Correcao Monetaria: A aplicacao do IGP-M como indice de correcao pactuado no contrato e amplamente reconhecida e adotada nos contratos imobiliarios. A sua variacao durante a pandemia, embora significativa, nao justifica a revisao contratual, pois nao configura fato imprevisivel que permita a substituicao do indice acordado livremente entre as partes. Nao ha onerosidade excessiva, de acordo com a jurisprudencia do STJ e TJSP . Tabela Price e Capitalizacao de Juros: A utilizacao da Tabela Price para amortizacao e legal e nao implica, por si so, em anatocismo. Conforme laudo pericial, a Tabela Price nao caracteriza cobranca de juros compostos, visto que o metodo de amortizacao dilui os juros ao longo das prestacoes mensais, quitando-os integralmente a cada periodo, sem que se incorporem ao saldo devedor. Esse entendimento esta pacificado no STJ, que reconhece a legitimidade desse sistema em contratos de financiamento imobiliario. Cobranca Indevida de Parcelas Residuais: Confirmada pela pericia e pelo juizo de primeiro grau, a cobranca de parcelas residuais nao previstas no contrato configura pratica abusiva e nao se sustenta em razao da ausencia de autorizacao expressa . A decisao de excluir esses valores do saldo devedor deve ser mantida. Aplicacao Subsidiaria do Codigo de Defesa do Consumidor: Embora o contrato esteja sujeito a Lei de Alienacao Fiduciaria, admite-se a aplicacao do CDC de forma subsidiaria para proteger o equilibrio contratual, desde que nao haja conflito com a legislacao especifica. SENTENCA MANTIDA - RECURSO NAO PROVIDO. (TJ-SP - Apelacao Civel: 10215257320218260361 Mogi das Cruzes, Relator.: Olavo Paula Leite Rocha, Data de Julgamento: 29/10/2024, 5ª Camara de Direito Privado, Data de Publicacao: 29/10/2024, grifo nosso). APELACAO. CONTRATOS BANCARIOS. REVISIONAL. TUTELA DE URGENCIA . FINANCIAMENTO IMOBILIARIO. RELACAO DE CONSUMO. Sentenca de improcedencia da acao. Insurgencia recursal do autor . 1. JUROS REMUNERATORIOS. 1. Instituicoes financeiras nao estao sujeitas a limitacao de juros remuneratorios (STJ, Tema repetitivo 24); (STF, Sumula 596) . 2. Reconhecimento da abusividade e medida excepcional, como assentado pelo C. Superior Tribunal de Justica (STJ, Tema repetitivo 27). 3 . No caso concreto, nao ha abusividade, eis que nao extrapolou a taxa media de mercado. 2. CAPITALIZACAO DE JUROS. Permitida a capitalizacao de juros nos contratos firmados apos a edicao da MP 1963-17/2000, pois foi clara e expressamente pactuada, nos termos do decidido no REsp 973 .827/RS (STJ, Sumula 539 e Tema repetitivo 953). Adocao da Tabela Price que, por si so, nao implica anatocismo. Metodo de distribuicao desses juros ao longo do ano nao implica capitalizacao, nao importando a formula utilizada para esse calculo, seja linear ou exponencial, desde que nao viole a taxa estabelecida pelas partes no periodo de doze meses. 3 . TUTELA DE URGENCIA RECURSAL. Indeferimento, ante a resultante da acao em cognicao exauriente, que afastou a plausibilidade do direito do autor, mitigando o risco ao resultado util do processo (art. 300 do CPC/15). 4 . RECURSO DESPROVIDO. Majoracao da verba honoraria de 10% para 15% sobre o valor atualizado da causa ( § 11, do art. 85, do CPC/15). (TJ-SP - AC: 10086402420228260577 Sao Jose dos Campos, Relator.: Luis H . B. Franze, Data de Julgamento: 08/11/2023, 17ª Camara de Direito Privado, Data de Publicacao: 08/11/2023, grifo nosso). Por fim, nao ha amparo juridico para o pedido de afastamento dos juros remuneratorios estipulados a taxa de 10% ao ano, uma vez que foram expressamente previstos no contrato e sequer se mostram abusivos. Diante da inexistencia de cobrancas ilegais, nao ha que se falar em restituicao, tampouco em indenizacao por danos morais. Ante o exposto JULGO: 1) EXTINTO, sem resolucao do merito, o pedido de substituicao do indice IGP-M pelo IPCA, referente as parcelas vencidas a partir do termo aditivo de fls. 276/281, por falta de interesse de agir, nos termos do art. 485, VI, do CPC; 2) IMPROCEDENTE, quanto ao mais, a pretensao de ELIANA LIMA DE CASTRO em face de VIVA VISTA SOLAR SPE EMPREENDIMENTOS IMOBILIARIOS LTDA. Condeno a requerente ao pagamento das custas e dos honorarios advocaticios de 10% sobre o valor da causa em favor do advogado do reu, nos termos do CPC, art. 85, § 2º, ressalvando-se quanto a suspensao prevista pelo CPC, art. 98, § 3º, diante da concessao dos beneficios da justica gratuita ao autor. P.I. e, oportunamente, arquivem- se. - ADV: LUIZ ALCESTE DEL CISTIA THONON FILHO (OAB 211808/SP), 
MAYARA CARRARO BRANDAO (OAB 433085/SP)
    """

    metadados = extrair_metadados_publicacao(texto_exemplo)
    print(json.dumps(metadados, indent=2, ensure_ascii=False))
