# app/modules/utils/archival_patterns.py
#### Novo utilitário de padrões

from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple

def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))

def normalize(s: str) -> str:
    # mantém uma linha e remove acentos; use a versão original para gerar HTML
    s = strip_accents(s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

# ——— Padrões (regex) e pesos ———
PATTERNS: List[Tuple[re.Pattern, float]] = [
    (re.compile(r"\barquiv(e|em)-se\b"), 1.00),
    (re.compile(r"\barquivament\w+\b"), 0.75),
    (re.compile(r"\bbaixa (definitiva|na distribuic\w*|com baixa)\b"), 0.60),
    (re.compile(r"\btransito em julgado\b"), 0.50),
    (re.compile(r"\bextin(g|c)\w* do feito\b|\bextingo o processo\b"), 0.70),

    # contexto/seção
    (re.compile(r"\bsentenc\w*\b|\bdispositivo\b|\bisto posto\b|\bante o exposto\b|\bpubliqu\w*-se\b|\bintimem\w*-se\b"), 0.20),

    # moderados (nunca isolam)
    (re.compile(r"\bimprocedent\w*\b|\bprocedent\w*\b"), 0.20),
    (re.compile(r"\bdesist\w*\b"), 0.50),
    (re.compile(r"\bdeneg\w* a seguranc\w*\b"), 0.30),
]

NEGATIONS: List[re.Pattern] = [
    re.compile(r"\bn\w* arquivar\b"),
    re.compile(r"\bn\w* arquivament\w*\b"),
    re.compile(r"\bsem arquivament\w*\b"),
    re.compile(r"\bdesarquiv\w*\b"),
]

CNJ_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
FGV_RE = re.compile(r"\bfundac\w* getulio vargas\b|\bfgv\b")

THRESHOLDS = {
    "forte": 0.90,
    "provavel": 0.60,
}

# termos para highlight em HTML (case-insensitive)
HIGHLIGHT_TERMS = [
    r"Arquiv(?:e-se|em-se|amento\w*)",
    r"tr[aâ]nsito em julgado",
    r"baixa(?: definitiva| na distribui[cç][aã]o| com baixa)",
    r"extin[gç][aã]o do feito|extingo o processo",
    r"senten[cç][aã]|dispositivo|publiqu(?:e|em)-se|intimem-se",
    r"improcedent\w+|procedent\w+",
    r"deneg\w+ a seguran[cç]\w+",
    r"desist\w+",
]

@dataclass
class ArchivalScore:
    score: float
    nivel: str
    matches: List[str]
