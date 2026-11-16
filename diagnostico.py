#!/usr/bin/env python3
"""Diagnóstico local (sem baixar pacotes nem enviar arquivos)."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rag_core import pdf_files, doc_signature
from lmstudio_api import list_models, LMStudioError

root=Path(__file__).resolve().parent
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--workspace',type=Path,default=root/'demo')
args=parser.parse_args()
collection=args.workspace.resolve()
print('Coleção:',collection)
print('RCA-RAG Lab 0.1 | diagnóstico')
print('Python:',sys.version.split()[0], sys.executable)
import platform
from recursos import memory_snapshot
print('Windows/arquitetura:',platform.platform(),platform.machine())
print('Memória:',memory_snapshot())
try:
    import subprocess
    result=subprocess.run(['powershell','-NoProfile','-Command',
        'Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name; Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess'],
        capture_output=True,text=True,timeout=20)
    print(result.stdout or result.stderr)
except (OSError,subprocess.TimeoutExpired) as exc:print('Hardware/portas não disponíveis:',exc)
try:
    import pypdf
    print('pypdf:',pypdf.__version__)
except Exception as exc:
    print('pypdf: ERRO',exc)
paths=pdf_files(collection/'documentos') if (collection/'documentos').is_dir() else []
print('PDFs encontrados:',len(paths))
for path in paths:print(' -',path.name,round(path.stat().st_size/1024**2,2),'MB')
if paths:print('Fingerprint de documentos:',doc_signature(collection/'documentos')[:12])
for url in ['http://127.0.0.1:1234/v1','http://127.0.0.1:1235/v1']:
    try:print('API',url,':',list_models(url))
    except LMStudioError as exc:print('API',url,': indisponível:',exc)
print('Abra a interface com: iniciar_windows.bat (ou .venv/Scripts/python.exe -X utf8 app.py)')
