# api/routes/sqlserver_test.py
from fastapi import APIRouter
import pyodbc

router = APIRouter()

@router.get("/testar-conexao-sqlserver")
def testar_conexao_sqlserver():
    servidor = "SQLDC1VDS0006"
    banco = "FGV_SOLCORP_SERDON"
    usuario = "FGV_SOLCORP_SERDON"
    senha = "w>#t<L$4W#B183D7HLp4Z6P9"

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
