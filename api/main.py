from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# como o main está dentro de api/, use o pacote local "routes"
from routes import root
from routes import recortes as recortes_routes
from routes import rede_test
from routes import healthcheck
from routes import sqlserver_test
from routes import arquivamento  # <— novo

app = FastAPI(title="SOLCORP - SJUR-RECORTES", version="1.0")

# CORS (ajuste origins conforme necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # ou ["http://localhost:8501", "http://127.0.0.1:8501"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas existentes
app.include_router(root.router)  # raiz "/"
app.include_router(recortes_routes.router)  # mantém comportamento atual
app.include_router(rede_test.router, prefix="/api/rede", tags=["Rede"])
app.include_router(healthcheck.router, prefix="/api/healthcheck", tags=["Healthcheck"])
app.include_router(sqlserver_test.router, prefix="/api/sqlserver", tags=["SQL Server"])

# Novo: arquivamento
# OBS: em api/routes/arquivamento.py o router já tem prefix="/arquivamento"
# então aqui aplicamos apenas "/api" para resultar em "/api/arquivamento/scan"
app.include_router(arquivamento.router, prefix="/api", tags=["Arquivamento"])
