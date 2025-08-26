# app_arquivamento_streamlit.py
# — Scanner de Indícios de Arquivamento (SJUR) • 3 abas • popup (overlay) com fundo branco

from __future__ import annotations
from pathlib import Path
import json
import re
import urllib.parse
import html
import logging as _logging

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import matplotlib.pyplot as plt

try:
    from bs4 import BeautifulSoup, NavigableString

    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

# -----------------------------------------------------------------------------
# Configurações gerais
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Scanner de Arquivamento (SJUR)", layout="wide")
st.title("📄 Scanner de Indícios de Arquivamento — SJUR")

# Silenciar ruído do hash fallback, caso apareça em ambientes com listas no DF
_logging.getLogger("streamlit.runtime.caching.hashing").setLevel(_logging.ERROR)

# -----------------------------------------------------------------------------
# Sidebar — fontes e filtros básicos globais
# -----------------------------------------------------------------------------
default_csv = st.sidebar.text_input("Caminho do CSV", value="outputs/arquivamento.csv")
html_dir = st.sidebar.text_input("Pasta de HTML (opcional)", value="outputs/html")
jsonl_path = st.sidebar.text_input("JSONL (opcional, para enriquecer HTML)", value="outputs/recortes_amostra.jsonl")
uploaded = st.sidebar.file_uploader("...ou carregue um CSV (separador ';')", type=["csv"])


# -----------------------------------------------------------------------------
# Query params helpers (compat)
# -----------------------------------------------------------------------------
def _strip_background_decls(style_str: str) -> str:
    """Remove 'background', 'background-color' e 'background-image' de um style inline."""
    if not style_str:
        return style_str
    # remove qualquer 'background[ -color|-image]: ...;'
    style_str = re.sub(r'background(?:-color|-image)?\s*:\s*[^;]+;?', '', style_str, flags=re.I)
    # compacta ; ;
    style_str = re.sub(r';\s*;', ';', style_str)
    return style_str.strip()


def _force_white_background_dom(soup):
    """Limpa atributos/estilos de fundo e força branco em toda a página."""
    # 1) remove bgcolor e backgrounds inline
    for tag in soup.find_all(True):
        if tag.has_attr('bgcolor'):
            del tag['bgcolor']
        if tag.has_attr('background'):
            del tag['background']
        if tag.has_attr('style'):
            new_style = _strip_background_decls(tag['style'])
            if new_style:
                tag['style'] = new_style
            else:
                del tag['style']

    # 2) injeta CSS branco (mantendo cores dos <mark>)
    css = """
    <style>
      /* Realces mais fortes */
      mark.sjur-hit { 
        background: #ffeb3b !important; 
        padding: 0 .2em !important;
        border-radius: 3px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        color: #000 !important;
        font-weight: bold !important;
        border: 1px solid #ffc107 !important;
      }

      mark.sjur-cnj { 
        background: #2196f3 !important; 
        padding: 0 .2em !important;
        border-radius: 3px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        color: white !important;
        font-weight: bold !important;
        border: 1px solid #1976d2 !important;
      }

      /* Realce especial para FUNDACAO GETULIO VARGAS */
      mark.sjur-fgv {
        background: #ff4444 !important;
        color: white !important;
        padding: 0 .2em !important;
        border-radius: 3px !important;
        font-weight: bold !important;
        border: 1px solid #cc0000 !important;
      }

      /* Realce especial para PRAZO */
      mark.sjur-prazo {
        background: #1565c0 !important;
        color: white !important;
        padding: 0 .2em !important;
        border-radius: 3px !important;
        font-weight: bold !important;
        border: 1px solid #0d47a1 !important;
      }

      /* Melhorar legibilidade geral */
      * {
        background: white !important;
        color: #333 !important;
      }

      /* Forçar fundo branco em todos os elementos */
      div, p, span, td, tr, table, li, ul, ol {
        background: white !important;
        color: #333 !important;
      }
    </style>
    """

    head = soup.find("head")
    style_tag = BeautifulSoup(css, "html.parser")
    if head:
        head.append(style_tag)
    else:
        soup.insert(0, style_tag)


def _get_query_param(key: str, default=None):
    try:
        qp = st.query_params  # Streamlit >= 1.33
        return qp.get(key, default)
    except Exception:
        pass
    try:
        qpe = st.experimental_get_query_params()
        vals = qpe.get(key)
        if vals:
            return vals[0]
        return default
    except Exception:
        return default


def _set_query_params(**kwargs):
    try:
        st.query_params = kwargs
    except Exception:
        st.experimental_set_query_params(**kwargs)


# -----------------------------------------------------------------------------
# Helpers para cache/hash do Streamlit (listas -> tuplas)
# -----------------------------------------------------------------------------
def _make_hashable_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    cols_seq = [c for c in ("processos_list", "processos_list_ctx", "hits_norm") if c in df.columns]
    if not cols_seq:
        return df
    df = df.copy()
    for c in cols_seq:
        df[c] = df[c].apply(lambda x: tuple(x) if isinstance(x, list) else x)
    return df


# -----------------------------------------------------------------------------
# Parse / enriquecimento
# -----------------------------------------------------------------------------
CNJ_REGEX = re.compile(
    r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b"
)


