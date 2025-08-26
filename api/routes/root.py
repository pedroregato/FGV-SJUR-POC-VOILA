from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse, tags=["Root"])
async def read_root(request: Request):
    base_url = str(request.base_url).rstrip("/")
    swagger_url = f"{base_url}/docs"

    html_content = f"""
    <html>
        <head>
            <title>SJUR - API Ativa</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f8f9fa;
                    text-align: center;
                    padding-top: 50px;
                }}
                h1 {{
                    color: #0d6efd;
                }}
                p {{
                    font-size: 18px;
                }}
                a {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 10px 20px;
                    font-size: 16px;
                    color: white;
                    background-color: #0d6efd;
                    text-decoration: none;
                    border-radius: 5px;
                }}
                a:hover {{
                    background-color: #0b5ed7;
                }}
            </style>
        </head>
        <body>
            <h1>🔵 API SJUR-RECORTES</h1>
            <p>Esta API está ativa e funcionando corretamente.</p>
            <a href="{swagger_url}" target="_blank">Acessar Documentação (Swagger)</a>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)
