"""Prepara o Python embed e compila instalador offline, sem instalar no sistema.

Executar com Python 3.14; dependencias locais fornecidas por --packages.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import shutil
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--embed', type=Path, required=True)
    parser.add_argument('--packages', type=Path, required=True)
    parser.add_argument('--iscc', type=Path, default=Path(r'C:\Program Files\Inno Setup 7\ISCC.exe'))
    args = parser.parse_args()
    payload = ROOT / 'tmp' / 'instalador_rag' / str(time.time_ns()) / 'payload'
    runtime = payload / 'runtime'
    runtime.mkdir(parents=True)
    with zipfile.ZipFile(args.embed) as archive:
        archive.extractall(runtime)
    # O ._pth isola o runtime de Python/PYTHONPATH/pacotes do computador.
    (runtime / 'python314._pth').write_text(
        'python314.zip\n.\nLib/site-packages\n../app\n../app/packaging_rag\n', encoding='ascii')
    versions = {}
    for name, folder, version in [('pypdf', 'pypdf', '6.21.4'), ('fonttools', 'fontTools', '4.68.0')]:
        dist = next(d for d in metadata.distributions(path=[str(args.packages)])
                    if d.metadata['Name'].lower() == name)
        if dist.version != version:
            raise RuntimeError(f'{name}: esperado {version}; encontrado {dist.version}')
        versions[name] = dist.version
        shutil.copytree(args.packages / folder, runtime / 'Lib' / 'site-packages' / folder,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for file in dist.files or []:
            if '.dist-info' in file.parts[0]:
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = runtime / 'Lib' / 'site-packages' / str(file)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    code = payload / 'app'
    (code / 'packaging_rag').mkdir(parents=True)
    for file in ['app.py', 'rag_core.py', 'lmstudio_api.py', 'recursos.py', 'conversation.py']:
        shutil.copy2(ROOT / file, code / file)
    for file in ['portable_main.py', 'installed_main.py']:
        shutil.copy2(ROOT / 'packaging_rag' / file, code / 'packaging_rag' / file)
    shutil.copytree(ROOT / 'web', code / 'web')
    shutil.copy2(ROOT / 'packaging_rag' / 'LEIA-ME-INSTALADOR.txt', payload / 'LEIA-ME.txt')
    for file, extra in [('Abrir_RAG.cmd', ''), ('Diagnosticar_RAG.cmd', '--diagnostico'),
                        ('Verificar_pacote.cmd', '--verificar')]:
        (payload / file).write_text(
            '@echo off\nsetlocal\nchcp 65001 >nul\n'
            '"%~dp0runtime\\python.exe" "%~dp0app\\packaging_rag\\installed_main.py" '
            + extra + ' %*\n' + ('pause\n' if extra else 'if errorlevel 1 pause\n'), encoding='ascii')
    info = {'version': '0.3.3.2026.11.16', 'python': '3.14.10', 'dependencies': versions,
            'embed_sha256': hashlib.sha256(args.embed.read_bytes()).hexdigest(),
            'scope': 'RCA-RAG Lab; LM Studio e Bionic externos', 'per_user': True}
    (payload / 'VERSAO.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(payload).as_posix()
              for p in sorted(payload.rglob('*')) if p.is_file()]
    (payload / 'MANIFESTO_SHA256.txt').write_text('\n'.join(hashes) + '\n', encoding='utf-8')
    build_env = dict(os.environ, LOCALAPPDATA=str(payload.parent / 'verificacao_dados'))
    subprocess.run([str(runtime / 'python.exe'), str(code / 'packaging_rag' / 'installed_main.py'),
                    '--verificar', '--no-browser'], check=True, env=build_env)
    subprocess.run([str(args.iscc), '/Q', '/DPayloadDir=' + str(payload),
                    str(ROOT / 'packaging_rag' / 'installer.iss')], check=True)
    print('Payload:', payload)
    print('Instalador:', ROOT / 'distribuicao' / 'Instalar_RCA_RAG_2026.11.16_v4_x64.exe')


if __name__ == '__main__':
    main()
