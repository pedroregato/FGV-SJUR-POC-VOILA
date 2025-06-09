@echo off
REM Inicia o container sjur-api com mapeamento de host adicional

echo 🔄 Removendo container anterior (se existir)...
docker rm -f sjur-api >nul 2>&1

echo 🚀 Iniciando novo container sjur-api com mapeamento de host SQLDC1VDS0006...
docker run -d ^
  --name sjur-api ^
  --env-file api/.env ^
  -e MODE=prod ^
  -p 8000:8000 ^
  --add-host SQLDC1VDS0006:10.60.66.32 ^
  sjur-api

echo ✅ Container iniciado com sucesso em http://localhost:8000
pause
