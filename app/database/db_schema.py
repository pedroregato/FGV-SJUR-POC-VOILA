# db_schema.py

def criar_tabelas(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            data_recebimento TEXT,
            assunto TEXT,
            remetente TEXT,
            escritorio TEXT,
            codigo TEXT,
            area TEXT,
            jornal TEXT,
            data_disponibilizacao TEXT,
            data_processamento TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recortes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT,
            nome_pesquisado TEXT,
            tribunal TEXT,
            secretaria TEXT,
            data_publicacao TEXT,
            publicacao TEXT,
            tipo TEXT,
            FOREIGN KEY (message_id) REFERENCES emails(message_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_recorte INTEGER,
            parte TEXT,
            papel TEXT,
            FOREIGN KEY (id_recorte) REFERENCES recortes(id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            classificacao TEXT,
            url_email TEXT,
            data_publicacao TEXT,
            FOREIGN KEY (id_recorte) REFERENCES recortes(id)
        );
    """)

    conn.commit()
