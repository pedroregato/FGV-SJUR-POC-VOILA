# app/rules/archival_rules.py (VERSÃO CORRIGIDA - GARANTE A COMPILAÇÃO)

import json
from pathlib import Path
import regex as re


class SjurRulesManager:
    def __init__(self):
        self.rules_dir = Path(__file__).parent
        self.mandatory_rules_file = self.rules_dir / "mandatory_rules.json"
        self.determinant_rules_file = self.rules_dir / "determinant_rules.json"
        self.context_rules_file = self.rules_dir / "context_rules.json"

        self.mandatory_rules = {}
        self.determinant_rules = {}
        self.context_rules = {}
        self._rules_loaded = False

    # app/rules/archival_rules.py (CORREÇÃO CRÍTICA)

    def _load_rules_from_file(self, file_path: Path) -> dict:
        """Lê um arquivo JSON de regras e compila os padrões de regex."""
        if not file_path.exists():
            print(f"AVISO: Arquivo de regras não encontrado: {file_path}")
            return {}

        with open(file_path, "r", encoding="utf-8") as f:
            rules_data = json.load(f)

        # >>>>> CORREÇÃO: Cria uma cópia profunda para não modificar o original <<<<<
        compiled_rules = {}
        for rule_id, spec in rules_data.items():
            spec_copy = spec.copy()  # Cria cópia para não modificar o original
            if "pattern" in spec_copy:
                try:
                    # Adiciona a chave '_compiled_regex' à cópia
                    spec_copy["_compiled_regex"] = re.compile(spec_copy["pattern"], re.DOTALL | re.IGNORECASE)
                except re.error as e:
                    print(f"AVISO: Erro ao compilar a regra '{rule_id}' em {file_path.name}: {e}")
                    spec_copy["_compiled_regex"] = None
            compiled_rules[rule_id] = spec_copy

        return compiled_rules

    def load_all_rules(self, force_reload: bool = False):
        """Carrega todas as categorias de regras dos seus respectivos arquivos JSON."""
        if self._rules_loaded and not force_reload:
            return

        self.mandatory_rules = self._load_rules_from_file(self.mandatory_rules_file)
        self.determinant_rules = self._load_rules_from_file(self.determinant_rules_file)
        self.context_rules = self._load_rules_from_file(self.context_rules_file)

        self._rules_loaded = True

    def check_mandatory_rules(self, text: str) -> bool:
        """Verifica se todas as regras mandatórias habilitadas são satisfeitas."""
        if not self.mandatory_rules: return True

        for spec in self.mandatory_rules.values():
            if spec.get("enabled", False) and spec.get("_compiled_regex"):
                if not spec["_compiled_regex"].search(text):
                    return False  # Se uma regra mandatória falhar, retorna False imediatamente
        return True

    def calculate_score(self, text: str) -> dict:
        """Calcula o score total com base nas regras determinantes."""
        total_score = 0.0
        hits = {}
        if not self.determinant_rules: return {"score": total_score, "hits": hits}

        for rule_id, spec in self.determinant_rules.items():
            if spec.get("enabled", False) and spec.get("_compiled_regex"):
                matches = spec["_compiled_regex"].findall(text)
                if matches:
                    count = len(matches)
                    hits[rule_id] = count
                    total_score += spec.get("score", 0.0) * count

        return {"score": total_score, "hits": hits}

    def extract_context_data(self, text: str) -> dict:
        """Extrai metadados e encontra hits de contexto."""
        metadata = {}
        context_hits = {}
        if not self.context_rules: return {"metadata": metadata, "context_hits": context_hits}

        for rule_id, spec in self.context_rules.items():
            if spec.get("enabled", False) and spec.get("_compiled_regex"):
                if spec.get("type") == "metadata_extractor" and "target_field" in spec:
                    match = spec["_compiled_regex"].search(text)
                    if match:
                        # Pega o primeiro grupo de captura, se existir, senão a correspondência inteira
                        value = match.group(1) if match.groups() else match.group(0)
                        metadata[spec["target_field"]] = value.strip()
                elif spec.get("type") == "highlight":
                    matches = spec["_compiled_regex"].findall(text)
                    if matches:
                        context_hits[rule_id] = len(matches)

        return {"metadata": metadata, "context_hits": context_hits}


# Cria a instância singleton que será usada em toda a aplicação
sjur_rules = SjurRulesManager()
