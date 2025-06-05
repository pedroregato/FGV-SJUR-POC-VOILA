from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.modules.classifiers.deepseek_classifier import DeepSeekLegalClassifier
from app.modules.extractors.deepseek_extractor import extrair_partes_processo
from app.modules.extractors.metadados_extractor import extrair_metadados_publicacao

router = APIRouter()

class ClassificacaoInput(BaseModel):
    texto: str

class ClassificacaoOutput(BaseModel):
    classificacao: str
    justificativa: Optional[str]
    status: str

class DetalhesInput(BaseModel):
    texto: str

class DetalhesOutput(BaseModel):
    partes: Dict[str, List[str]]
    metadados: Dict[str, Any]
    status: str

classificador = DeepSeekLegalClassifier()

@router.post("/recortes/classificar", response_model=ClassificacaoOutput)
def classificar_publicacao(payload: ClassificacaoInput):
    if not payload.texto.strip():
        return ClassificacaoOutput(
            classificacao="não previsto",
            justificativa=None,
            status="erro: texto vazio"
        )
    resultado = classificador.classify_text(payload.texto)
    return ClassificacaoOutput(
        classificacao=resultado.classification,
        justificativa=resultado.justification,
        status=resultado.status
    )

@router.post("/recortes/extrair_detalhes", response_model=DetalhesOutput)
def extrair_detalhes(payload: DetalhesInput):
    partes = extrair_partes_processo(payload.texto)
    metadados = extrair_metadados_publicacao(payload.texto)

    return DetalhesOutput(
        partes={
            "autor": partes.autor,
            "reu": partes.reu,
            "interessados": partes.interessados,
            "advogados_autor": partes.advogados_autor,
            "advogados_reu": partes.advogados_reu
        },
        metadados=metadados or {},
        status="sucesso"
    )