def _cnj_regex():
    """
    CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
    Aceita hífen/en-dash, pontos opcionais, espaços ocasionais:
    0000000-00.0000.0.00.0000
    0000000 – 00 0000 0 00 0000
    """
    pat = r"""
      (?<!\d)                       # não colado a outro dígito à esquerda
      (?:\d{7})                     # NNNNNNN
      \s*[-–—]?\s*                  # hífen/en-dash opcional
      (?:\d{2})                     # DD
      (?:\s*[.\s]\s*)?              # separador flexível
      (?:\d{4})                     # AAAA
      (?:\s*[.\s]\s*)?              # .
      (?:\d)                        # J
      (?:\s*[.\s]\s*)?              # .
      (?:\d{2})                     # TR
      (?:\s*[.\s]\s*)?              # .
      (?:\d{4})                     # OOOO
      (?!\d)                        # não colado a outro dígito à direita
    """
    return re.compile(pat, re.I | re.X)


def parse_hits_terms(hits: str) -> list[str]:
    """
    Converte a string 'hits' do CSV (ex.: '+3:arquivament,+3:arquivado,...')
    numa lista de termos únicos e normalizados.
    """
    if not hits:
        return []
    out = []
    for chunk in str(hits).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            _, term = chunk.split(":", 1)
        else:
            term = chunk
        term = term.strip()
        if term and term not in out:
            out.append(term)
    return out


