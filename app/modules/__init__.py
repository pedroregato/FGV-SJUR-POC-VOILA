# modules/__init__.py
from .classifiers.deepseek_classifier import DeepSeekLegalClassifier
from .classifiers.gpt35_classifier import GPT35LegalClassifier
from .classifiers.gemini_classifier import GeminiLegalClassifier
from .classifiers.regex_classifier import RegexLegalClassifier, RegexClassificationResult
# from .classifiers.llama_classifier import LlamaLocalClassifier
from .utilitarios import inicializar_base_avaliacoes, registrar_avaliacao
from .prompts.classification_definitions import carregar_prompt_custom
from .search_tokens import (
    highlight_text,
    count_occurrences,
    extrair_metadados,
    ExtractedDeadline,
    ParteReu,
    extract_partes_reus
)

__all__ = [
    'DeepSeekLegalClassifier',
    'GPT35LegalClassifier',
    'RegexLegalClassifier',
    'GeminiLegalClassifier',
    'RegexClassificationResult',
    ## 'LlamaLocalClassifier',
    'carregar_prompt_custom',
    'inicializar_base_avaliacoes',
    'registrar_avaliacao',
    'highlight_text',
    'count_occurrences',
    'extrair_metadados',
    'ExtractedDeadline',
    'ParteReu',
    'extract_partes_reus'
]