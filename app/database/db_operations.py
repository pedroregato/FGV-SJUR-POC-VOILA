import sqlite3
from typing import List, Optional
from app.database.db_connection import get_connection
from app.modules.extractors.partes_extractor import PartesProcesso
from app.modules.extractors.metadados_extractor import extrair_metadados_publicacao


def registrar_email(
    message_id: str,
    data_recebimento: str,
    assunto: str,
    remetente: str,
    escritorio: str,
    codigo: str,
    area: str,
    jornal: str,
    data_disponibilizacao: str,
    data_processamento: str
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO emails (
            message_id, data_recebimento, assunto, remetente, escritorio,
            codigo, area, jornal, data_disponibilizacao, data_processamento
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        message_id, data_recebimento, assunto, remetente, escritorio,
        codigo, area, jornal, data_disponibilizacao, data_processamento
    ))
    conn.commit()
    conn.close()

def registrar_recorte(
    message_id: str,
    nome_pesquisado: str,
    tribunal: str,
    secretaria: str,
    data_publicacao: str,
    publicacao: str,
    tipo: str
) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recortes (
                message_id, nome_pesquisado, tribunal, secretaria,
                data_publicacao, publicacao, tipo
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, nome_pesquisado, tribunal, secretaria,
            data_publicacao, publicacao, tipo
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def registrar_partes(id_recorte: int, partes: PartesProcesso):
    conn = get_connection()
    cursor = conn.cursor()

    def inserir(nomes: List[str], papel: str):
        for nome in nomes:
            cursor.execute("""
                INSERT INTO partes (id_recorte, parte, papel)
                VALUES (?, ?, ?);
            """, (id_recorte, nome, papel))

    inserir(partes.autor, "autor")
    inserir(partes.reu, "reu")
    inserir(partes.interessados, "interessado")
    inserir(partes.advogados_autor, "advogado_autor")
    inserir(partes.advogados_reu, "advogado_reu")

    conn.commit()
    conn.close()


def registrar_metadados(id_recorte: int, texto_publicacao: str):
    dados = extrair_metadados_publicacao(texto_publicacao)
    if not dados:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO metadados (
            id_recorte, numero_processo, tribunal, uf, orgao, comarca, classe,
            unidade_fgv, obrigacoes, conteudo_publicado, igpm_count, classificacao,
            url_email, data_publicacao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        id_recorte,
        dados.get("numero_processo"),
        dados.get("tribunal"),
        dados.get("uf"),
        dados.get("orgao"),
        dados.get("comarca"),
        dados.get("classe"),
        dados.get("unidade_fgv"),
        "; ".join(dados.get("obrigacoes", [])),
        dados.get("conteudo_publicado"),
        dados.get("igpm_count"),
        dados.get("classificacao"),
        dados.get("url_email"),
        dados.get("data_publicacao")
    ))

    conn.commit()
    conn.close()


def registrar_metadados_dict(id_recorte: int, dados: dict):
    from app.database.db_connection import get_connection
    import json

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO metadados (
                id_recorte, numero_processo, tribunal, uf, orgao, comarca, classe,
                unidade_fgv, obrigacoes, conteudo_publicado, igpm_count, classificacao,
                url_email, data_publicacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            id_recorte,
            dados.get("numero_processo"),
            dados.get("tribunal"),
            dados.get("uf"),
            dados.get("orgao"),
            dados.get("comarca"),
            dados.get("classe"),
            dados.get("unidade_fgv"),
            json.dumps(dados.get("obrigacoes", [])),
            dados.get("conteudo_publicado"),
            dados.get("igpm_count"),
            dados.get("classificacao"),
            dados.get("url_email"),
            dados.get("data_publicacao")
        ))
        conn.commit()
        print(f"✅ Metadados registrados para recorte {id_recorte}")
    except Exception as e:
        print(f"❌ Falha ao registrar metadados: {e}")
    finally:
        conn.close()

