# api/routes/sqlserver_test.py
from fastapi import APIRouter
import pyodbc
import os
from dotenv import load_dotenv


# Carrega .env apenas uma vez no topo
load_dotenv()

router = APIRouter()

@router.get("/testar-conexao-sqlserver")
def testar_conexao_sqlserver():
    servidor = os.getenv("SQLSERVER_SERVER")
    banco = os.getenv("SQLSERVER_DB")
    usuario = os.getenv("SQLSERVER_USER")
    senha = os.getenv("SQLSERVER_PWD")

    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={servidor};"
            f"DATABASE={banco};"
            f"UID={usuario};"
            f"PWD={senha};"
            "TrustServerCertificate=yes;"
            "Connection Timeout=5;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT GETDATE()")
        result = cursor.fetchone()
        conn.close()

        return {
            "status": "sucesso",
            "mensagem": f"Conectado com sucesso ao SQL Server.",
            "data_atual_sql": str(result[0])
        }
    except Exception as e:
        return {
            "status": "erro",
            "mensagem": str(e)
        }
