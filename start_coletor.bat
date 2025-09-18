@echo off
chcp 65001 >nul
title Coletor SJUR - Servidor

echo.
echo =================================================
echo      Iniciando o Servidor do Coletor SJUR...
echo =================================================
echo.
echo Este processo precisa permanecer aberto para que a aplicacao funcione.
echo.
echo A aplicacao estara disponivel em: http://localhost:8501
echo.
echo Pressione Ctrl+C para encerrar o servidor.
echo.

rem Verifica se o executável existe
if not exist "coletor_sjur.exe" (
    echo ERRO: Arquivo coletor_sjur.exe nao encontrado!
    echo Certifique-se de que este arquivo .bat esta na mesma pasta do executavel.
    pause
    exit /b 1
)

rem Verifica se a porta 8501 já está em uso
netstat -an | find ":8501" | find "LISTENING" >nul
if %errorlevel% equ 0 (
    echo ERRO: A porta 8501 ja esta em uso!
    echo Feche outros programas que possam estar usando esta porta.
    echo.
    echo Processos usando a porta 8501:
    netstat -ano | find ":8501" | find "LISTENING"
    echo.
    pause
    exit /b 1
)

rem Cria um arquivo de log com timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set logfile=log_%datetime:~0,8%_%datetime:~8,6%.txt

echo [%date% %time%] Iniciando Coletor SJUR >> %logfile%
echo Servidor iniciado em: %date% %time% >> %logfile%

echo Iniciando servidor... Verifique %logfile% para detalhes.
echo.

rem Executa o programa e redireciona a saída para o arquivo de log
coletor_sjur.exe >> %logfile% 2>&1

rem Verifica o código de erro
if %errorlevel% neq 0 (
    echo.
    echo ERRO: O servidor falhou ao iniciar (codigo: %errorlevel%)
    echo Verifique o arquivo %logfile% para detalhes do erro.
    echo.
    echo Ultimas linhas do log:
    powershell -Command "Get-Content %logfile% | Select-Object -Last 10"
) else (
    echo.
    echo Servidor encerrado normalmente.
)

echo.
echo Log completo disponivel em: %logfile%
pause