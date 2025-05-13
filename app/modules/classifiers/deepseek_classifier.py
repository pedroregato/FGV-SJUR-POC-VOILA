import json
import os
import re
import requests
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
from dotenv import load_dotenv

from app.modules.prompts.prompt_definitions import carregar_prompt_custom

# Carrega .env apenas uma vez no topo
load_dotenv()

ClassificationLabel = Literal["citação", "intimação", "não previsto"]

@dataclass
class ClassificationResult:
    classification: ClassificationLabel
    status: str
    method: Literal["ia_deepseek", "fallback_local"]
    confidence: float = 1.0
    justification: Optional[str] = None

class DeepSeekAPIClient:
    def __init__(self, api_key: str = None):
        if not api_key:
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            if not self.api_key:
                print("❌ A variável DEEPSEEK_API_KEY não foi encontrada no .env ou no ambiente.")
                exit(1)
        else: self.api_key = api_key

        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def make_request(self, payload: dict, timeout: int = 10) -> Tuple[Optional[dict], Optional[str]]:
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            if response.status_code == 200:
                return response.json(), None
            return None, f"HTTP {response.status_code}: {response.text}"
        except Exception as e:
            return None, str(e)

class DeepSeekLegalClassifier:
    def __init__(self, api_key: str = None):
        self.api_client = DeepSeekAPIClient(api_key)
        self.classifier_type = "deepseek"
        self.system_prompt = carregar_prompt_custom()
        self.cnj_regex = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

    def _validate_classification(self, classification: str, justification: str) -> bool:
        """Valida apenas se a resposta está no formato esperado."""
        if classification not in ("citação", "intimação", "não previsto"):
            return False
        if not justification or len(justification.split()) > 30:
            return False
        return True

    def _parse_api_response(self, response: dict, original_text: str) -> ClassificationResult:
        """Processa a resposta da API e valida a classificação"""
        try:
            resposta_bruta = response['choices'][0]['message']['content']
            print(f"🧠 DeepSeek resposta bruta:\n{resposta_bruta}")

            # Remove blocos markdown
            resposta_bruta = resposta_bruta.strip()
            if resposta_bruta.startswith("```json"):
                resposta_bruta = resposta_bruta[7:-3].strip()
            elif resposta_bruta.startswith("```"):
                resposta_bruta = resposta_bruta[3:-3].strip()

            resposta_json = json.loads(resposta_bruta)
            classificacao = resposta_json.get("classificacao", "").strip().lower()
            justificativa = resposta_json.get("justificativa", "").strip()

            if not self._validate_classification(classificacao, justificativa):
                print("⚠️ Classificação não atende aos critérios formais")
                return ClassificationResult("não previsto", "erro: regras não atendidas", "fallback_local")

            return ClassificationResult(
                classificacao,
                "sucesso",
                "ia_deepseek",
                justification=justificativa
            )

        except json.JSONDecodeError as e:
            print(f"❌ Erro ao decodificar JSON: {e}\nResposta: {resposta_bruta}")
            return ClassificationResult("não previsto", "erro: json inválido", "fallback_local")
        except KeyError as e:
            print(f"❌ Erro de chave na resposta: {e}")
            return ClassificationResult("não previsto", "erro: formato inesperado", "fallback_local")

    def classify_text(self, text: str) -> ClassificationResult:
        """Classifica o texto jurídico com validação rigorosa"""
        if not text.strip():
            return ClassificationResult("não previsto", "erro: texto vazio", "fallback_local")

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.0,
            "max_tokens": 300,
            "top_p": 0.1
        }

        api_response, error = self.api_client.make_request(payload, timeout=30)
        if error:
            print(f"⚠️ Erro na requisição: {error}")
            return ClassificationResult("não previsto", f"erro: {error}", "fallback_local")

        return self._parse_api_response(api_response, text)

