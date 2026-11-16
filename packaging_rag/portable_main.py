"""Entrada portátil do laboratório RAG; não depende de Python no destino."""
from __future__ import annotations
import argparse
import io
import json
import logging
import os
from pathlib import Path
import platform
import sys
import tempfile

VERSION='0.2-portatil-2026.11.11'
HOME=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]
if not getattr(sys,'frozen',False):sys.path.insert(0,str(HOME))

def verify():
    import app
    import pypdf
    import fontTools
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    from rag_core import build_index,BM25,pick_context
    writer=pypdf.PdfWriter();page=writer.add_blank_page(width=595,height=842)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    content=DecodedStreamObject();content.set_data(b'BT /F1 12 Tf 50 700 Td (A biblioteca abre as nove horas e fecha as dezoito horas. O prazo do emprestimo dos livros e de sete dias.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(content)
    with tempfile.TemporaryDirectory(prefix='rca_rag_verificacao_') as folder:
        path=Path(folder)/'verificacao_temporaria.pdf'
        with path.open('wb') as stream:writer.write(stream)
        index=build_index(Path(folder))
        evidence=pick_context(index,BM25(index['chunks']).search('biblioteca emprestimo'))
        if not evidence or 'sete dias' not in evidence[0]['text']:raise RuntimeError('Extração/busca não passou.')
    if not app.WEB.is_file() or not (app.ROOT/'web'/'app.js').is_file():
        raise RuntimeError('Arquivos da interface ausentes; copie a pasta inteira, incluindo _internal.')
    return {'status':'ok','version':VERSION,'frozen':bool(getattr(sys,'frozen',False)),
            'architecture':platform.machine(),'python_bundled':platform.python_version(),
            'pypdf':pypdf.__version__,'fonttools':fontTools.__version__,
            'checks':['runtime','pypdf','fonttools','extração PDF','BM25','páginas','interface HTML/JS']}

def diagnose(workspace):
    from lmstudio_api import list_models,LMStudioError
    from recursos import memory_snapshot
    result=verify();result['memory']=memory_snapshot();result['workspace']=str(workspace)
    result['models']={}
    for port in (1234,1235):
        url=f'http://127.0.0.1:{port}/v1'
        try:result['models'][url]={'status':'ok','ids':list_models(url)}
        except LMStudioError as exc:result['models'][url]={'status':'indisponível','detail':str(exc)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    (HOME/'logs'/'diagnostico.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    for stream in (sys.stdout,sys.stderr):
        if stream and hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='replace')
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--verificar',action='store_true')
    parser.add_argument('--diagnostico',action='store_true')
    parser.add_argument('--version',action='store_true')
    parser.add_argument('--workspace',type=Path,default=HOME/'colecoes'/'principal')
    opts,_=parser.parse_known_args()
    if opts.version:print(VERSION);return 0
    if opts.verificar:
        print(json.dumps(verify(),ensure_ascii=False,indent=2));return 0
    # CWD pode ser uma pasta arbitrária quando o .exe é aberto por atalho.
    workspace=opts.workspace if opts.workspace.is_absolute() else HOME/opts.workspace
    os.chdir(HOME)
    (HOME/'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.FileHandler(HOME/'logs'/'rca_rag.log',encoding='utf-8'),logging.StreamHandler()])
    if opts.diagnostico:diagnose(workspace.resolve());return 0
    import app
    args=sys.argv[1:]
    # Os assets vivem em _internal; os documentos ficam ao lado do executável.
    if not any(x=='--workspace' or x.startswith('--workspace=') for x in args):
        args+=['--workspace',str(workspace.resolve())]
    sys.argv=[sys.argv[0]]+args
    try:app.main()
    except OSError as exc:
        if getattr(exc,'winerror',None)==10048 or getattr(exc,'errno',None)==10048:
            raise RuntimeError('Porta em uso. Abra a instância já iniciada ou use Abrir_RAG.cmd --port 8766.') from exc
        raise
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        logging.exception('Falha ao iniciar o RAG portátil')
        print('\nERRO:',exc,'\nConsulte os manuais e logs. Copie a pasta inteira para um local com permissão de escrita.',file=sys.stderr)
        if sys.stdin and sys.stdin.isatty() and '--no-browser' not in sys.argv:
            try:input('Pressione Enter para fechar...')
            except (EOFError,KeyboardInterrupt):pass
        sys.exit(1)
