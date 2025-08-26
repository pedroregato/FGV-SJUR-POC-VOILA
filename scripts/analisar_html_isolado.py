# analisar_html_isolado.py
import re
import unicodedata
from bs4 import BeautifulSoup
from typing import List, Dict, Set

# =============================================================================
# LÓGICA CENTRAL (copiada e adaptada do coletor)
# =============================================================================

# Léxico e Regex (essenciais para a análise)
LEXICON_ARQ_WEIGHTS: Dict[str, int] = {
    "arquivamento": 3, "arquivado": 3, "arquivar": 3, "baixa": 2,
    "baixado": 2, "trânsito em julgado": 3, "transito em julgado": 3,
    "tjulg": 2, "extinção do processo": 2, "extinto o processo": 2,
    "extinção": 1, "preclusão": 1, "encerramento": 1, "desarquivamento": -2,
}

CNJ_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
POSITIVE_LEXICON_TERMS = {term for term, weight in LEXICON_ARQ_WEIGHTS.items() if weight > 0}


def normalize_simple(s: str) -> str:
    """Função de normalização para busca de termos."""
    if s is None: return ""
    return unicodedata.normalize("NFKD", str(s)).encode("ASCII", "ignore").decode("ASCII").lower()


def html_to_text(html: str) -> str:
    """Converte um trecho de HTML para texto puro."""
    if not html: return ""
    return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)


def split_html_into_publications(html_content: str) -> List[str]:
    """
    Divide o HTML de um recorte em uma lista de publicações individuais.
    A heurística aprimorada busca por tabelas que contenham o campo 'Publicação:'.
    """
    if not html_content or not BeautifulSoup:
        return [html_content]

    soup = BeautifulSoup(html_content, "html.parser")

    # NOVA HEURÍSTICA: Encontra todas as tags <strong> com o texto "Publicação:"
    # e retorna a tabela (<table>) que as contém.
    publication_tags = soup.find_all("strong", string=re.compile(r"Publicação:"))

    if not publication_tags:
        print(
            "AVISO: Nenhum delimitador de publicação ('<strong>Publicação:</strong>') encontrado. Analisando o HTML como um bloco único.")
        body_content = soup.body.decode_contents() if soup.body else html_content
        return [body_content]

    # Usamos um set para evitar duplicatas se uma tabela tiver múltiplos marcadores
    publication_tables = set()
    for tag in publication_tags:
        # .find_parent('table') sobe na árvore DOM até encontrar a tabela que contém a tag
        parent_table = tag.find_parent('table')
        if parent_table:
            publication_tables.add(parent_table)

    if not publication_tables:
        print("AVISO: Encontrado o texto 'Publicação:', mas não dentro de uma tabela. Analisando como bloco único.")
        return [soup.body.decode_contents() if soup.body else html_content]

    return [str(table) for table in publication_tables]


def process_publication(pub_html: str) -> Dict:
    """
    Processa uma única publicação (HTML) e retorna seus dados analisados.
    """
    pub_text = html_to_text(pub_html)
    pub_text_norm = normalize_simple(pub_text)

    cnjs_found: Set[str] = set(CNJ_RE.findall(pub_text))
    hits_found: Set[str] = {term for term in LEXICON_ARQ_WEIGHTS if term in pub_text_norm}
    score = sum(LEXICON_ARQ_WEIGHTS[term] for term in hits_found)

    # Verifica se algum termo POSITIVO do léxico está na publicação
    has_positive_indication = any(p_term in pub_text_norm for p_term in POSITIVE_LEXICON_TERMS)

    # Um CNJ tem indício se a publicação tem um score positivo E um termo positivo
    cnjs_with_indication: Set[str] = cnjs_found if has_positive_indication and score > 0 else set()

    return {
        "cnjs": sorted(list(cnjs_found)),
        "cnjs_with_indication": sorted(list(cnjs_with_indication)),
        "score": score,
        "hits": sorted(list(hits_found)),
        "has_positive_indication": has_positive_indication
    }


# =============================================================================
# FUNÇÃO PRINCIPAL DO SCRIPT
# =============================================================================
def analisar_arquivo_html(caminho_do_arquivo: str):
    """
    Função principal que lê, processa e exibe a análise de um arquivo HTML.
    """
    try:
        with open(caminho_do_arquivo, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo não encontrado em '{caminho_do_arquivo}'")
        return

    print("-" * 80)
    print(f"Analisando o arquivo: {caminho_do_arquivo}")
    print("-" * 80)

    # 1. Divide o recorte em publicações
    publications_html = split_html_into_publications(html_content)
    print(f"Encontradas {len(publications_html)} publicações no recorte.\n")

    # 2. Processa cada publicação e agrega os resultados
    total_score = 0
    all_cnjs: Set[str] = set()
    all_cnjs_with_indication: Set[str] = set()

    for i, pub_html in enumerate(publications_html):
        pub_result = process_publication(pub_html)

        # Agrega os resultados
        total_score += pub_result["score"]
        all_cnjs.update(pub_result["cnjs"])
        all_cnjs_with_indication.update(pub_result["cnjs_with_indication"])

        # Exibe a análise da publicação individual
        print(f"--- Publicação #{i + 1} ---")
        print(f"  Score da Publicação: {pub_result['score']}")
        print(f"  Hits Encontrados: {pub_result['hits'] if pub_result['hits'] else 'Nenhum'}")
        print(f"  Contém Indício Positivo? {'Sim' if pub_result['has_positive_indication'] else 'Não'}")
        print(f"  CNJs nesta Publicação: {pub_result['cnjs'] if pub_result['cnjs'] else 'Nenhum'}")
        print(
            f"  CNJs com Indício (nesta pub): {pub_result['cnjs_with_indication'] if pub_result['cnjs_with_indication'] else 'Nenhum'}")
        print("-" * 25 + "\n")

    # 3. Exibe o resultado final agregado
    print("=" * 80)
    print("RESULTADO FINAL AGREGADO PARA O RECORTE INTEIRO")
    print("=" * 80)
    print(f"Score Total do Recorte: {total_score}")
    print(f"\nColuna 'processos' (todos os CNJs únicos encontrados):")
    print(sorted(list(all_cnjs)))
    print(f"\nColuna 'indicios' (apenas CNJs de publicações com indícios positivos):")
    print(sorted(list(all_cnjs_with_indication)))
    print("-" * 80)


if __name__ == "__main__":
    # =================================================================
    # INSTRUÇÃO: Altere o caminho do arquivo HTML que você quer testar
    # =================================================================
    # Exemplo de uso:
    # caminho_html_para_teste = "caminho/para/seu/arquivo.html"
    # Use um arquivo que você sabe que deveria ter resultados diferentes.

    # Para facilitar, vamos usar o HTML que você compartilhou inicialmente.
    # Salvei ele como 'exemplo_recorte.html' na raiz do projeto.
    # Se você salvou com outro nome, apenas altere a linha abaixo.
    caminho_html_para_teste = r"F:\FGV-SJUR\sjur-poc-voila\outputs\html\2025-03-24_125401__Publicações do dia _ 24_03_2025 _ Jornal RIO DE JANEIRO.html"

    # Verifica se o arquivo de exemplo existe antes de rodar
    import os

    if not os.path.exists(caminho_html_para_teste):
        print(f"ERRO: O arquivo de teste '{caminho_html_para_teste}' não foi encontrado.")
        print(
            "Por favor, salve o HTML que você compartilhou no início da nossa conversa com este nome na raiz do projeto, ou altere o caminho no script.")
    else:
        analisar_arquivo_html(caminho_html_para_teste)

