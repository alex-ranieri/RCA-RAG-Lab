"""Entrada da instalação por usuário, com dados fora dos arquivos do programa."""
from pathlib import Path
import os
import sys

import portable_main

portable_main.HOME = Path(os.environ['LOCALAPPDATA']) / 'RCA-RAG Lab'
portable_main.VERSION = '0.3.4-instalador-2026.11.16'

if __name__ == '__main__':
    try:
        portable_main.HOME.mkdir(parents=True, exist_ok=True)
        sys.exit(portable_main.main())
    except Exception:
        import traceback
        detail = traceback.format_exc()
        try:
            portable_main.HOME.mkdir(parents=True, exist_ok=True)
            (portable_main.HOME / 'falha_inicializacao.log').write_text(detail, encoding='utf-8')
        except OSError:
            pass
        print(detail, file=sys.stderr)
        if sys.stdin and sys.stdin.isatty() and '--no-browser' not in sys.argv:
            input('Falha ao iniciar. Pressione Enter para fechar...')
        sys.exit(1)
