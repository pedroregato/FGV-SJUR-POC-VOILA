from .db_connection import get_connection

def criar_tabelas():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id_email TEXT PRIMARY KEY,
        message_id TEXT UNIQUE,
        data_recebimento TEXT,
        assunto TEXT,
        remetente TEXT,
        escritorio TEXT,
        codigo TEXT,
        area TEXT,
        jornal TEXT,
        data_disponibilizacao TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS recortes (
        id_recorte INTEGER PRIMARY KEY AUTOINCREMENT,
        id_email TEXT,
        nome_pesquisado TEXT,
        tribunal TEXT,
        secretaria TEXT,
        data_publicacao TEXT,
        publicacao TEXT,
        identificador_documento TEXT,
        FOREIGN KEY(id_email) REFERENCES emails(id_email)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS metadados_citacoes_fgv (
        id_metadado INTEGER PRIMARY KEY AUTOINCREMENT,
        id_recorte INTEGER,
        numero_processo TEXT,
        tribunal TEXT,
        uf TEXT,
        orgao TEXT,
        comarca TEXT,
        classe TEXT,
        unidade_fgv TEXT,
        obrigacoes TEXT,
        conteudo_publicado TEXT,
        igpm_count INTEGER,
        classificacao TEXT DEFAULT 'citação',
        url_email TEXT,
        data_publicacao TEXT,
        FOREIGN KEY(id_recorte) REFERENCES recortes(id_recorte)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS emails_processados (
        message_id TEXT PRIMARY KEY,
        data_processamento TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

