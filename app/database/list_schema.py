import sqlite3
from pathlib import Path

# Caminho para o banco de dados
db_path = Path.cwd().parents[1] / "data" / "sjur_recortes.db"

# Conecta ao banco
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Lista todas as tabelas (exceto internas do SQLite)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tabelas = [row[0] for row in cursor.fetchall()]

# Inspeção de cada tabela
for tabela in tabelas:
    print(f"\n📌 Tabela: {tabela}")

    # Lista colunas e tipos, com info de chave primária
    cursor.execute(f"PRAGMA table_info({tabela});")
    colunas = cursor.fetchall()
    for col in colunas:
        nome_coluna = col[1]
        tipo = col[2]
        is_pk = " [PK]" if col[5] == 1 else ""
        print(f" - {nome_coluna} ({tipo}){is_pk}")

    # Verifica se há chaves estrangeiras
    cursor.execute(f"PRAGMA foreign_key_list({tabela});")
    fks = cursor.fetchall()
    if fks:
        print(" 🔗 Chaves estrangeiras:")
        for fk in fks:
            print(f"   - {fk[3]} → {fk[2]}({fk[4]})")

    # Conta registros
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {tabela};")
        total = cursor.fetchone()[0]
        print(f"📊 Total de registros: {total}")
    except Exception as e:
        print(f"⚠️ Erro ao contar registros: {e}")

conn.close()
