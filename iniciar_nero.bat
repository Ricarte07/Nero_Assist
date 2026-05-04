@echo off
cd /d "%~dp0"

:: Lê o arquivo .env e extrai NGROK_TOKEN e NGROK_DOMAIN
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
    if "%%a"=="NGROK_TOKEN"  set NGROK_TOKEN=%%b
    if "%%a"=="NGROK_DOMAIN" set NGROK_DOMAIN=%%b
)

if "%NGROK_TOKEN%"=="" (
    echo.
    echo  ERRO: NGROK_TOKEN nao encontrado no arquivo .env
    echo  Adicione a linha: NGROK_TOKEN=seu_token_aqui
    pause
    exit /b
)

if "%NGROK_DOMAIN%"=="" (
    echo.
    echo  ERRO: NGROK_DOMAIN nao encontrado no arquivo .env
    echo  Adicione a linha: NGROK_DOMAIN=seu-dominio.ngrok-free.app
    pause
    exit /b
)

echo.
echo  Configurando ngrok...
ngrok.exe config add-authtoken %NGROK_TOKEN%

echo.
echo  Iniciando Nero API...
start "Nero API" cmd /k "python nero_api.py"

timeout /t 3 /nobreak >nul

echo  Iniciando tunel ngrok...
start "Nero Tunel" cmd /k "ngrok.exe http --url %NGROK_DOMAIN% 8000"

echo.
echo  Nero iniciado!
echo  Acesse de qualquer lugar: https://%NGROK_DOMAIN%
echo.
pause