def classificar_publicacao_heuristica(texto_publicacao: str) -> ClassificationResult:
    texto = texto_publicacao.lower()

    if ("intime-se" in texto or "intimar" in texto) and any(term in texto for term in ["dia", "dias"]):
        return ClassificationResult("intimação", "heurística", "fallback_local", confidence=0.8)

    if "fundação getúlio vargas" in texto or "fgv" in texto:
        if "citação" in texto or "réu" in texto or "autor" in texto:
            return ClassificationResult("citação", "heurística", "fallback_local", confidence=0.9)

    return ClassificationResult("não previsto", "heurística", "fallback_local", confidence=0.7)

if __name__ == "__main__":
    # Lê chave da API do ambiente
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ A variável DEEPSEEK_API_KEY não foi encontrada no .env ou no ambiente.")
        exit(1)

    texto_teste = '''
0000 - PODER JUDICIARIO TRIBUNAL DE JUSTICA DO ESTADO DA BAHIA Des. Rolemberg Jose Araujo Costa DECISAO 8013207-41.2025.8.05.0000 Mandado De Seguranca Civel Jurisdicao: Tribunal De Justica Impetrado: FUNDACAO GETULIO VARGAS Impetrado: Estado Da Bahia Impetrante: Jeslye Jordania Freire Da Silva Advogado: Jeslye Jordania Freire Da Silva (OAB:BA5311100A) Impetrado: Governador Do Estado Da Bahia Impetrado: Secretario De Administracao Do Estado Da Bahia Impetrado: Diretor Geral Da FUNDACAO GETULIO VARGAS - Fgv Decisao: PODER JUDICIARIO TRIBUNAL DE JUSTICA DO ESTADO DA BAHIA Secao Civel de Direito Publico Processo: MANDADO DE SEGURANCA CIVEL n. 8013207-41.2025.8.05.0000 Orgao Julgador: Secao Civel de Direito Publico IMPETRANTE: JESLYE JORDANIA FREIRE DA SILVA Advogado(s): JESLYE JORDANIA FREIRE DA SILVA (OAB:BA5311100A) IMPETRADO: FUNDACAO GETULIO VARGAS e outros (4) Advogado(s): RC01 DECISAO I.Relatorio Trata-se de mandado de seguranca impetrado por JESLYE JORDANIA FREIRE DA SILVA contra ato atribuido ao Governador do Estado, ao Secretario da Administracao e ao Diretor da FGV, autoridades vinculadas ao Estado da Bahia. Segundo relatado na peticao inicial, “A Impetrante participou do Concurso Publico para provimento de vagas no quadro de pessoal da Secretaria de Administracao Penitenciaria e Ressocializacao do Estado da Bahia, cargo de Policial Penal, regidos pelo Edital de abertura de inscricoes – SEAP nº 02/2024, de 12 de junho de 2024 .[...]Realizadas as provas objetiva e discursiva, a Impetrante obteve 60 (sessenta) pontos na prova objetiva (Doc. 02), o que a classifi cou na posicao 94ª da ampla concorrencia (Doc. 03 – pag. 04), prosseguindo no certame para a correcao da prova discursiva, onde obteve a pontuacao 17,7 (Doc. 03 e Doc.05 – pag 14 e 27). Deste modo, a pontuacao fi nal da Impetrante e 77,7 (setenta e sete virgula sete), conforme se extrai das listas de aprovados no certame[...] Impetrante optou por concorrer pelo sistema de cotas para candidatos negros, sendo observado pelo Edital de Abertura SEAP nº 02/2024, publicado no dia 12 de junho de 2024 (Doc. 01), que os optantes por essa modalidade de concorrencia seriam submetidos a verifi cacao da condicao declarada no dia 06 de janeiro 2025. Contudo, no dia 27 de dezembro de 2024, fora publicada modifi cacao do cronograma do certame, ocasiao em que a data para o Procedimento de Heteroidentifi cacao foi alterada para o dia 26 de janeiro de 2025. Em virtude da alteracao no cronograma da banca examinadora, a candidata fi cou impossibilitada de comparecer a etapa de Heteroidentifi cacao, uma vez que na mesma data, dia 26 de janeiro de 2025, teria que realizar outro concurso, no Estado de Minas Gerais, organizado pela mesma banca (FUNDACAO GETULIO VARGAS), [...] a Impetrante prontamente entrou em contato com a organizacao do certame, informando o ocorrido e requerendo nova data para realizacao do exame mails enviados tempestivamente (Doc. 11, 12 e 13) .[...] No entanto, seu pedido foi indeferido. A impetrante alega que, apesar de ter obtido nota sufi ciente para aprovacao na ampla concorrencia, foi excluida do concurso, o que ela considera ilegal, pois que o edital do concurso nao poderia prever sua exclusao e que a eliminacao por nao comparecimento a heteroidentifi cacao e desproporcional, especialmente porque ela ja foi reconhecida como negra em outra avaliacao. Requer o beneficio da justica gratuita e “Seja DEFERIDA LIMINARMENTE ao Impetrante, inaldita altera pars (sic), a suspensao imediata do ato impugnado, a saber, a desclassifi cacao da candidata no Concurso da Secretaria de Administracao Penitenciaria e Ressocializacao do Estado da Bahia - SEAP, para o cargo de Policial Penal, utilizando a nota da Impetrante para as vagas da ampla concorrencia, determinando o seu prosseguimento nas proximas fases do certame, e a sua inclusao a LISTA DE CONVOCACAO PARA A APRESENTACAO DE DOCUMENTACAO entre os dias 17/03/2025 a 19/03/2025, conforme consta da Portaria n° 058, de 12 de marco de 2025 (Doc. 23). [...] Subsidiariamente, seja DEFERIDA LIMINARMENTE ao Impetrante, inaldita altera pars [sic], a suspensao imediata do ato impugnado, a saber, a desclassifi cacao da candidata no Concurso da Secretaria de Administracao Penitenciaria e Ressocializacao do Estado da Bahia - SEAP, para o cargo de Policial Penal, reconhecendo a Impetrante como candidata negra/parda, com base na decisao unanime da Comissao de Heteroidentifi cacao da banca FCC, determinando o seu prosseguimento nas proximas fases do certame, e a sua inclusao a LISTA DE CONVOCACAO PARA A APRESENTACAO DE DOCUMENTACAO entre os dias 17/03/2025 a 19/03/2025, conforme consta da Portaria n° 058, de 12 de marco de 2025 (Doc. 23).” II. Fundamentacao Inicialmente, por observar que nada infi rma a alegada insufi ciencia de recursos, defi ro a gratuidade de justica. Quanto ao objetivo almejado pela impetrante de reforma/anulacao do resultado da Comissao que a excluiu do certame pelo nao comparecimento ao Procedimento de Heteroidentifi cacao, observa-se que consta no edital (doc. id 78902573): 9. DAS VAGAS DESTINADAS A CANDIDATOS NEGROS 9.1 Serao reservados aos candidatos negros (preto/pardo) que facultativamente autodeclarem tais condicoes no momento da inscricao, na forma do artigo 49 da Lei estadual nº 13.182, de 06 de junho de 2014, regulamentada pelo Decreto estadual nº 15.353, de 07 de agosto de 2014, 30% (trinta por cento) das vagas oferecidas no Concurso (...) 9.6.2 O candidato convocado na forma do item 9.6 deste Edital e que nao comparecer ao Procedimento de Heteroidentifi cacao sera excluido do Concurso Publico, dispensada a convocacao suplementar de candidatos nao convocados para o Procedimento de Heteroidentifi cacao. (...) 9.18.1 O candidato que nao for considerado negro, caso seja aprovado no Concurso Publico, fi gurara na lista de classifi cacao de ampla concorrencia caso tenha obtido pontuacao/classifi cacao necessaria para tanto, no limite estabelecido nos Capitulos 11 e 12 deste Edital. A uma primeira analise, a exclusao do candidato do concurso pelo nao comparecimento a avaliacao da Comissao de heteroidentifi cacao, conforme previsto no Edital acima transcrito, nao encontra amparo legal, pois a Lei nº 12.990, de 09 de junho de 2014, que reserva aos negros 20% (vinte por cento) das vagas oferecidas nos concursos publicos para provimento de cargos efetivos e empregos publicos no ambito da administracao publica federal, das autarquias, das fundacoes publicas, das empresas publicas e das sociedades de economia mista controladas pela Uniao, assim estabelece: Art. 2º Poderao concorrer as vagas reservadas a candidatos negros aqueles que se autodeclararem pretos ou pardos no ato da inscricao no concurso publico, conforme o quesito cor ou raca utilizado pela Fundacao Instituto Brasileiro de Geografi a e Estatistica - IBGE. Paragrafo unico. Na hipotese de constatacao de declaracao falsa, o candidato sera eliminado do concurso e, se houver sido nomeado, fi cara sujeito a anulacao da sua admissao ao servico ou emprego publico, apos procedimento administrativo em que lhe sejam assegurados o contraditorio e a ampla defesa, sem prejuizo de outras sancoes cabiveis. Art. 3º Os candidatos negros concorrerao concomitantemente as vagas reservadas e as vagas destinadas a ampla concorrencia, de acordo com a sua classifi cacao no concurso. Da Leitura dos dispositivos legais acima transcritos, constata-se que a exclusao do candidato do certame decorre de declaracao falsa, o que nao ocorreu no caso em exame. O “fumus boni iuris” se evidencia, pois caso o candidato nao tivesse a sua autodeclaracao ratifi cada pela Banca, ainda assim, poderia permanecer no concurso nas vagas destinadas a ampla concorrencia. Dessa forma, nesse primeiro momento processual, com base no principio da isonomia, nao parece razoavel o ato da autoridade que resultou na exclusao da candidata do certame pelo nao comparecimento a avaliacao. Assim, vem se posicionando os Tribunais Patrios: E M E N T A ADMINISTRATIVO. CONSTITUCIONAL. MANDADO DE SEGURANCA. SISTEMA DE COTAS . NAO COMPARECIMENTO AO EXAME DE HETEROIDENTIFICACAO. ELIMINACAO DO CERTAME. ILEGALIDADE. PERMANENCIA NA LISTA DE AMPLA CONCORRENCIA . POSSIBILIDADE. SENTENCA REFORMADA. - A reserva de vagas para os negros/pardos em concursos publicos federais esta prevista na Lei n. 12 .990/2014 - O Supremo Tribunal Federal, no julgamento do ADC n. 41 em 08.06.2017, reconheceu a constitucionalidade da reserva de vagas oferecidas em concursos publicos e tambem a regularidade da avaliacao da autodeclaracao por meio de comissao de heteroidentifi cacao - Estando o candidato negro/pardo concorrendo simultaneamente as vagas destinadas a cota racial e as de ampla concorrencia, a sua aprovacao em vaga de ampla concorrencia, torna dispensavel a verifi cacao da autodeclaracao - A exclusao do certame de candidato autodeclarado negro ou pardo aprovado em vagas de ampla concorrencia vai de encontro as politicas afi rmativas nas quais a Lei 12 .990/2014 se ampara e ao escopo do proprio concurso, que visa a selecao dos candidatos mais bem preparados - Sem condenacao em honorarios - Apelacao provida. (TRF-3 - ApCiv: 50010731220194036118 SP, Relator.: Desembargador Federal PAULO SERGIO DOMINGUES, Data de Julgamento: 05/08/2022, 6ª Turma, Data de Publicacao: DJEN DATA: 10/08/2022). ADMINISTRATIVO. AGRAVO DE INSTRUMENTO. ACAO ORDINARIA. CONCURSO . ACOES AFIRMATIVAS. NAO COMPARECIMENTO A HETEROIDENTIFICACAO. DESPROVIMENTO. 1 . A perda da chance de concorrer a vaga pelo sistema de cotas, ocasionada pela ausencia da candidata a entrevista de heteroidentifi cacao, nao pode representar obice a sua classifi cacao no concurso pelo sistema de ampla concorrencia. 2. Desta forma, a despeito das alegacoes da parte agravante, tem-se que e caso de prestigiar-se o juizo a quo, uma vez que este esta proximo das partes e dos fatos da causa, nao existindo nos autos situacao que justifi que, nesse momento processual, alteracao do que foi decidido. (TRF-4 - AG: 50183093420204040000 5018309-34 .2020.4.04.0000, Relator.: VANIA HACK DE ALMEIDA, Data de Julgamento: 28/07/2020, TERCEIRA TURMA) Nesse sentido, segue a orientacao adotada neste Colegiado: MANDADO DE SEGURANCA. DIREITO CONSTITUCIONAL E ADMINISTRATIVO. CONCURSO PUBLICO. DEFENSORIA PU- BLICA DO ESTADO DA BAHIA. DEFENSOR PUBLICO. SISTEMA DE COTAS RACIAIS. AUTODECLARACAO. EXCLUSAO DO CANDIDATO. COMISSAO ESPECIAL DE VERIFICACAO. LEGALIDADE DO PROCEDIMENTO. CONDICAO DE PARDO. NAO VERIFICADO. AUSENCIA DE MA-FE. MANUTENCAO NO CERTAME NA LISTA DE AMPLA CONCORRENCIA. ENTENDIMENTO FIRMADO POR ESTA CORTE. DIREITO LIQUIDO E CERTO. VERIFICADO EM PARTE. CONCESSAO PARCIAL DA SEGURANCA. (TJBA - Mandado de Seguranca no 0018210-94.2017.8.05.0000, Relator: Des. EDMILSON JATAHY FONSECA JUNIOR, p. em: 03/05/2018). Assim, nao se tratando de hipotese revestida de ma-fe, o candidato excluido da etapa de heteroidentifi cacao devera continuar participando do concurso em relacao as vagas destinadas a ampla concorrencia, desde que obtenham a pontuacao/classifi cacao para tanto. Essa exclusao, pode decorrer tanto pelo fato de nao ser confi rmada a autodeclaracao fi rmada ou, como no caso em analise, pelo nao comparecimento do candidato a etapa de heteroidentifi cacao. O “periculum in mora” se constata pelas consequencias da exclusao da candidata obstada de seguir as fases subsequentes do certame, apresentar documentos, etc. Presentes, assim, os requisitos para concessao da liminar. III. Dispositivo Posto isso, DEFIRO A LIMINAR para determinar as autoridades coatoras a suspensao do ato de eliminacao da impetrante do certame, mantendo-a provisoriamente na lista geral de classifi cacao, desde que tenha obtido pontuacao/classifi cacao para fi gurar na listagem de ampla concorrencia, procedendo a sua inclusao a lista de convocacao para a apresentacao de documentacao e prosseguir as demais etapas do concurso, assegurando em seu favor a reserva de vaga, ate ulterior deliberacao deste juizo. Notifi que-se as autoridades apontadas como coatoras para que prestem, no PRAZO de dez dias, as informacoes que entenderem necessarias. Oportunamente, abra-se vista dos autos a Procuradoria de Justica para emissao de parecer, em 20 dias, salvo se suscitadas preliminares ou juntados documentos, quando, entao, deve-se ouvir previamente o impetrante, no PRAZO de dez dias. Publique-se. Intime-se. Decisao/despacho com forca de mandado/ oficio Salvador/BA, 21 de marco de 2025. Desembargador ROLEMBERG COSTA – Relator'''


    classificador = DeepSeekLegalClassifier(api_key)
    resultado = classificador.classify_text(texto_teste)

    print("\n🔍 Resultado da Classificação:")
    print(f"🏷️ Classificação: {resultado.classification}")
    print(f"🧾 Justificativa: {resultado.justification}")
    print(f"⚙️ Método: {resultado.method}")
    print(f"📈 Confiança: {resultado.confidence}")
    print(f"📡 Status: {resultado.status}")