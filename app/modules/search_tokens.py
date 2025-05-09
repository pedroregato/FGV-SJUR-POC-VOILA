# modules/search_tokens.py
import re
from typing import Dict, List

# Cores para destacar os termos de busca
SEARCH_COLORS = [
    'background-color: yellow',
    'background-color: lightgreen',
    'background-color: lightblue',
    'background-color: pink',
    'background-color: lavender'
]


def highlight_text(text: str, terms: str) -> str:
    """
    Destaca os termos no texto com cores diferentes

    Args:
        text: Texto onde a busca será realizada
        terms: Termos separados por ";" para buscar

    Returns:
        Texto com os termos destacados em HTML
    """
    if not text or not terms:
        return text

    # Divide os termos e remove espaços em branco
    search_terms = [term.strip() for term in terms.split(';') if term.strip()]

    if not search_terms:
        return text

    highlighted = text
    for i, term in enumerate(search_terms):
        color_style = SEARCH_COLORS[i % len(SEARCH_COLORS)]
        # Usa regex para encontrar correspondências parciais (case insensitive)
        highlighted = re.sub(
            f'({re.escape(term)})',
            f'<span style="{color_style}">\\1</span>',
            highlighted,
            flags=re.IGNORECASE
        )

    return highlighted


def count_occurrences(text: str, terms: str) -> Dict[str, int]:
    """
    Conta as ocorrências de cada termo no texto

    Args:
        text: Texto onde a busca será realizada
        terms: Termos separados por ";" para contar

    Returns:
        Dicionário com os termos e suas contagens
    """
    if not text or not terms:
        return {}

    search_terms = [term.strip() for term in terms.split(';') if term.strip()]
    counts = {}

    for term in search_terms:
        counts[term] = len(re.findall(re.escape(term), text, flags=re.IGNORECASE))

    return counts


# modules/search_tokens.py
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


# ... (código existente mantido)

@dataclass
class ExtractedDeadline:
    raw_text: str  # Texto original encontrado
    days: int  # Número de dias convertido para inteiro
    type: str  # Tipo de prazo (ex: "dias", "horas")


def extract_deadlines(text: str) -> List[ExtractedDeadline]:
    """
    Extrai prazos do texto, incluindo formatos como "15 (quinze) dias"
    """
    if not text:
        return []

    number_map = {
        'zero': 0, 'um': 1, 'dois': 2, 'três': 3, 'quatro': 4, 'cinco': 5,
        'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9, 'dez': 10,
        'onze': 11, 'doze': 12, 'treze': 13, 'quatorze': 14, 'quinze': 15,
        'dezesseis': 16, 'dezessete': 17, 'dezoito': 18, 'dezenove': 19, 'vinte': 20,
        'trinta': 30, 'quarenta': 40, 'cinquenta': 50, 'sessenta': 60
    }

    patterns = [
        # Formato: "PRAZO de 15 (quinze) dias"
        r'(?:prazo\s+de|em|no\s+prazo\s+de|dentro\s+de)\s+(\d+)\s*\(\s*([a-zç]+)\s*\)\s*(dias|horas)',
        # Formato: "PRAZO de 10 dias" ou "em 10 dias"
        r'(?:prazo\s+de|em|no\s+prazo\s+de|dentro\s+de)\s+(\d+|[a-zç]+)\s+(dias|horas)',
        # Formato: "10 dias úteis"
        r'(\d+|[a-zç]+)\s+(dias|horas)\s+[úu]teis',
        # Formato: "no período de 10 dias"
        r'(?:per[ií]odo|prazo)\s+de\s+(\d+|[a-zç]+)\s+(dias|horas)'
    ]

    deadlines = []

    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            groups = match.groups()

            if len(groups) == 3 and groups[0] and groups[1] and groups[2]:
                # Formato com número e por extenso entre parênteses
                num_str, ext_str, unit = groups
                try:
                    days = int(num_str)  # Prioriza o numeral
                except ValueError:
                    days = number_map.get(ext_str.lower(), 0)
            elif len(groups) == 2 and groups[0] and groups[1]:
                # Formato padrão
                num_str, unit = groups
                if num_str.isdigit():
                    days = int(num_str)
                else:
                    days = number_map.get(num_str.lower(), 0)
            else:
                continue

            if days > 0:
                deadlines.append(ExtractedDeadline(
                    raw_text=match.group(0),
                    days=days,
                    type=unit.lower()
                ))

    return deadlines


def extrair_metadados(texto: str) -> Dict:
    """
    Extrai metadados do texto, incluindo número do processo e prazos

    Args:
        texto: Texto para análise

    Returns:
        Dicionário com metadados extraídos
    """
    metadados = {}

    # Extrai número do processo (código existente)
    processo = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto)
    metadados["Número do Processo"] = processo.group(0) if processo else "Não encontrado"

    # Extrai prazos
    prazos = extract_deadlines(texto)
    if prazos:
        metadados["Prazos"] = [
            {"texto": p.raw_text, "dias": p.days, "tipo": p.type}
            for p in prazos
        ]
    else:
        metadados["Prazos"] = "Nenhum prazo identificado"

    return metadados


@dataclass
class ParteReu:
    nome: str
    tipo_indicador: str  # "impetrado", "réu", "parte intimada", etc.


# modules/search_tokens.py
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# ... (código existente mantido)

