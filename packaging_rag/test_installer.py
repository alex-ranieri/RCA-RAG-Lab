"""Teste real de instalação, HTTP, atualização e desinstalação, sem elevação.

Usa /NOICONS para não modificar atalhos pessoais e diretórios de teste isolados.
"""
from pathlib import Path
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import winreg
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / 'distribuicao' / 'Instalar_RCA_RAG_2026.11.16_v5_x64.exe'
CASE = ROOT / 'tmp' / 'instalador_rag' / ('teste_' + str(time.time_ns()))
INSTALL = CASE / 'Instalação com espaços e acentuação'
CASE.mkdir(parents=True)
env = dict(os.environ, LOCALAPPDATA=str(CASE / 'perfil_usuario'))
Path(env['LOCALAPPDATA']).mkdir(parents=True)
env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
for name in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
    env.pop(name, None)
REPORT = {'status': 'running', 'case': str(CASE), 'checks': [],
          'installer_sha256': hashlib.sha256(SETUP.read_bytes()).hexdigest()}
TARGET = ROOT / 'docs' / 'validacao_instalador_20261116_v5.json'


def checked(name, detail=None):
    REPORT['checks'].append({'name': name, 'status': 'ok', 'details': detail})
    TARGET.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    print(name, 'OK', flush=True)