def ensure_processos_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante que temos a coluna 'processos' com apenas CNJs que possuem indícios de arquivamento.
    Preferências:
      1) 'processos' (já existente) - mantemos
      2) 'indicios' (nova coluna com apenas CNJs com indícios positivos)
      3) 'processos_list_ctx' (lista de dicts com {'cnj':..., 'context':...})
      4) 'processos_list'     (lista de CNJs já filtrada no coletor)
    """
    df = df.copy()

    # Se já existe a coluna processos, mantemos
    if "processos" in df.columns:
        return df

    # PRIORIDADE 1: Use a nova coluna 'indicios' se existir
    if "indicios" in df.columns:
        df["processos"] = df["indicios"]
        return df

    if "processos_list_ctx" in df.columns and len(df):
        proc_series = []
        for row in df["processos_list_ctx"]:
            cnjs = []
            if isinstance(row, (list, tuple)):
                for item in row:
                    if isinstance(item, dict) and "cnj" in item:
                        cnj = str(item["cnj"]).strip()
                        if cnj and cnj not in cnjs:
                            cnjs.append(cnj)
            proc_series.append(", ".join(cnjs))
        df["processos"] = proc_series
        return df

    if "processos_list" in df.columns and len(df):
        proc_series = []
        for row in df["processos_list"]:
            if isinstance(row, (list, tuple)):
                cnjs = [str(x).strip() for x in row if str(x).strip()]
                proc_series.append(", ".join(dict.fromkeys(cnjs)))
            else:
                proc_series.append("")
        df["processos"] = proc_series
        return df

    # fallback: se houver texto bruto ou html_original, tenta extrair todos CNJs (não filtra indícios aqui)
    if "texto_bruto" in df.columns:
        df["processos"] = df["texto_bruto"].fillna("").apply(
            lambda t: ", ".join(sorted(set(CNJ_REGEX.findall(t))))
        )
    elif "html_original" in df.columns:
        df["processos"] = df["html_original"].fillna("").apply(
            lambda h: ", ".join(sorted(set(CNJ_REGEX.findall(h))))
        )
    else:
        df["processos"] = ""
    return df


# -----------------------------------------------------------------------------
# Carregamento do CSV / JSONL
# -----------------------------------------------------------------------------
@st.cache_data
def load_df_from_source(source):
    if hasattr(source, "read"):  # uploaded file
        df_ = pd.read_csv(source, sep=";")
    else:  # path string
        df_ = pd.read_csv(source, sep=";")

    # tipagens/conversões
    if "score" in df_.columns:
        df_["score"] = pd.to_numeric(df_["score"], errors="coerce").fillna(0).astype(int)

    if "is_arquivamento" in df_.columns:
        df_["is_arquivamento"] = (
            df_["is_arquivamento"].astype(str).str.strip().replace({"True": "1", "False": "0"})
        )
        df_["is_arquivamento_flag"] = (df_["is_arquivamento"] == "1").astype(int)

    def _parse_dt(dt_str):
        try:
            return pd.to_datetime(dt_str, format="%Y-%m-%d_%H%M%S")
        except Exception:
            try:
                return pd.to_datetime(dt_str)
            except Exception:
                return pd.NaT

    if "received" in df_.columns:
        df_["received_dt"] = df_["received"].apply(_parse_dt)

    # garantir coluna 'processos'
    df_ = ensure_processos_column(df_)

    # hits_norm para destaque (lista de termos)
    if "hits" in df_.columns:
        df_["hits_norm"] = df_["hits"].fillna("").apply(parse_hits_terms)
    else:
        df_["hits_norm"] = [[] for _ in range(len(df_))]

    # preparar para hash do cache
    df_ = _make_hashable_df(df_)
    return df_


@st.cache_data
def enrich_with_jsonl(df_in: pd.DataFrame, jsonl_file: str) -> pd.DataFrame:
    jp = Path(jsonl_file)
    if not jp.exists():
        return _make_hashable_df(df_in)

    extra_rows = []
    with jp.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
                extra_rows.append({
                    "entry_id": o.get("entry_id"),
                    "message_id": o.get("message_id"),
                    "html_original": o.get("html_original"),
                    "html_file": o.get("html_file") or o.get("html_path"),
                })
            except Exception:
                pass

    if not extra_rows:
        return _make_hashable_df(df_in)

    df_extra = pd.DataFrame(extra_rows).drop_duplicates(subset=["entry_id"])
    if "entry_id" in df_in.columns:
        merged = df_in.merge(df_extra[["entry_id", "html_file", "html_original"]],
                             on="entry_id", how="left")
    else:
        merged = df_in

    return _make_hashable_df(merged)


# -----------------------------------------------------------------------------
# Filtro e ordenação
# -----------------------------------------------------------------------------
def apply_filters(df: pd.DataFrame, score_range=None, only_flagged=False, q="", term="") -> pd.DataFrame:
    mask = pd.Series([True] * len(df), index=df.index)
    if score_range and "score" in df.columns:
        mask &= df["score"].between(score_range[0], score_range[1])
    if only_flagged and "is_arquivamento_flag" in df.columns:
        mask &= (df["is_arquivamento_flag"] == 1)
    if q:
        ql = q.lower()
        subject_s = df.get("subject", pd.Series("", index=df.index)).fillna("").str.lower()
        # removemos 'sender' da busca por não ter utilidade nesta pasta
        mask &= subject_s.str.contains(ql)
    if term:
        tl = term.lower()
        hits_s = df.get("hits", pd.Series("", index=df.index)).fillna("").str.lower()
        mask &= hits_s.str.contains(tl)
    return df.loc[mask].copy()


def sort_df(df: pd.DataFrame, sort_col: str | None, sort_order: str | None) -> pd.DataFrame:
    if not sort_col:
        if "score" in df.columns and "received_dt" in df.columns:
            return df.sort_values(["score", "received_dt"], ascending=[False, False])
        if "score" in df.columns:
            return df.sort_values(["score"], ascending=[False])
        if "received_dt" in df.columns:
            return df.sort_values(["received_dt"], ascending=[False])
        return df
    asc = True if (sort_order or "").lower() == "asc" else False
    if sort_col in df.columns:
        return df.sort_values([sort_col], ascending=[asc])
    return df


def _header_link(col: str, current_sort: str | None, current_order: str | None) -> str:
    # alterna asc/desc se for a mesma coluna
    next_order = "asc"
    if current_sort == col and (current_order or "").lower() == "asc":
        next_order = "desc"
    params = {"sort": col, "order": next_order}
    viewrow = _get_query_param("viewrow", None)
    if viewrow:
        params["viewrow"] = viewrow
    href = "?" + urllib.parse.urlencode(params)
    return f'<a href="{href}" target="_self">{html.escape(col)}</a>'


# -----------------------------------------------------------------------------
# Localização do HTML e destaque (keywords + CNJ)
# -----------------------------------------------------------------------------
def safe_filename(s: str, maxlen: int = 140) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "_", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return (s[:maxlen].rstrip() if len(s) > maxlen else s) or "sem_assunto"


def guess_html_path_from_dir(row: pd.Series, html_dir_path: str) -> str | None:
    if not html_dir_path:
        return None
    d = Path(html_dir_path)
    if not d.exists():
        return None

    rec = str(row.get("received", "") or "")
    subject = str(row.get("subject", "") or "").lower()

    # PRIMEIRO: Buscar exatamente pelo nome esperado
    expected_name = f"{rec}__{safe_filename(subject)}.html"
    exact_path = d / expected_name
    if exact_path.exists():
        return str(exact_path)

    # SEGUNDO: Buscar por arquivos que comecem com a data
    if rec:
        matching_files = []
        for p in d.glob(f"{rec}*.html"):
            matching_files.append(p)

        if matching_files:
            # Ordenar por similaridade com o assunto
            def similarity_score(filename):
                filename_lower = filename.lower()
                subject_terms = subject.split()
                score = sum(1 for term in subject_terms if term in filename_lower and len(term) > 3)
                return score

            matching_files.sort(key=lambda x: similarity_score(x.name), reverse=True)
            return str(matching_files[0])

    return None


def get_html_for_row(row: pd.Series) -> str | None:
    # Primeiro tenta pelo nome do arquivo (caminho relativo)
    html_filename = row.get("html_filename") or row.get("html_file_basename")
    if html_filename and isinstance(html_filename, str):
        html_path = Path(html_dir) / html_filename
        if html_path.exists():
            try:
                return html_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    # Depois tenta o caminho completo (fallback)
    html_path = (row.get("html_file") if "html_file" in row else None) or (
        row.get("html_path") if "html_path" in row else None)
    if html_path and isinstance(html_path, str) and Path(html_path).exists():
        try:
            return Path(html_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    # Terceiro: busca por padrão no diretório
    guessed = guess_html_path_from_dir(row, html_dir)
    if guessed and Path(guessed).exists():
        try:
            return Path(guessed).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    html_original = row.get("html_original") if "html_original" in row else None
    if isinstance(html_original, str) and html_original.strip():
        return html_original
    return None


def _compile_terms_regex(terms: list[str]) -> re.Pattern | None:
    # junta termos do hits em um regex case-insensitive, escapando individualmente
    terms = [t for t in (terms or []) if t and t.strip()]
    if not terms:
        return None
    escaped = [re.escape(t.strip()) for t in terms]
    pattern = r"(" + "|".join(escaped) + r")"
    try:
        return re.compile(pattern, re.IGNORECASE)
    except Exception:
        return None


def _compile_cnjs_regex(cnjs: list[str]) -> re.Pattern | None:
    cnjs = [c for c in (cnjs or []) if c and c.strip()]
    if not cnjs:
        return None
    escaped = [re.escape(c.strip()) for c in cnjs]
    pattern = r"(" + "|".join(escaped) + r")"
    try:
        return re.compile(pattern)
    except Exception:
        return None


def highlight_keywords_in_html(html_content: str, hits_seq, processos_seq):
    # hits (palavras-chave) — lista de strings
    hits_seq = list(hits_seq) if isinstance(hits_seq, (list, tuple)) else []

    # regex de hits (se houver)
    re_hits = _compile_terms_regex(hits_seq) if hits_seq else None

    # regex de CNJ (sempre)
    re_cnjs = _cnj_regex()

    # regex para FGV (case insensitive)
    re_fgv = re.compile(r'\b(funda[cç][aã]o getulio vargas|fgv|getulio vargas)\b', re.IGNORECASE)

    # regex para prazos
    re_prazo = re.compile(r'\b(prazo|termo|diligenci[ao]|intima[cç][aã]o|ci[êe]ncia)\b', re.IGNORECASE)

    base_css = """
    <style>
      /* Realces mais fortes */
      mark.sjur-hit { 
        background: #ffeb3b !important; 
        padding: 0 .2em !important;
        border-radius: 3px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        color: #000 !important;
        font-weight: bold !important;
        border: 1px solid #ffc107 !important;
      }

      mark.sjur-cnj { 
        background: #2196f3 !important; 
        padding: 0 .2em !important;
        border-radius: 3px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        color: white !important;
        font-weight: bold !important;
        border: 1px solid #1976d2 !important;
      }

      /* Realce especial para FUNDACAO GETULIO VARGAS */
      mark.sjur-fgv {
        background: #ff4444 !important;
        color: white !important;
        padding: 0 .2em !important;
        border-radius: 3px !important;
        font-weight: bold !important;
        border: 1px solid #cc0000 !important;
      }

      /* Realce especial para PRAZO */
      mark.sjur-prazo {
        background: #1565c0 !important;
        color: white !important;
        padding: 0 .2em !important;
        border-radius: 3px !important;
        font-weight: bold !important;
        border: 1px solid #0d47a1 !important;
      }

      /* Melhorar legibilidade geral */
      * {
        background: white !important;
        color: #333 !important;
      }

      /* Forçar fundo branco em todos os elementos */
      div, p, span, td, tr, table, li, ul, ol {
        background: white !important;
        color: #333 !important;
      }
    </style>
    """

    # Fallback sem BeautifulSoup
    if not HAS_BS4:
        out = html_content
        # Aplicar realces na ordem de prioridade
        out = re_fgv.sub(r'<mark class="sjur-fgv">\1</mark>', out)
        out = re_prazo.sub(r'<mark class="sjur-prazo">\1</mark>', out)
        out = re_cnjs.sub(lambda m: f'<mark class="sjur-cnj">{m.group(0)}</mark>', out)
        if re_hits:
            out = re_hits.sub(r'<mark class="sjur-hit">\1</mark>', out)
        return base_css + out

    # Com BeautifulSoup: limpe fundos e substitua em text nodes
    soup = BeautifulSoup(html_content, "html.parser")
    _force_white_background_dom(soup)

    from bs4 import NavigableString

    def _replace_in_text_node(node: NavigableString):
        s = str(node)
        changed = False

        # Aplicar realces na ordem de prioridade
        if re_fgv.search(s):
            s = re_fgv.sub(r'<mark class="sjur-fgv">\1</mark>', s)
            changed = True
        if re_prazo.search(s):
            s = re_prazo.sub(r'<mark class="sjur-prazo">\1</mark>', s)
            changed = True
        if re_cnjs.search(s):
            s = re_cnjs.sub(lambda m: f'<mark class="sjur-cnj">{m.group(0)}</mark>', s)
            changed = True
        if re_hits and re_hits.search(s):
            s = re_hits.sub(r'<mark class="sjur-hit">\1</mark>', s)
            changed = True

        if changed:
            node.replace_with(BeautifulSoup(s, "html.parser"))

    for t in soup.find_all(string=True):
        if t.parent.name in ("script", "style", "noscript", "head", "title"):
            continue
        if isinstance(t, NavigableString):
            _replace_in_text_node(t)

    # injeta CSS + retorna
    return base_css + str(soup)


# -----------------------------------------------------------------------------
# Sistema de Resolução de Conteúdo Robustecido
# -----------------------------------------------------------------------------
def find_html_content_robust(row: pd.Series) -> tuple[str | None, str]:
    """
    Tenta múltiplas estratégias para encontrar o conteúdo HTML.
    Retorna (conteúdo_html, método_utilizado)
    """
    methods_tried = []

    # 1. Tentativa: html_file path direto
    html_path = row.get("html_file") or row.get("html_path")
    if html_path and isinstance(html_path, str) and Path(html_path).exists():
        try:
            content = Path(html_path).read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                methods_tried.append(f"html_file: {html_path}")
                return content, " → ".join(methods_tried)
        except Exception as e:
            methods_tried.append(f"html_file error: {str(e)}")

    # 2. Tentativa: html_original direto da linha
    html_original = row.get("html_original")
    if isinstance(html_original, str) and html_original.strip():
        methods_tried.append("html_original direct")
        return html_original, " → ".join(methods_tried)

    # 3. Tentativa: Busca por padrão de arquivo baseado em received + subject
    received = row.get("received", "")
    subject = row.get("subject", "")
    if received and subject:
        try:
            # Padrão: YYYY-MM-DD_HHMMSS__subject_safe.html
            expected_filename = f"{received}__{safe_filename(subject)}.html"
            expected_path = Path(html_dir) / expected_filename

            if expected_path.exists():
                try:
                    content = expected_path.read_text(encoding="utf-8", errors="ignore")
                    if content.strip():
                        methods_tried.append(f"exact_match: {expected_filename}")
                        return content, " → ".join(methods_tried)
                except Exception as e:
                    methods_tried.append(f"exact_match error: {str(e)}")
        except Exception as e:
            methods_tried.append(f"pattern_match error: {str(e)}")

    # 4. REMOVIDO: Busca por termos do assunto nos arquivos HTML (CAUSA PROBLEMAS)
    # 5. REMOVIDO: Último recurso - qualquer arquivo HTML (CAUSA PROBLEMAS)

    return None, " → ".join(methods_tried) if methods_tried else "Nenhum método encontrou o arquivo exato"


def highlight_keywords_in_html_with_fallback(html_content: str, hits_seq, processos_seq, row: pd.Series) -> str:
    """
    Versão robusta do highlight com fallback para conteúdo alternativo
    """
    if not html_content:
        # Fallback: criar conteúdo básico a partir dos dados da linha
        basic_content = f"""
        <html>
        <head><title>Conteúdo não encontrado - Fallback</title></head>
        <body style="background: white; padding: 20px; font-family: Arial, sans-serif;">
            <h2>Conteúdo HTML não encontrado para este item</h2>
            <p><strong>Entry ID:</strong> {row.get('entry_id', 'N/A')}</p>
            <p><strong>Assunto:</strong> {html.escape(str(row.get('subject', 'N/A')))}</p>
            <p><strong>Received:</strong> {row.get('received', 'N/A')}</p>
            <p><strong>Score:</strong> {row.get('score', 'N/A')}</p>
            <p><strong>Processos detectados:</strong> {', '.join(processos_seq) if processos_seq else 'Nenhum'}</p>
            <p><strong>Termos encontrados:</strong> {', '.join(hits_seq) if hits_seq else 'Nenhum'}</p>
            <hr>
            <p><em>O sistema não conseguiu localizar o conteúdo HTML original.</em></p>
            <p><em>Verifique se o arquivo existe em: {html_dir}</em></p>
        </body>
        </html>
        """
        return basic_content

    # Aplicar o highlight normal
    return highlight_keywords_in_html(html_content, hits_seq, processos_seq)


# -----------------------------------------------------------------------------
# Modal (overlay) com fundo branco
# -----------------------------------------------------------------------------
def render_modal_overlay(html_content: str, title: str = "Visualização do HTML"):
    # data URI para evitar I/O adicional
    data_uri = "data:text/html;charset=utf-8," + urllib.parse.quote(html_content, safe="/:;,+-_=()!?@#[]{}*'\" \n\r")
    modal = f"""
    <style>
      .sjur-modal-backdrop {{
        position: fixed; inset: 0; background: rgba(0,0,0,.45);
        z-index: 9999; display: flex; align-items: center; justify-content: center;
      }}
      .sjur-modal {{
        background: #fff; width: 92vw; height: 90vh; border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,.25); overflow: hidden; display: flex; flex-direction: column;
      }}
      .sjur-modal-header {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 10px 12px; border-bottom: 1px solid #e5e5e5; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        background: #fff;
      }}
      .sjur-modal-title {{ font-weight: 600; font-size: 14px; color: #111; }}
      .sjur-modal-close {{
        border: 0; background: #111; color: #fff; padding: 6px 10px; border-radius: 6px; cursor: pointer;
      }}
      .sjur-modal-iframe {{ width: 100%; height: 100%; border: 0; background: #fff; }}
    </style>
    <div class="sjur-modal-backdrop" id="sjurModal">
      <div class="sjur-modal">
        <div class="sjur-modal-header">
          <div class="sjur-modal-title">{html.escape(title)}</div>
          <div><button class="sjur-modal-close" onclick="document.getElementById('sjurModal').remove()">Fechar</button></div>
        </div>
        <iframe class="sjur-modal-iframe" src="{data_uri}"></iframe>
      </div>
    </div>
    """
    components.html(modal, height=10, scrolling=False)


# -----------------------------------------------------------------------------
# Funções corrigidas para resolução de linhas e links
# -----------------------------------------------------------------------------
def resolve_row_by_key(fdf_: pd.DataFrame, key: str) -> pd.Series | None:
    if not key:
        return None

    # Primeiro tenta por entry_id (se existir a coluna)
    if "entry_id" in fdf_.columns:
        _match = fdf_[fdf_["entry_id"].astype(str) == str(key)]
        if not _match.empty:
            return _match.iloc[0]

    # Depois tenta por índice (se for numérico)
    try:
        idx = int(key)
        if idx in fdf_.index:
            return fdf_.loc[idx]
    except (ValueError, TypeError):
        pass

    # Finalmente tenta match parcial no entry_id
    if "entry_id" in fdf_.columns:
        _match = fdf_[fdf_["entry_id"].astype(str).str.contains(str(key), na=False)]
        if not _match.empty:
            return _match.iloc[0]

    return None


def build_self_link(row) -> str:
    # Preferência: usar entry_id se disponível
    if "entry_id" in row.index and pd.notna(row["entry_id"]):
        val = str(row["entry_id"])
    else:
        val = str(row.name)  # índice da linha

    params = {"viewrow": val}
    sort_col = _get_query_param("sort", None)
    sort_order = _get_query_param("order", None)
    if sort_col:
        params["sort"] = sort_col
    if sort_order:
        params["order"] = sort_order
    href = "?" + urllib.parse.urlencode(params)
    return f'<a href="{href}" target="_self">abrir</a>'


# -----------------------------------------------------------------------------
# Carregar DF
# -----------------------------------------------------------------------------
if uploaded is not None:
    df = load_df_from_source(uploaded)
elif default_csv and Path(default_csv).exists():
    df = load_df_from_source(default_csv)
else:
    st.warning("Carregue um CSV válido para começar.")
    st.stop()

if jsonl_path:
    df = enrich_with_jsonl(df, jsonl_path)

# -----------------------------------------------------------------------------
# Abas
# -----------------------------------------------------------------------------
tab_res, tab_view, tab_doc = st.tabs(["📊 Resultados", "📰 Visualização", "📘 Documentação"])

# -----------------------------------------------------------------------------
# 📊 Resultados
# -----------------------------------------------------------------------------
with tab_res:
    # Filtros
    st.subheader("Filtros")
    if "score" in df.columns and len(df):
        min_sc, max_sc = int(df["score"].min()), int(df["score"].max())
    else:
        min_sc, max_sc = 0, 0

    colA, colB, colC, colD = st.columns([1, 1, 2, 2])
    with colA:
        score_range = st.slider("Score (mín ↔ máx)", min_sc, max_sc, (min_sc, max_sc))
    with colB:
        only_flagged = st.checkbox("Somente is_arquivamento=1", value=False)
    with colC:
        q = st.text_input("Busca em assunto", value="").strip()
    with colD:
        term = st.text_input("Precisa conter em 'hits'", value="").strip()

    # aplicar filtros
    fdf = apply_filters(df, score_range, only_flagged, q, term)

    # Ordenação por clique no cabeçalho
    sort_col = _get_query_param("sort", None)
    sort_order = _get_query_param("order", None)
    fdf_sorted = sort_df(fdf, sort_col, sort_order)

    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Total (CSV)", len(df))
    c2.metric("Filtrados", len(fdf_sorted))
    c3.metric("Marcados (CSV)", int(df.get("is_arquivamento_flag", pd.Series([0] * len(df))).sum()))

    # Histograma do Score
    if "score" in df.columns and len(df):
        with st.expander("Distribuição do Score"):
            fig, ax = plt.subplots()
            df["score"].value_counts().sort_index().plot(kind="bar", ax=ax)
            ax.set_xlabel("Score")
            ax.set_ylabel("Quantidade")
            ax.set_title("Distribuição de Score")
            st.pyplot(fig)

    # Tabela principal - MOSTRAR AMBAS AS COLUNAS se existirem
    st.subheader("Resultados filtrados")

    # Definir colunas para mostrar
    cols_show = []

    # Colunas básicas sempre mostradas
    base_cols = ["received", "score", "is_arquivamento", "hits", "subject"]
    for col in base_cols:
        if col in fdf_sorted.columns:
            cols_show.append(col)

    # Adicionar ambas as colunas de processos se existirem
    if "indicios" in fdf_sorted.columns:
        cols_show.append("indicios")

    if "processos" in fdf_sorted.columns:
        cols_show.append("processos")

    # Mensagens informativas
    if "indicios" in fdf_sorted.columns and "processos" in fdf_sorted.columns:
        st.info("📋 **indicios**: apenas processos com indícios positivos | **processos**: todos os CNJs encontrados")
    elif "indicios" in fdf_sorted.columns:
        st.info("📋 Coluna 'indicios' mostra apenas processos com indícios positivos de arquivamento")
    elif "processos" in fdf_sorted.columns:
        st.info("📋 Coluna 'processos' mostra todos os CNJs encontrados no documento")

    link_col = "🔗 Ver HTML"
    view_df = fdf_sorted[cols_show].copy()

    # CORREÇÃO: Usar apply para construir links consistentemente
    view_df[link_col] = fdf_sorted.apply(build_self_link, axis=1)

    # Cabeçalhos com links de ordenação
    rendered = view_df.copy()
    new_cols = []
    for c in rendered.columns:
        if c == link_col:
            new_cols.append(c)
        else:
            new_cols.append(_header_link(c, sort_col, sort_order))
    rendered.columns = new_cols

    st.markdown(rendered.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Downloads
    st.caption("Exportações")
    colx, coly = st.columns(2)
    with colx:
        csv_bytes = fdf_sorted.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button("⬇️ Baixar CSV filtrado", data=csv_bytes, file_name="arquivamento_filtrado.csv",
                           mime="text/csv")

    with coly:
        # Excel (xlsx): tenta xlsxwriter, depois openpyxl
        try:
            import xlsxwriter  # noqa: F401

            engine = "xlsxwriter"
        except Exception:
            try:
                import openpyxl  # noqa: F401

                engine = "openpyxl"
            except Exception:
                engine = None

        if engine is None:
            st.warning(
                "Para exportar em Excel, instale **xlsxwriter** ou **openpyxl**.\n\nEx.: `pip install xlsxwriter`")
        else:
            # transformar colunas potencialmente lista/tupla em string
            xdf = fdf_sorted.copy()
            for c in ("processos_list", "processos_list_ctx", "hits_norm"):
                if c in xdf.columns:
                    xdf[c] = xdf[c].apply(lambda x: ", ".join(map(str, x)) if isinstance(x, (list, tuple)) else x)

            from io import BytesIO

            bio = BytesIO()
            with pd.ExcelWriter(bio, engine=engine) as writer:
                xdf.to_excel(writer, index=False, sheet_name="Resultados")
            st.download_button("⬇️ Baixar Excel (xlsx)", data=bio.getvalue(), file_name="arquivamento_filtrado.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -----------------------------------------------------------------------------
# 📰 Visualização
# -----------------------------------------------------------------------------
with tab_view:
    st.subheader("Visualização do recorte (com destaques)")
    st.caption("Destaques: **CNJs** (azul) e **palavras-chave (hits)** (amarelo). Fundo do HTML: **branco**.")

    # Resolver a linha baseada no viewrow parameter
    viewrow = _get_query_param("viewrow", None)
    row = None
    resolution_method = ""

    if viewrow:
        key = urllib.parse.unquote(viewrow)
        row = resolve_row_by_key(df, key)
        resolution_method = f"Por viewrow: {key}"

    if row is None and len(df):
        # Fallback para a primeira linha
        row = df.iloc[0]
        resolution_method = "Fallback: primeira linha"

    if row is not None:
        # Mostrar informações de debug
        with st.expander("🔍 Informações de Debug"):
            st.write(f"**Método de resolução:** {resolution_method}")
            st.write(f"**Entry ID:** {row.get('entry_id', 'N/A')}")
            st.write(f"**HTML File:** {row.get('html_file', 'N/A')}")
            st.write(f"**Subject:** {row.get('subject', 'N/A')}")

        # Buscar conteúdo HTML com sistema robusto
        html_content, content_method = find_html_content_robust(row)

        with st.expander("🔍 Métodos de busca de HTML"):
            st.write(f"**Estratégias tentadas:** {content_method}")

        # título exato com dados da linha
        titulo = f"{row.get('received', '')} — {row.get('subject', '')}"
        st.markdown(f"### {titulo}")

        if html_content:
            highlighted = highlight_keywords_in_html_with_fallback(
                html_content,
                row.get("hits_norm", []),
                row.get("processos_list_ctx", row.get("processos_list", [])),
                row
            )

            # render direto (área blanco — já forçado no CSS injetado)
            components.html(highlighted, height=700, scrolling=True)

            # botão opcional de popup (overlay blanco)
            if st.button("🔎 Abrir em popup (overlay)"):
                render_modal_overlay(highlighted, title=titulo)
        else:
            st.warning("""
            **Não foi possível encontrar o conteúdo HTML para este item.**

            Possíveis causas:
            - O arquivo HTML não existe na pasta especificada
            - O entry_id no CSV não corresponde aos arquivos
            - O arquivo pode estar corrompido ou em formato diferente
            """)

            # Mostrar fallback básico
            fallback_content = f"""
            <html>
            <body style="background: white; padding: 20px;">
                <h3>Conteúdo não disponível</h3>
                <p><strong>Entry ID:</strong> {row.get('entry_id', 'N/A')}</p>
                <p><strong>Assunto:</strong> {html.escape(str(row.get('subject', 'N/A')))}</p>
                <p><strong>Arquivo esperado:</strong> {row.get('html_file', 'N/A')}</p>
                <p><strong>Pasta de busca:</strong> {html_dir}</p>
            </body>
            </html>
            """
            components.html(fallback_content, height=300, scrolling=False)
    else:
        st.info("Selecione um item para visualizar.")

    # Sistema de seleção manual melhorado
    st.markdown("---")
    st.subheader("Seleção Manual Avançada")

    # Criar opções de seleção com informações úteis
    options_data = []
    for idx, row in df.iterrows():
        entry_id = str(row.get("entry_id", idx))
        subject = str(row.get("subject", ""))[:60]
        score = row.get("score", 0)
        received = row.get("received", "")

        options_data.append({
            "value": entry_id,
            "label": f"{entry_id} | Score: {score} | {received} | {subject}",
            "score": score,
            "received": received
        })

    # Ordenar por score e data
    options_data.sort(key=lambda x: (x["score"], x["received"]), reverse=True)

    option_labels = [opt["label"] for opt in options_data]
    option_values = [opt["value"] for opt in options_data]

    selected_option = st.selectbox(
        "Selecione um item (ordenado por score):",
        options=[""] + option_labels,
        index=0,
        key="advanced_manual_select"
    )

    if selected_option:
        selected_index = option_labels.index(selected_option)
        selected_value = option_values[selected_index]
        _set_query_params(viewrow=selected_value)
        st.rerun()

# -----------------------------------------------------------------------------
# 📘 Documentação
# -----------------------------------------------------------------------------
with tab_doc:
    st.markdown("""
### O que esta aplicação faz?
- Lê um **CSV** (saída do pipeline) com resultados do scanner de indícios de arquivamento.
- Permite **filtrar** por *score*, flag de arquivamento (`is_arquivamento`), termos em **assunto** e em `hits`.
- **Ordena** clicando nos cabeçalhos das colunas (gera `?sort=<col>&order=asc|desc`).
- Mostra **processos (CNJs) com indícios de arquivamento** na coluna `processos`.
- Exibe o **HTML do recorte** com **destaque de CNJ** (azul) e **palavras-chave** (amarelo).
- Exporta os resultados filtrados para **CSV** e **Excel**.

### Explicação das colunas
- **score**: pontuação heurística baseada em palavras-chave / padrões que indicam **arquivamento**. Quanto maior, maior a força do indício.
- **is_arquivamento**: rótulo binário da linha (1 = possui indício forte de arquivamento; 0 = não).
- **hits**: termos que contribuíram para o score (ex.: `+3:arquivament, +3:arquivado, +2:baixa, ...`).
- **processos**: **apenas** os CNJs para os quais foram encontrados **indícios de arquivamento**.
- **received**: data/hora de recebimento da mensagem.
- **subject**: assunto da mensagem.

### Como usar
1. **Carregue o CSV**: use o campo na sidebar ou faça upload
2. **Filtre os resultados**: use os controles na aba "Resultados"
3. **Visualize detalhes**: clique em "abrir" na coluna "🔗 Ver HTML"
4. **Exporte**: use os botões de download na parte inferior

### Dicas
- Use `Ctrl+F` no navegador para buscar dentro do HTML visualizado
- Clique nos cabeçalhos da tabela para ordenar (asc/desc)
- A coluna `indicios` mostra apenas processos com indícios positivos
- O sistema tenta automaticamente localizar o HTML correspondente

### Troubleshooting
**Problema**: HTML não aparece ou está em branco
**Solução**: 
- Verifique se a pasta de HTML está correta na sidebar
- Confirme se os nomes dos arquivos seguem o padrão `YYYY-MM-DD_HHMMSS__assunto.html`

**Problema**: Destaques não aparecem no HTML
**Solução**:
- Instale BeautifulSoup: `pip install beautifulsoup4`
- O fallback regex funciona, mas o BeautifulSoup é mais preciso

### Desenvolvimento
Esta aplicação faz parte do projeto **Scanner de Indícios de Arquivamento (SJUR)**.

Código aberto disponível em: [link para o repositório]
""")

# -----------------------------------------------------------------------------
# Footer e informações de debug
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.caption(f"✨ SJUR Scanner v1.0 • {len(df)} registros carregados")

# Debug info (expandable)
with st.sidebar.expander("ℹ️ Debug Info"):
    st.write(f"Colunas disponíveis: {list(df.columns)}")
    st.write(f"Total de linhas: {len(df)}")
    st.write(f"BeautifulSoup disponível: {HAS_BS4}")
    if len(df) > 0:
        sample_row = df.iloc[0]
        st.write("Amostra da primeira linha:")
        for col in ["entry_id", "score", "is_arquivamento", "subject", "processos", "indicios"]:
            if col in sample_row:
                st.write(f"- {col}: {sample_row[col]}")

# -----------------------------------------------------------------------------
# Script de inicialização para garantir que o modal funcione
# -----------------------------------------------------------------------------
components.html("""
<script>
// Garantir que o modal possa ser fechado mesmo após rerender do Streamlit
document.addEventListener('click', function(e) {
    if (e.target && e.target.classList.contains('sjur-modal-close')) {
        const modal = document.getElementById('sjurModal');
        if (modal) {
            modal.remove();
        }
    }
});
</script>
""", height=0)

# -----------------------------------------------------------------------------
# Finalização
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Para execução direta via python app_arquivamento_streamlit.py
    pass