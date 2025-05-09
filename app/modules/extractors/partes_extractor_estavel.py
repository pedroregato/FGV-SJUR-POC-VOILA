import re
import spacy
from typing import Dict, List
from dataclasses import dataclass

nlp = spacy.load("pt_core_news_lg")

# Dicionário de abreviações comuns em documentos jurídicos
ABREVIACOES = {
    "fgv": "fundação getúlio vargas",
    "seap": "secretaria de administração penitenciária",
    "tjba": "tribunal de justiça da bahia",
    "mp": "ministério público",
    "trf3": "tribunal regional federal da 3ª região",
    "dp": "defensoria pública"
}

@dataclass
class PartesProcesso:
    autor: List[str]
    reu: List[str]
    interessados: List[str]

def expandir_abreviacoes(texto: str) -> str:
    """Substitui abreviações por seus equivalentes completos."""
    for abrev, completo in ABREVIACOES.items():
        texto = re.sub(
            rf"\b{abrev}\b",
            completo,
            texto,
            flags=re.IGNORECASE
        )
    return texto

def limpar_entidade(texto: str) -> str:
    """Remove ruídos e normaliza."""
    texto = re.sub(r"\(OAB:[^)]+\)", "", texto)
    texto = re.sub(r"\b(?:DOC|Proc)\.?\s*[\d.-]+", "", texto)
    return texto.strip().upper()

def extrair_partes_avancado(texto: str) -> PartesProcesso:
    texto = expandir_abreviacoes(texto.lower())
    partes = PartesProcesso([], [], [])
    doc = nlp(texto)

    # --- Extração por Regex (campos explícitos) ---
    campos = {
        "autor": r"(?:impetrante|autor|requerente):\s*([^\n:]+)",
        "reu": r"(?:impetrado|reu|coator):\s*([^\n:]+)",
        "interessados": r"(?:interessado|terceiro):\s*([^\n:]+)"
    }

    for campo, padrao in campos.items():
        matches = re.finditer(padrao, texto, re.IGNORECASE)
        for match in matches:
            entidade = limpar_entidade(match.group(1))
            getattr(partes, campo).append(entidade)

    # --- Análise Semântica (spaCy) ---
    # Regra 1: Entidades após "contra" + NER
    for sent in doc.sents:
        if " contra " in sent.text:
            for ent in sent.ents:
                if ent.label_ in ("ORG", "PERSON", "LOC"):
                    ent_limpa = limpar_entidade(ent.text)
                    if ent_limpa not in partes.reu:
                        partes.reu.append(ent_limpa)

    # Regra 2: Verbos de ação + objetos
    for token in doc:
        if token.dep_ == "obj" and token.ent_type_ in ("ORG", "PERSON"):
            ent_limpa = limpar_entidade(token.text)
            if ent_limpa not in partes.reu:
                partes.reu.append(ent_limpa)

    return partes

# --- Testes com Abreviações ---
def testar_extracao_partes():
    test_cases = [
        {
            "input": "IMPETRADO: FGV e SEAP\nDecisão contra o MP",
            "expected": PartesProcesso(
                [],
                ["FUNDAÇÃO GETÚLIO VARGAS", "SECRETARIA DE ADMINISTRAÇÃO PENITENCIÁRIA", "MINISTÉRIO PÚBLICO"],
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

# Exemplo de uso direto (execução manual)
if __name__ == "__main__":
    # Exemplo com um texto real
    texto_exemplo = """
Publicacao Processo: 0804239-32.2025.8.19.0002 Orgao: 7ª Vara Civel da Comarca de Niteroi Data de disponibilizacao: 25/03/2025 Tipo de comunicacao: Intimacao Meio: Diario de Justica Eletronico Nacional Inteiro teor: https://tjrj.pje.jus.br/1g/Processo/ConsultaDocumento/listView.seam?x=25021414412467400000164184077 Parte: MARCO AURELIO TAVARES PEREZ Parte: ESTADO DO RIO DE JANEIRO Parte: FUNDACAO GETULIO VARGAS Advogado: CHRISTINA AIRES CORREA LIMA DE SIQUEIRA DIAS - OAB DF-11873 Advogado: JACQUELINE TAQUES DE SOUZA KUHN MONTEIRO - OAB RJ-063266 Advogado: PEDRO LUIZ MOREIRA AUAR PINTO - OAB RJ-234478 Advogado: BEATRIZ SARMENTO LEITE DO COUTO E SILVA - OAB RJ-001640 Advogado: LUCIANA GONCALVES NUNES MACEDO - OAB MG-83505 Advogado: MARCELO ROCHA DE MELLO MARTINS - OAB DF-06541 Conteudo: Poder Judiciario do Estado do Rio de Janeiro Comarca de Niteroi 7ª Vara Civel da Comarca de Niteroi Rua Visconde de Sepetiba, 519, 8º Andar, Centro, NITEROI - RJ - CEP: 24020-206 CERTIDAO Processo: 0804239-32.2025.8.19.0002 Classe: TUTELA CAUTELAR ANTECEDENTE (12134) AUTOR: MARCO AURELIO TAVARES PEREZ REU: ESTADO DO RIO DE JANEIRO, FUNDACAO GETULIO VARGAS Ao autor para recolher o valor das custas judiciais descritas no id. 172606343. NITEROI, 14 de fevereiro de 2025. MARCIO PONTES SOARES 
    """

    partes = extrair_partes_avancado(texto_exemplo)
    print(partes)