def run(command, **kwargs):
    result = subprocess.run(command, env=env, cwd=CASE, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=120,
                            creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{command}: {result.returncode}\n{result.stdout}\n{result.stderr}')
    return result


def install(label):
    run([str(SETUP), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS',
         '/DIR=' + str(INSTALL), '/LOG=' + str(CASE / (label + '.log'))])


def main():
    # Não usar uma execução administrativa para provar instalação por usuário.
    token = wintypes.HANDLE()
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                          wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    assert advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token))
    try:
        elevation, size = wintypes.DWORD(), wintypes.DWORD()
        assert advapi.GetTokenInformation(token, 20, ctypes.byref(elevation),
                                          ctypes.sizeof(elevation), ctypes.byref(size))
        assert elevation.value == 0, 'Execute o teste com token não elevado.'
    finally:
        kernel.CloseHandle(token)
    checked('Processo de teste com token Windows não elevado')
    key = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{E9C20D44-10D3-466B-A122-D026CE149634}_is1'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key):
            raise RuntimeError('Já existe instalação real; preservar e testar em outro perfil.')
    except FileNotFoundError:
        pass
    assert shutil.which('python', path=env['PATH']) is None
    install('instalacao')
    checked('Instalador concluiu sem administrador e sem Python no PATH')
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
        assert Path(winreg.QueryValueEx(handle, 'InstallLocation')[0]) == INSTALL
    checked('Desinstalador registrado apenas para o usuário')
    python = INSTALL / 'runtime' / 'python.exe'
    entry = INSTALL / 'app' / 'packaging_rag' / 'installed_main.py'
    verify = json.loads(run([str(python), str(entry), '--verificar', '--no-browser']).stdout)
    assert verify['status'] == 'ok' and verify['python_bundled'] == '3.14.10'
    checked('Runtime embutido, bibliotecas, PDF, BM25 e interface', verify)
    # Confere os arquivos realmente instalados contra o manifesto do payload.
    for line in (INSTALL / 'MANIFESTO_SHA256.txt').read_text(encoding='utf-8').splitlines():
        digest, file = line.split('  ', 1)
        assert hashlib.sha256((INSTALL / file).read_bytes()).hexdigest() == digest, file
    checked('Integridade de todos os arquivos instalados')
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    opener = build_opener(ProxyHandler({}))

    def api(path, body=None):
        req = Request(f'http://127.0.0.1:{port}' + path, data=body,
                      headers={'Content-Type': 'application/json'})
        with opener.open(req, timeout=20) as response:
            data = response.read()
            return json.loads(data) if response.headers.get_content_type() == 'application/json' else data

    log = (CASE / 'servidor.log').open('wb')
    proc = subprocess.Popen([str(python), str(entry), '--no-browser', '--port', str(port)],
                            env=env, cwd=CASE, stdout=log, stderr=log,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    data_root = Path(env['LOCALAPPDATA']) / 'RCA-RAG Lab'
    document = data_root / 'colecoes' / 'principal' / 'documentos' / 'teste.pdf'
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError('Servidor encerrou: ' + str(proc.returncode))
            try:
                if api('/api/health')['status'] == 'ok':
                    break
            except (OSError, URLError):
                time.sleep(.2)
        else:
            raise RuntimeError('Servidor não respondeu em 30 segundos.')
        assert b'Converse com seus PDFs' in api('/')
        assert b'value="131072"' in api('/')
        assert b'aria-description' in api('/app.js')
        assert b'id="allowContextOverflow"' in api('/')
        assert b'max="100"' in api('/')
        assert b'function history' in api('/app.js')
        info = api('/api/info')
        assert not info['pdfs'] and info['chunk_count'] == 0
        assert Path(info['workspace']) == data_root / 'colecoes' / 'principal'
        checked('Servidor HTTP e interface; coleção vazia separada do programa')
        content = b'BT /F1 12 Tf 50 700 Td (O prazo do emprestimo na biblioteca e de sete dias. A devolucao ocorre no balcao principal.) Tj ET'
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
                   b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                   b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
                   b'<< /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream']
        pdf, offsets = b'%PDF-1.4\n', [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(pdf))
            pdf += str(i).encode() + b' 0 obj\n' + obj + b'\nendobj\n'
        start = len(pdf)
        pdf += b'xref\n0 6\n0000000000 65535 f \n'
        pdf += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
        pdf += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
        api('/api/upload?name=teste.pdf', pdf)
        assert api('/api/index', b'{}')['documents'] == 1
        result = api('/api/search', json.dumps({'question': 'prazo emprestimo biblioteca'}).encode())
        assert 'sete dias' in result['evidence'][0]['text']
        assert document.read_bytes() == pdf
        checked('Upload de PDF, extração, indexação e busca por HTTP')
        assert b'removeSelected' in api('/') and b'clearBase' in api('/')
        api('/api/upload?name=segundo.pdf',pdf)
        api('/api/index',b'{}')
        retrieved=api('/api/search',json.dumps({'question':'emprestimo','top_k':5}).encode())
        assert retrieved['top_k_requested']==5 and retrieved['top_k_sent']==2
        checked('Top-K e novas opções de contexto/ajuda na interface instalada')
        removed=api('/api/documents/remove',json.dumps({'confirm':True,'filenames':['teste.pdf']}).encode())
        assert removed['remaining']==1 and removed['indexed']
        assert (Path(removed['archived_to'])/'teste.pdf').read_bytes()==pdf
        assert not document.exists()
        assert {item['doc'] for item in api('/api/search',json.dumps({'question':'emprestimo'}).encode())['evidence']}=={'segundo.pdf'}
        cleared=api('/api/documents/remove',json.dumps({'confirm':True,'all':True}).encode())
        assert cleared['remaining']==0 and not api('/api/info')['base_has_data']
        checked('Remoção seletiva e total no pacote instalado, com PDFs arquivados')
        # Restaura apenas a amostra fictícia para testar atualização/desinstalação.
        api('/api/upload?name=teste.pdf',pdf)
        api('/api/index',b'{}')

        try:
            models = api('/api/models')
            checked('Consulta às APIs locais', models)
        except (OSError, URLError) as exc:
            REPORT['local_api_limitation'] = str(exc)
    finally:
        proc.terminate()
        proc.wait(timeout=15)
        log.close()
    install('reinstalacao')
    assert document.read_bytes() == pdf
    assert (document.parent.parent / 'dados' / 'index.json').is_file()
    checked('Reinstalação preserva documentos e índices')
    run([str(INSTALL / 'unins000.exe'), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
         '/LOG=' + str(CASE / 'desinstalacao.log')])
    # O desinstalador pode concluir a limpeza em um processo filho temporário.
    deadline = time.monotonic() + 15
    while (INSTALL / 'runtime' / 'python.exe').exists() and time.monotonic() < deadline:
        time.sleep(.2)
    assert not (INSTALL / 'runtime' / 'python.exe').exists()
    assert document.read_bytes() == pdf
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key):
            raise AssertionError('Registro de desinstalação ainda existe')
    except FileNotFoundError:
        pass
    checked('Desinstalação remove programa e registro, preservando os documentos')
    REPORT['status'] = 'ok'
    REPORT['limitations'] = ['Teste nesta máquina, com token não elevado; sem VM limpa.',
                              'Atalhos não criados no teste silencioso (/NOICONS).',
                              'Não testada geração de respostas por um modelo.']
    TARGET.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    print(TARGET)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        if (INSTALL / 'unins000.exe').exists():
            try:
                run([str(INSTALL / 'unins000.exe'), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'])
            except Exception as cleanup_exc:
                REPORT['cleanup_error'] = str(cleanup_exc)
        REPORT['status'] = 'failed'
        REPORT['error'] = str(exc)
        TARGET.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
