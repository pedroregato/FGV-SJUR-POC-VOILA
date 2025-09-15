# app/modules/analysis/publication_analyzer.py

import re
from typing import Dict, List


class PublicationMetadataExtractor:
    """
    Isola a lógica de extração de metadados (Tribunal, Secretaria, etc.)
    do texto de uma publicação.
    """

    def __init__(self):
        # Pré-compila os Regex para performance
        self._re_data = re.compile(r"Data\s+de\s+disponibiliza[cç][aã]o\s*:\s*([0-3]?\d[-/][01]?\d[-/][12]\d{3})",
                                   re.IGNORECASE)
        self._re_orgao = re.compile(
            r"Orga[oã]\s*:\s*(.+?)(?:\s+(?:Data\s+de\s+disponibiliza[cç][aã]o|Tipo\s+de\s+comunica[cç][aã]o|Meio|Inteiro\s+teor)\b|[\r\n]|$)",
            re.IGNORECASE)
        self._re_trib = re.compile(
            r"(TRIBUNAL\s+(?:REGIONAL\s+DO\s+TRABALHO|DE\s+JUSTI[ÇC]A|REGIONAL\s+FEDERAL)[^\n\r]+)", re.IGNORECASE)
        self._re_trib_check = re.compile(r"\bTRIBUNAL\b", re.IGNORECASE)
        self._re_secretaria_check = re.compile(r"\b(VARA|SECRETARIA|TURMA|C[âa]MARA)\b", re.IGNORECASE)

    def extract(self, pub_text: str) -> Dict[str, str]:
        """
        Extrai metadados de um texto e retorna um dicionário.
        """
        if not pub_text:
            return {"tribunal": "", "secretaria": "", "data_publicacao": ""}

        m_data = self._re_data.search(pub_text)
        data_publicacao = m_data.group(1).strip() if m_data else ""

        m_orgao = self._re_orgao.search(pub_text)
        orgao_val = m_orgao.group(1).strip() if m_orgao else ""

        m_trib = self._re_trib.search(pub_text)
        tribunal = m_trib.group(1).strip() if m_trib else ""

        secretaria = ""
        if orgao_val:
            if self._re_trib_check.search(orgao_val):
                tribunal = tribunal or orgao_val
            else:
                secretaria = orgao_val

        return {"tribunal": tribunal, "secretaria": secretaria, "data_publicacao": data_publicacao}


class ArchivalScorer:
    """
    Calcula o score de arquivamento e o nível de classificação
    com base nos matches encontrados e nas regras de thresholds.
    """

    def calculate(self, matches: List[Dict], rules_manager: 'ArchivalRulesManager') -> Dict[str, any]:
        """
        Calcula o score e o nível.
        """
        score = rules_manager.calculate_score(matches)

        thresholds = rules_manager.rules.get("thresholds", {"forte": 0.9, "provavel": 0.6})
        thr_forte = float(thresholds.get("forte", 0.9))
        thr_prov = float(thresholds.get("provavel", 0.6))

        if score >= thr_forte:
            level = "forte"
        elif score >= thr_prov:
            level = "provável"
        elif score > 0:
            level = "fraco"
        else:
            level = ""

        return {"score": score, "level": level}


# Instâncias globais (singletons) para serem importadas
metadata_extractor = PublicationMetadataExtractor()
archival_scorer = ArchivalScorer()
