from fastapi import FastAPI
from api.routes.recortes import router
from api.routes import rede_test
from api.routes import healthcheck
from api.routes import sqlserver_test


app = FastAPI(title="SOLCORP - SJUR-RECORTES", version="1.0")
app.include_router(router)
app.include_router(rede_test.router, prefix="/api/rede", tags=["Rede"])
app.include_router(healthcheck.router, prefix="/api/healthcheck", tags=["Healthcheck"])
app.include_router(sqlserver_test.router, prefix="/api/sqlserver", tags=["SQL Server"])