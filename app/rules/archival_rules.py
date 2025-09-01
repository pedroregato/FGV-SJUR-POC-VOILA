import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


class ArchivalRulesManager:
    """
    Componente centralizado para gerenciar todas as regras de detecção de arquivamento.
    Garante que classificador e visualização usem exatamente as mesmas regras.
    """

    def __init__(self, rules_file: str = None):
        self.rules_file = rules_file or Path(__file__).parent / "archival_heuristic_rules.json"
        self._rules = None
        self._compiled_patterns = None

    @property
    def rules(self) -> Dict:
        """Carrega regras do JSON (lazy loading)"""
        if self._rules is None:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                self._rules = json.load(f)
        return self._rules

    @property
    def compiled_patterns(self) -> Dict[str, re.Pattern]:
        """Retorna patterns regex compilados (cache)"""
        if self._compiled_patterns is None:
            self._compiled_patterns = {}
            for rule_id, rule_data in self.rules.items():
                try:
                    self._compiled_patterns[rule_id] = re.compile(
                        rule_data['pattern'],
                        re.IGNORECASE
                    )
                except re.error as e:
                    print(f"Erro ao compilar regex '{rule_id}': {e}")
        return self._compiled_patterns

    def get_basic_patterns(self) -> Dict[str, Dict]:
        """Retorna apenas patterns básicos"""
        return {k: v for k, v in self.rules.items()
                if v.get('type', 'basic') == 'basic'}

    def get_proximity_patterns(self) -> Dict[str, Dict]:
        """Retorna apenas patterns de proximidade"""
        return {k: v for k, v in self.rules.items()
                if v.get('type') == 'proximity'}

    def get_cnj_pattern(self) -> str:
        """Retorna pattern para CNJ"""
        return self.rules.get('cnj', {}).get('pattern', r'\b\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}\b')

    def find_matches(self, text: str, rule_types: List[str] = None) -> List[Dict]:
        """
        Encontra todos os matches no texto usando as regras especificadas.

        Args:
            text: Texto para analisar
            rule_types: Lista de tipos ['basic', 'proximity'] ou None para todos

        Returns:
            Lista de matches com detalhes completos
        """
        matches = []

        for rule_id, pattern in self.compiled_patterns.items():
            rule_data = self.rules[rule_id]

            # Filtra por tipo se especificado
            if rule_types and rule_data.get('type', 'basic') not in rule_types:
                continue

            # Encontra matches
            for match in pattern.finditer(text):
                matches.append({
                    'rule_id': rule_id,
                    'rule_type': rule_data.get('type', 'basic'),
                    'description': rule_data.get('description', rule_id),
                    'match_text': match.group(0),
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'score': rule_data.get('score', 1.0),
                    'pattern': rule_data['pattern']
                })

        return matches

    def calculate_score(self, matches: List[Dict]) -> float:
        """Calcula score total baseado nos matches"""
        return sum(match['score'] for match in matches)

    def format_hits_for_display(self, matches: List[Dict]) -> str:
        """Formata matches para exibição no CSV"""
        formatted = []
        for match in matches:
            formatted.append(f"{match['description']} (texto: \"{match['match_text']}\")")
        return "; ".join(formatted)

    def extract_hit_texts(self, formatted_hits: str) -> List[str]:
        """Extrai textos dos hits formatados (para compatibilidade)"""
        return re.findall(r'texto: "([^"]+)"', formatted_hits)


# Instância global (singleton)
archival_rules = ArchivalRulesManager()
