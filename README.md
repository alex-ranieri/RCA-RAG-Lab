# RCA-RAG Lab

Ferramenta local para conversar com PDFs usando LM Studio/Bionic. Versão 0.3.2,
de 16/11/2026. Interface em português, busca lexical BM25, busca por embeddings,
busca híbrida, referências por página e histórico de conversa.

## Instalar no Windows

Na seção **Releases** deste repositório, baixe
`Instalar_RCA_RAG_2026.11.16_v3_x64.exe` da versão `v0.3.2` e execute normalmente.
Windows 11 x64. A instalação ocorre por usuário, sem precisar de administrador.
O Python embutido e as bibliotecas acompanham o instalador; a instalação funciona
sem internet. LM Studio/Bionic e os modelos devem estar preparados separadamente.

Abra **Abrir RCA-RAG Lab** no menu Iniciar. O navegador acessa
`http://127.0.0.1:8765`. Mantenha a janela do servidor aberta; Ctrl+C encerra.
Ative a API local no LM Studio/Bionic, importe PDFs, clique em **Indexar PDFs**
e selecione um modelo de geração. A detecção automática consulta as portas 1234 e 1235.

## Alterações desta versão

- Seleção de PDFs para **Remover selecionados** ou **Limpar toda a base**.
- PDFs retirados são arquivados em `removidos`, fora da busca.
- Busca lexical dos documentos restantes atualizada automaticamente; vetores e
  caches anteriores são limpos. Gere embeddings novamente para usar busca vetorial.
- Confirmação antes de remover; conversa desta aba limpa após a operação.
- Espera padrão pelo modelo de 30 minutos, configurável de 1 a 120 minutos,
  com indicação do tempo decorrido na interface.

Os dados instalados ficam em `%LOCALAPPDATA%\RCA-RAG Lab` e são preservados
na atualização e desinstalação. Confira as respostas e citações nos PDFs originais.
PDFs escaneados precisam de OCR prévio; OCR não está incluído.

## Executar o código-fonte

Com Python 3.14 instalado, abra o PowerShell na raiz deste repositório:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --workspace colecoes\principal
```

Não é necessário ativar a venv. Para usar outra porta, acrescente `--port 8766`.
O servidor escuta somente em `127.0.0.1`, e o cliente aceita somente APIs locais.
Este pacote começa sem documentos ou índices. Os diretórios são criados no uso.

## Testes

Os testes usam PDFs fictícios gerados em memória, sem exigir documentos pessoais
ou um modelo real. Execute na raiz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Com Node.js disponível, os controles da interface também podem ser verificados:

```powershell
node packaging_rag\test_remove_ui.js
```

O teste de instalação `packaging_rag/test_installer.py` é específico de Windows,
usa diretórios temporários e exige um usuário não elevado sem instalação real
preexistente com o mesmo identificador. Após compilar o EXE conforme o guia:

```powershell
.\.venv\Scripts\python.exe packaging_rag\test_installer.py
```

## Código e compilação

- `app.py`: servidor HTTP local e operações da coleção.
- `rag_core.py`: extração, fragmentação, BM25 e referências.
- `lmstudio_api.py`: comunicação com a API local.
- `conversation.py`: histórico e orçamento de contexto.
- `recursos.py`: leitura de recursos da máquina.
- `web/`: interface HTML/JavaScript.
- `packaging_rag/`: iniciadores, script Inno Setup e preparação do instalador.
- `tests/`: testes independentes de documentos externos.

Veja [COMPILAR_WINDOWS.md](docs/COMPILAR_WINDOWS.md) para recriar o instalador e
[PUBLICAR_NO_GITHUB.md](PUBLICAR_NO_GITHUB.md) para publicar o código e a release.
As [instruções de uso](packaging_rag/LEIA-ME-INSTALADOR.txt) acompanham o instalador.
