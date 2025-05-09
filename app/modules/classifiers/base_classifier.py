"""
Classe base para todos os classificadores
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ClassificationResult:
    classification: str
    status: str
    method: str
    confidence: float

class BaseLegalClassifier(ABC):
    def __init__(self):
        self.classifier_type = "base"

    @abstractmethod
    def classify_text(self, text: str) -> ClassificationResult:
        pass