def extract_partes_reus(text: str) -> List[ParteReu]:
    """
    Extrai partes réus do texto garantindo a captura completa do nome
    """
    if not text:
        return []

    partes_reus = []

    # 1. Padrão para REU/RÉU explícito - captura tudo até o próximo marcador em maiúsculas
    reu_explicito_pattern = r'(?i)(?:r[ée]u?\s*:\s*)([A-ZÀ-Ú\s]+?)(?=\s{2,}|\n|\r|\badvogado\b|\bautor\b|\bdecisa[oõ]\b|$)'

    for match in re.finditer(reu_explicito_pattern, text):
        nome_reu = clean_parte_name(match.group(1).strip())
        if nome_reu:
            partes_reus.append(ParteReu(
                nome=nome_reu,
                tipo_indicador="termo_explicito_reu"
            ))

    # 2. Padrão para Partes - captura tudo até o próximo marcador em maiúsculas
    todas_partes = re.finditer(
        r'(?i)parte\s*:\s*([A-ZÀ-Ú\s]+?)(?=\s{2,}|\n|\r|\bparte\b|\badvogado\b|\bautor\b|\bdecisa[oõ]\b|$)',
        text
    )
    partes_list = [clean_parte_name(match.group(1).strip()) for match in todas_partes if match.group(1)]

    if len(partes_list) >= 2:
        partes_reus.append(ParteReu(
            nome=partes_list[-1],
            tipo_indicador="ultima_parte"
        ))

    # Remover duplicados mantendo a ordem
    seen = set()
    partes_unicas = []
    for parte in partes_reus:
        if parte.nome not in seen:
            seen.add(parte.nome)
            partes_unicas.append(parte)

    return partes_unicas


def clean_parte_name(name: str) -> str:
    """
    Limpa o nome mantendo o nome completo
    """
    if not name:
        return ""

    # Remove conteúdo entre parênteses (como OAB)
    name = re.sub(r'\(.*?\)', '', name)

    # Remove marcadores de advogado no final
    name = re.sub(r'(?i)\b(?:adv|advogado|oab).*$', '', name)

    # Remove múltiplos espaços e trim
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def clean_parte_name(name: str) -> str:
    """
    Limpeza mais robusta para nomes de partes
    """
    if not name:
        return ""

    # Remove conteúdo após OAB ou similar
    name = re.sub(r'(?i)\b(?:oab|adv|advogado)[^\w]*.*$', '', name)

    # Remove caracteres especiais exceto letras, números, espaços e hífens
    name = re.sub(r'[^\w\sÀ-ú-]', '', name, flags=re.IGNORECASE)

    # Remove prefixos/sufixos específicos
    for term in ['e outros', 'etc', 'e outro', 'e demais']:
        name = re.sub(rf'\b{term}\b.*', '', name, flags=re.IGNORECASE)

    # Normaliza espaços e remove espaços no início/fim
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def clean_parte_name(name: str) -> str:
    """
    Limpeza mais precisa para nomes de partes
    """
    if not name:
        return ""

    # Remove conteúdo entre parênteses (como CNPJ, OAB)
    name = re.sub(r'\(.*?\)', '', name)

    # Remove caracteres especiais exceto letras, números, espaços e hífens
    name = re.sub(r'[^\w\sÀ-ú-]', '', name, flags=re.IGNORECASE)

    # Remove prefixos/sufixos específicos
    for term in ['advogado', 'advogada', 'adv', 'advs', 'oab', 'e outros', 'etc']:
        name = re.sub(rf'\b{term}\b.*', '', name, flags=re.IGNORECASE)

    # Normaliza espaços e remove espaços no início/fim
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def clean_parte_name(name: str) -> str:
    """
    Limpa o nome da parte removendo:
    - Espaços extras
    - Pontuação indesejada
    - Texto após parênteses (OAB)
    - Prefixos/sufixos comuns
    """
    if not name:
        return ""

    # Remove conteúdo após parênteses (como OAB)
    name = re.sub(r'\(.*?\)', '', name)

    # Remove caracteres especiais e espaços múltiplos
    name = re.sub(r'[^\w\s-]', '', name.strip())
    name = re.sub(r'\s+', ' ', name)

    # Remove prefixos/sufixos comuns
    for prefix in ['e outros', 'e outros (', 'e outro', 'advogado', 'advogados']:
        if name.lower().startswith(prefix):
            return ""

    return name.strip()


# Atualize a função extrair_metadados para usar a versão melhorada
def extrair_metadados(texto: str) -> Dict:
    metadados = {
        "Número do Processo": "Não encontrado",
        "Prazos": "Nenhum prazo identificado",
        "Partes Réus": "Nenhuma parte ré identificada"
    }

    # Extrai número do processo
    processo = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto)
    if processo:
        metadados["Número do Processo"] = processo.group(0)

    # Extrai prazos
    prazos = extract_deadlines(texto)
    if prazos:
        metadados["Prazos"] = [
            {"texto": p.raw_text, "dias": p.days, "tipo": p.type}
            for p in prazos
        ]

    # Extrai partes réus
    partes_reus = extract_partes_reus(texto)
    if partes_reus:
        metadados["Partes Réus"] = [
            {"nome": p.nome, "tipo_indicador": p.tipo_indicador}
            for p in partes_reus
        ]

    return metadados