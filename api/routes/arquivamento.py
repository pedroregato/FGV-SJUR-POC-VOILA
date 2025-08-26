# api/routes/arquivamento.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.modules.classifiers.archival_regex_classifier import ArchivalRegexClassifier, SerdonClip

router = APIRouter(prefix="/arquivamento", tags=["arquivamento"])
clf = ArchivalRegexClassifier()

class ClipIn(BaseModel):
    processo: Optional[str] = None
    orgao: Optional[str] = None
    data_disponibilizacao: Optional[str] = None
    tipo_comunicacao: Optional[str] = None
    link_inteiro_teor: Optional[str] = None
    texto_bruto: str
    html_original: Optional[str] = None

class ClipOut(BaseModel):
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

@router.post("/scan", response_model=List[ClipOut])
def scan_clips(clips: List[ClipIn], require_fgv: bool = False):
    out: List[ClipOut] = []
    for c in clips:
        res = clf.classify_clip(SerdonClip(**c.model_dump()), require_fgv=require_fgv)
        out.append(ClipOut(
            processo=res.processo, orgao=res.orgao, data_disponibilizacao=res.data_disponibilizacao,
            tipo_comunicacao=res.tipo_comunicacao, link_inteiro_teor=res.link_inteiro_teor,
            score=res.score, nivel=res.nivel, matches=res.matches, snippet=res.snippet, html=res.html
        ))
    return out
