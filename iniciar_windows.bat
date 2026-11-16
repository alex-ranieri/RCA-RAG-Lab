@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto check
where python >nul 2>&1
if errorlevel 1 (
    echo ERRO: instale Python 3.10 ou superior e habilite o PATH.
    pause
    exit /b 1
)
python -m venv .venv
if errorlevel 1 goto failure
:check
".venv\Scripts\python.exe" -c "import pypdf, fontTools" >nul 2>&1
if not errorlevel 1 goto start
echo Preparando dependencias locais. Internet necessaria apenas nesta etapa.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failure
:start
echo RCA-RAG Lab - colecao demo por padrao; veja o endereco exibido abaixo.
echo Deixe esta janela aberta. CTRL+C para encerrar.
".venv\Scripts\python.exe" -X utf8 app.py %*
if errorlevel 1 goto failure
exit /b 0
:failure
echo ERRO: consulte a mensagem acima. Nenhum PDF foi excluido.
pause
exit /b 1
