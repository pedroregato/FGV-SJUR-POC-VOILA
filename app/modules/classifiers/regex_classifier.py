"""
Módulo para classificação baseada em regex
"""
import re
from dataclasses import dataclass
from typing import Optional
from app.modules.utils.legal_patterns import CITATION_PATTERNS, INTIMATION_PATTERNS


@dataclass
class RegexClassificationResult:
    classification: Optional[str]  # "citação", "intimação" ou None
    matched_pattern: Optional[str]
    confidence: float  # 0-1


class RegexLegalClassifier:
    def __init__(self):
        self.citation_patterns = CITATION_PATTERNS
        self.intimation_patterns = INTIMATION_PATTERNS

    def classify(self, text: str) -> RegexClassificationResult:
        text_lower = text.lower()
        tem_processo = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', text)

        matched_citation = None
        for pattern in self.citation_patterns:
            if re.search(pattern, text_lower):
                matched_citation = pattern
                break

        matched_intimation = None
        for pattern in self.intimation_patterns:
            if re.search(pattern, text_lower):
                matched_intimation = pattern
                break

        # Precedência: citação > intimação
        if matched_citation and tem_processo:
            return RegexClassificationResult("citação", matched_citation, 0.95)
        elif matched_intimation:
            return RegexClassificationResult("intimação", matched_intimation, 0.8)
        else:
            return RegexClassificationResult(None, None, 0)

# Padrões podem ser importados de:
# from ..prompts.prompt_definitions import CITATION_PROMPT