# api/routes/rede_test.py
from fastapi import APIRouter
import subprocess

router = APIRouter()

@router.get("/testar-rede-sqlserver")
def testar_rede_sqlserver():
    hostname = "SQLDC1VDS0006"
    porta = "1433"

    try:
        # Teste de ping
        ping_result = subprocess.run(["ping", "-c", "2", hostname], capture_output=True, text=True)
        ping_output = ping_result.stdout if ping_result.returncode == 0 else ping_result.stderr

        # Teste de telnet
        telnet_result = subprocess.run(["timeout", "5", "telnet", hostname, porta], capture_output=True, text=True)
        telnet_output = telnet_result.stdout + telnet_result.stderr

        return {
            "ping_sucesso": ping_result.returncode == 0,
            "ping_saida": ping_output,
            "telnet_saida": telnet_output
        }
    except Exception as e:
        return {
            "erro": str(e)
        }
