import re
import spacy
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

nlp = spacy.load("pt_core_news_lg")

ABREVIACOES = {
    "fgv": "FUNDAÇÃO GETÚLIO VARGAS",
    "seap": "SECRETARIA DE ADMINISTRAÇÃO PENITENCIÁRIA",
    "tjba": "TRIBUNAL DE JUSTIÇA DA BAHIA",
    "mp": "MINISTÉRIO PÚBLICO",
    "trf3": "TRIBUNAL REGIONAL FEDERAL DA 3ª REGIÃO",
    "dp": "DEFENSORIA PÚBLICA",
    "oab": "ORDEM DOS ADVOGADOS DO BRASIL"
}

SINONIMOS_AUTOR = {"impetrante", "autor", "requerente", "demandante", "exequente", "recorrente"}
SINONIMOS_REU = {"impetrado", "reu", "coator", "demandado", "executado", "recorrido"}


@dataclass
class PartesProcesso:
    autor: List[str]
    reu: List[str]
    interessados: List[str]
    advogados_autor: List[str]
    advogados_reu: List[str]

    def __post_init__(self):
        def processar_lista(lista: List[str]) -> List[str]:
            return sorted(list(set(filter(None, (self.limpar_entidade(nome) for nome in lista)))))

        self.autor = processar_lista(self.autor)
        self.reu = processar_lista(self.reu)
        self.interessados = processar_lista(self.interessados)
        self.advogados_autor = processar_lista(self.advogados_autor)
        self.advogados_reu = processar_lista(self.advogados_reu)

    @staticmethod
    def limpar_entidade(texto: str) -> Optional[str]:
        if not texto or len(texto.strip()) < 2:
            return None

        # Primeiro expande abreviações
        texto = texto.upper()
        for abrev, completo in ABREVIACOES.items():
            texto = re.sub(rf"\b{abrev.upper()}\b", completo, texto)

        # Remove informações de OAB e números de processo
        texto = re.sub(r"\(?OAB[^)]*\)?", "", texto)
        texto = re.sub(r"\b(?:DOC|PROC|PROCESSO|N°?|Nº?|FLS?\.?|FOLHA|FLS)\s*[\d.-]*\b", "", texto)

        # Remove termos genéricos
        termos_remover = SINONIMOS_AUTOR.union(SINONIMOS_REU).union({"ADVOGADO", "ADVOGADA", "PARTE"})
        texto = re.sub(rf"\b(?:{'|'.join(termos_remover)})\b", "", texto)

        # Limpa pontuação e espaços
        texto = re.sub(r"[^\w\s]", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip()

        return texto if texto and len(texto) > 2 else None


def extrair_por_campos_explicitos(texto: str) -> Dict[str, List[str]]:
    partes = defaultdict(list)

    # Padrão para capturar autores e réus explicitamente declarados
    padrao = re.compile(
        rf"(?P<autor>(?:{'|'.join(SINONIMOS_AUTOR)})\s*:\s*(.+?))"
        rf"(?=\n|$|(?:{'|'.join(SINONIMOS_REU)})\s*:|$)|"
        rf"(?P<reu>(?:{'|'.join(SINONIMOS_REU)})\s*:\s*(.+?))"
        rf"(?=\n|$|(?:{'|'.join(SINONIMOS_AUTOR)})\s*:|$)",
        re.IGNORECASE | re.DOTALL
    )

    for match in padrao.finditer(texto):
        if match.group("autor"):
            partes_raw = match.group(2).strip()
            for parte in re.split(r"\s*[,;]\s*|\s+e\s+", partes_raw):
                if parte and len(parte) > 2:
                    partes["autor"].append(parte)
        elif match.group("reu"):
            partes_raw = match.group(4).strip()
            for parte in re.split(r"\s*[,;]\s*|\s+e\s+", partes_raw):
                if parte and len(parte) > 2:
                    partes["reu"].append(parte)

    return partes


def extrair_por_ordem_menção(texto: str) -> Dict[str, List[str]]:
    partes = defaultdict(list)
    matches = list(re.finditer(r"parte\s*:\s*([^\n:]+)", texto, re.IGNORECASE))

    if not matches:
        return partes

    # Primeira parte é sempre autor
    if matches[0].group(1).strip():
        partes["autor"].append(matches[0].group(1).strip())

    # Última parte é réu se houver mais de uma
    if len(matches) > 1 and matches[-1].group(1).strip():
        partes["reu"].append(matches[-1].group(1).strip())

    # Partes intermediárias são interessados
    for match in matches[1:-1]:
        if match.group(1).strip():
            partes["interessados"].append(match.group(1).strip())

    return partes


def analisar_relacoes_semanticas(texto: str) -> Dict[str, List[str]]:
    partes = defaultdict(list)
    doc = nlp(texto.lower())

    # Padrão para relações "contra"
    contra_matches = list(re.finditer(
        r"(?:processo\s+movi[td]o\s+por|aut[oa]r(?:a|es)?)\s+(.+?)\s+contra\s+(.+?)(?:\s+[e,]\s+|\s+|$)",
        texto,
        re.IGNORECASE
    ))

    for match in contra_matches:
        autores = match.group(1).strip()
        reus = match.group(2).strip()

        if autores:
            for autor in re.split(r"\s*[,;]\s*|\s+e\s+", autores):
                if autor and len(autor) > 2:
                    partes["autor"].append(autor)

        if reus:
            for reu in re.split(r"\s*[,;]\s*|\s+e\s+", reus):
                if reu and len(reu) > 2:
                    partes["reu"].append(reu)

    return partes


def extrair_advogados(texto: str) -> Tuple[List[str], List[str]]:
    advogados = []

    # Padrão melhorado para capturar advogados
    for match in re.finditer(
            r"advogad[oa](?:s)?\s*:\s*([^:\n]+?)(?:\s*-?\s*oab[^)\n]*)?(?=\n|$|advogad[oa])",
            texto,
            re.IGNORECASE
    ):
        nome = match.group(1).strip()
        if nome and len(nome.split()) >= 2:  # Pelo menos nome e sobrenome
            advogados.append(nome)

    if not advogados:
        return [], []

    # Se houver apenas 1 advogado, assume que é do autor
    if len(advogados) == 1:
        return advogados, []

    # Se houver 2, divide entre autor e réu
    if len(advogados) == 2:
        return [advogados[0]], [advogados[1]]

    # Para mais de 2, divide proporcionalmente
    split_point = len(advogados) * 2 // 3
    return advogados[:split_point], advogados[split_point:]


def extrair_partes_avancado(texto: str) -> PartesProcesso:
    # Extrai partes por campos explícitos
    partes_explicitas = extrair_por_campos_explicitos(texto)

    # Se não encontrou partes explícitas, tenta por ordem de menção
    if not partes_explicitas["autor"] and not partes_explicitas["reu"]:
        partes_explicitas.update(extrair_por_ordem_menção(texto))

    # Extrai relações semânticas
    partes_semanticas = analisar_relacoes_semanticas(texto)

    # Extrai advogados
    advogados_autor, advogados_reu = extrair_advogados(texto)

    return PartesProcesso(
        autor=partes_explicitas["autor"] + partes_semanticas["autor"],
        reu=partes_explicitas["reu"] + partes_semanticas["reu"],
        interessados=partes_explicitas["interessados"],
        advogados_autor=advogados_autor,
        advogados_reu=advogados_reu
    )


def testar_extracao_partes():
    test_cases = [
        {
            "input": "AUTOR: FGV e SEAP\nDecisão contra o MP",
            "expected": PartesProcesso(
                ["FUNDAÇÃO GETÚLIO VARGAS", "SECRETARIA DE ADMINISTRAÇÃO PENITENCIÁRIA"],
                ["MINISTÉRIO PÚBLICO"],
                [],
                [],
                []
            )
        },
        {
            "input": "Parte: EMPRESA A LTDA Parte: EMPRESA B SA Advogado: JOÃO SILVA - OAB/SP 123456",
            "expected": PartesProcesso(
                ["EMPRESA A LTDA"],
                ["EMPRESA B SA"],
                [],
                ["JOÃO SILVA"],
                []
            )
        },
        {
            "input": "Processo movido por MARIA SILVA contra JOSÉ SOUZA e EMPRESA X",
            "expected": PartesProcesso(
                ["MARIA SILVA"],
                ["JOSÉ SOUZA EMPRESA X"],
                [],
                [],
                []
            )
        },
        {
            "input": "AUTOR: BANCO DO BRASIL, FGV\nREU: ESTADO DO RJ",
            "expected": PartesProcesso(
                ["BANCO DO BRASIL", "FUNDAÇÃO GETÚLIO VARGAS"],
                ["ESTADO DO RJ"],
                [],
                [],
                []
            )
        }
    ]

    for case in test_cases:
        resultado = extrair_partes_avancado(case["input"])
        assert resultado == case["expected"], f"""
❌ Falha no caso: {case['input']}
Esperado: {case['expected']}
Obtido: {resultado}
"""
        print(f"✅ Caso aprovado: {case['input']}")


if __name__ == "__main__":
    texto_exemplo = """
Publicacao Processo: 0804239-32.2025.8.19.0002 Orgao: 7ª Vara Civel da Comarca de Niteroi Data de disponibilizacao: 25/03/2025 Tipo de comunicacao: Intimacao Meio: Diario de Justica Eletronico Nacional Inteiro teor: https://tjrj.pje.jus.br/1g/Processo/ConsultaDocumento/listView.seam?x=25021414412467400000164184077 Parte: MARCO AURELIO TAVARES PEREZ Parte: ESTADO DO RIO DE JANEIRO Parte: FUNDACAO GETULIO VARGAS Advogado: CHRISTINA AIRES CORREA LIMA DE SIQUEIRA DIAS - OAB DF-11873 Advogado: JACQUELINE TAQUES DE SOUZA KUHN MONTEIRO - OAB RJ-063266 Advogado: PEDRO LUIZ MOREIRA AUAR PINTO - OAB RJ-234478 Advogado: BEATRIZ SARMENTO LEITE DO COUTO E SILVA - OAB RJ-001640 Advogado: LUCIANA GONCALVES NUNES MACEDO - OAB MG-83505 Advogado: MARCELO ROCHA DE MELLO MARTINS - OAB DF-06541 Conteudo: Poder Judiciario do Estado do Rio de Janeiro Comarca de Niteroi 7ª Vara Civel da Comarca de Niteroi Rua Visconde de Sepetiba, 519, 8º Andar, Centro, NITEROI - RJ - CEP: 24020-206 CERTIDAO Processo: 0804239-32.2025.8.19.0002 Classe: TUTELA CAUTELAR ANTECEDENTE (12134) AUTOR: MARCO AURELIO TAVARES PEREZ REU: ESTADO DO RIO DE JANEIRO, FUNDACAO GETULIO VARGAS Ao autor para recolher o valor das custas judiciais descritas no id. 172606343. NITEROI, 14 de fevereiro de 2025. MARCIO PONTES SOARES 
"""
    partes = extrair_partes_avancado(texto_exemplo)
    print("=== Partes Extraídas ===")
    print(f"Autores: {partes.autor}")
    print(f"Réus: {partes.reu}")
    print(f"Interessados: {partes.interessados}")
    print(f"Advogados do Autor: {partes.advogados_autor}")
    print(f"Advogados do Réu: {partes.advogados_reu}")
