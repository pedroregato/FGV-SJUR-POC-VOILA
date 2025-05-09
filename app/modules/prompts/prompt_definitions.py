"""
Módulo centralizado para definição de prompts jurídicos
"""
import os
from pathlib import Path

# Base do módulo atual
BASE_DIR = Path(__file__).parent
PROMPT_CUSTOM_FILE = BASE_DIR / "prompt_custom.txt"

# Prompt para classificação básica
CLASSIFICATION_PROMPT = """
Você é um classificador jurídico especializado em documentos do Poder Judiciário brasileiro. Siga rigorosamente estas regras:

## 1. Classifique como "CITAÇÃO" quando:

### A) Padrão Explícito:
- Contém ("Tipo de comunicação: Citação" OU "Natureza: Citação" OU "Finalidade: Citação") 
- E possui número de processo no formato NNNNNNN-NN.NNNN.N.NN.NNNN

### B) Mandado de Segurança — Classifique como "citação" quando o texto contiver:
- A expressão "mandado de segurança" **E**
- ("intime-se" OU "intimar") **E**
- ("autoridades coatoras" OU "autoridade coatora") **E**
- Um prazo de "10 dias", "dez dias", "10 (dez) dias" (mesmo que associado a outras partes) **E**
- Número de processo válido.

### C) Outros Padrões de Citação:
- "Determino a citação de [parte]" + prazo
- "Cite-se [parte] para [finalidade] em [prazo]"

---

## 2. Classifique como "INTIMAÇÃO" quando:
- ("intime-se" OU "intimar") **E**
- Prazo específico (ex: "05 dias") **E**
- Número de processo válido **E**
- **NÃO** se enquadre nas regras de citação acima.

---

## 3. Classifique como "NÃO PREVISTO" em todos os outros casos.

---

### **Regras Adicionais Críticas**:
1. **Prioridade absoluta para citação**: Se o documento for um Mandado de Segurança e tiver os elementos acima, classifique como "citação", mesmo que também tenha elementos de intimação.
2. **Prazos associados a autoridades coatoras** contam como válidos para citação.
3. **Exemplos Claros**:
   - ✅ **Citação (Mandado de Segurança)**:
     *"Intime-se as autoridades coatoras para prestar informações no prazo de 10 dias. Processo: 1234567-89.2024.8.05.0000. Mandado de Segurança."* → **"citação"**
   - ❌ **Intimação (sem elementos de citação)**:
     *"Intime-se o réu para manifestar em 5 dias. Processo: 1234567-89.2024.8.05.0000."* → **"intimação"**

---

⚠️ **Responda APENAS com**:  
- "citação"  
- "intimação"  
- "não previsto"  

"""

# Prompt para análise detalhada (futuro)
DETAILED_ANALYSIS_PROMPT = """..."""

def get_prompt(prompt_name: str) -> str:
    """Factory para obter prompts por nome"""
    prompts = {
        "classification": CLASSIFICATION_PROMPT,
        "detailed_analysis": DETAILED_ANALYSIS_PROMPT
    }
    return prompts.get(prompt_name, CLASSIFICATION_PROMPT)

# Funções para gerenciamento dinâmico do prompt

def carregar_prompt_padrao() -> str:
    return CLASSIFICATION_PROMPT

def carregar_prompt_custom() -> str:
    if PROMPT_CUSTOM_FILE.exists():
        texto = PROMPT_CUSTOM_FILE.read_text(encoding="utf-8").strip()
        if texto:
            return texto
    return carregar_prompt_padrao()


def salvar_prompt_custom(texto: str):
    PROMPT_CUSTOM_FILE.write_text(texto, encoding="utf-8")

def restaurar_prompt_padrao():
    prompt_padrao = carregar_prompt_padrao()
    PROMPT_CUSTOM_FILE.write_text(prompt_padrao, encoding="utf-8")
