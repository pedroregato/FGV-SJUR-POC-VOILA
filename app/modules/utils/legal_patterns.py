"""
Padrões regex compartilhados entre classificadores
"""

CITATION_PATTERNS = [
    # Padrão completo para Mandado de Segurança
    r'(?i)(?=.*intime-se)(?=.*mandado de seguranca)(?=.*(?:10 dias|dez dias|10 \(dez\) dias))(?=.*coatora[s]?)(?=.*informac[aãõo](?:es)?)',

    # Padrões explícitos de citação (com case insensitive)
    r'(?i)tipo\s*de\s*comunicacao\s*:\s*citacao',
    r'(?i)tipo\s*:\s*citacao',
    r'(?i)comunicacao\s*:\s*citacao',
    r'(?i)finalidade\s*:\s*citacao',
    r'(?i)cite-se',
    r'(?i)citar\s+a\s+parte',
    r'(?i)citacao\s+para'
]

INTIMATION_PATTERNS = [
    r'(?i)intime-se',
    r'(?i)intimem-se',
    r'(?i)comunicacao\s*:\s*intimacao'
]
