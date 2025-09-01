from typing import List, Dict
from app.rules.archival_rules import archival_rules


class ArchivalHeuristicClassifier:
    def __init__(self):
        # Não precisa mais carregar regras - usa o componente
        pass

    def classify(self, text: str) -> Dict:
        """Classifica texto usando regras centralizadas"""

        # Usa o componente para encontrar matches
        matches = archival_rules.find_matches(text, rule_types=['basic', 'proximity'])

        # Calcula score usando o componente
        total_score = archival_rules.calculate_score(matches)

        return {
            'score': total_score,
            'matches': matches,
            'has_archival_indication': total_score > 0
        }
