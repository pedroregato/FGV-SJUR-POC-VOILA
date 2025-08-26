# app/modules/classifiers/archival_regex_classifier.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
import re

try:
    # se existir um BaseClassifier no projeto, herdamos (não obrigatório)
    from .base_classifier import BaseClassifier  # type: ignore
except Exception:
    class BaseClassifier:  # fallback leve
        pass

from app.modules.utils.archival_patterns import (
    normalize, PATTERNS, NEGATIONS, CNJ_RE, FGV_RE, THRESHOLDS, HIGHLIGHT_TERMS
)
from app.modules.utils.html_highlight import highlight_html

@dataclass
class SerdonClip:
    processo: Optional[str]
    orgao: Optional[str]
    data_disponibilizacao: Optional[str]
    tipo_comunicacao: Optional[str]
    link_inteiro_teor: Optional[str]
    texto_bruto: str              # obrigatório
    html_original: Optional[str] = None

@dataclass
class ArchivalResult:
    processo: Optional[str]
    orgao: Optional[str]
    data_disponibilizacao: Optional[str]
    tipo_comunicacao: Optional[str]
    link_inteiro_teor: Optional[str]
    score: float
    nivel: str
    matches: List[str]
    snippet: str
    html: str

META_GRABS = {
    "orgao": re.compile(r"(?i)Orgao\s*:\s*(.+?)(?:\s{2,}|\n|$)"),
    "data": re.compile(r"(?i)Data de disponibilizac\w*\s*:\s*(.+?)(?:\s{2,}|\n|$)"),
    "tipo": re.compile(r"(?i)Tipo de comunicac\w*\s*:\s*(.+?)(?:\s{2,}|\n|$)"),
    "link": re.compile(r"(?i)Inteiro teor\s*:\s*(\S+)"),
}

def extract_meta_from_text(raw: str) -> Dict[str, Optional[str]]:
    meta: Dict[str, Optional[str]] = {"processo": None, "orgao": None, "data": None, "tipo": None, "link": None}
    cnj = CNJ_RE.findall(raw)
    meta["processo"] = cnj[0] if cnj else None
    m = META_GRABS["orgao"].search(raw); meta["orgao"] = m.group(1).strip() if m else None
    m = META_GRABS["data"].search(raw); meta["data"] = m.group(1).strip() if m else None
    m = META_GRABS["tipo"].search(raw); meta["tipo"] = m.group(1).strip() if m else None
    m = META_GRABS["link"].search(raw); meta["link"] = m.group(1).strip() if m else None
    return meta

def score_text(raw: str, require_fgv: bool = False) -> Tuple[float, List[str], str]:
    norm = normalize(raw)
    # proteger "arquivo(s)" (file) para não confundir com arquivamento
    norm = re.sub(r"\barquivo(s)?\b", " ARQFILE ", norm)

    if require_fgv and not FGV_RE.search(norm):
        return 0.0, [], "Nao identificado"

    neg = any(p.search(norm) for p in NEGATIONS)
    matches: List[str] = []
    score = 0.0

    for rx, w in PATTERNS:
        all_hits = rx.findall(norm)
        if all_hits:
            matches.append(rx.pattern)
            score += w * len(all_hits)

    # proximidade: trânsito em julgado até 300 chars de arquive(m)-se
    if re.search(r"\btransito em julgado\b.{0,300}\barquiv(e|em)-se\b", norm):
        score += 0.20

    if neg:
        score = max(0.0, score - 1.0)

    if score >= THRESHOLDS["forte"]:
        nivel = "Arquivamento forte"
    elif score >= THRESHOLDS["provavel"]:
        nivel = "Arquivamento provável"
    else:
        nivel = "Não identificado"

    return score, matches, nivel

def make_snippet(raw: str) -> str:
    m = re.search(r"(.{0,80}(?i)(arquiv\w+|transito em julgado|baixa|extin\w+).{0,80})", raw)
    return (m.group(1).strip() if m else raw[:160]).replace("\n", " ")

class ArchivalRegexClassifier(BaseClassifier):
    """
    Classificador heurístico baseado em regex e pesos.
    """
    NAME = "archival_regex"

    def classify_clip(self, clip: SerdonClip, require_fgv: bool = False) -> ArchivalResult:
        score, pats, nivel = score_text(clip.texto_bruto, require_fgv=require_fgv)
        html_src = clip.html_original or clip.texto_bruto
        html_out = highlight_html(html_src, HIGHLIGHT_TERMS)
        snippet = make_snippet(clip.texto_bruto)

        # preferir metadados já prontos; senão, extrair do texto
        processo = clip.processo
        orgao = clip.orgao
        data = clip.data_disponibilizacao
        tipo = clip.tipo_comunicacao
        link = clip.link_inteiro_teor

        if not (processo and orgao and data and tipo and link):
            meta = extract_meta_from_text(clip.texto_bruto)
            processo = processo or meta["processo"]
            orgao = orgao or meta["orgao"]
            data = data or meta["data"]
            tipo = tipo or meta["tipo"]
            link = link or meta["link"]

        return ArchivalResult(
            processo=processo, orgao=orgao, data_disponibilizacao=data,
            tipo_comunicacao=tipo, link_inteiro_teor=link,
            score=score, nivel=nivel, matches=pats,
            snippet=snippet, html=html_out
        )

    # compat: se o pipeline chamar .classify(text) puramente
    def classify(self, text: str) -> dict:
        fake_clip = SerdonClip(
            processo=None, orgao=None, data_disponibilizacao=None,
            tipo_comunicacao=None, link_inteiro_teor=None, texto_bruto=text
        )
        res = self.classify_clip(fake_clip)
        return {
            "label": res.nivel,
            "score": res.score,
            "matches": res.matches,
            "snippet": res.snippet,
        }
