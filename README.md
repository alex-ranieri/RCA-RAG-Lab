# RCA-RAG Lab

<p align="center">
  <a href="https://github.com/alex-ranieri/RCA-RAG-Lab/releases/tag/v0.3.4"><img src="https://img.shields.io/badge/Release-v0.3.4-176C62?style=flat-square" alt="Release v0.3.4"></a>
  <img src="https://img.shields.io/badge/Windows-11%20x64-0078D4?style=flat-square" alt="Windows 11 x64">
  <img src="https://img.shields.io/badge/IA-Local-176C62?style=flat-square" alt="Inteligência artificial local">
  <img src="https://img.shields.io/badge/Interface-PT--BR-475569?style=flat-square" alt="Interface em português">
</p>

Ferramenta local para conversar com PDFs usando LM Studio/Bionic. Versão 0.3.4,
de 16/11/2026. Interface em português, busca lexical BM25, busca por embeddings,
busca híbrida, referências por página e histórico de conversa.

## Materiais e downloads do curso

Recursos para preparar o ambiente e acompanhar as atividades práticas de IA local, RAG e agentes aplicados a documentos.

| Recurso | Descrição | Download |
| --- | --- | --- |
| **RCA-RAG Lab** | Instalador da ferramenta de RAG local para Windows 11 x64. | [![Baixar RCA-RAG Lab](https://img.shields.io/badge/Baixar-RCA--RAG%20Lab-176C62?style=flat-square&logo=github&logoColor=white)](https://github.com/alex-ranieri/RCA-RAG-Lab/releases/download/v0.3.4/Instalar_RCA_RAG_2026.11.16_v5_x64.exe) |
| **Modelos de IA local** | Modelos necessários para as atividades práticas do curso. | [![Baixar modelos](https://img.shields.io/badge/Baixar-Modelos-176C62?style=flat-square&logo=googledrive&logoColor=white)](https://drive.google.com/drive/folders/1yaCp1dJQngLddHpL7ctNv-dJez7YyCBU?usp=sharing) |
| **DocNexus** | Ferramenta complementar para as atividades de organização e conexão de documentos. | [![Baixar DocNexus](https://img.shields.io/badge/Baixar-DocNexus-176C62?style=flat-square&logo=googledrive&logoColor=white)](https://drive.google.com/drive/folders/1_Nz19dE7CyNPvZHMoCzD4Dbmw9I7Xii1?usp=sharing) |

Os modelos e o DocNexus são distribuídos separadamente do instalador do RCA-RAG Lab. Prepare os modelos no LM Studio/Bionic antes das atividades práticas.

## Instalar no Windows

Na seção [**Releases**](https://github.com/alex-ranieri/RCA-RAG-Lab/releases/tag/v0.3.4) deste repositório, baixe
`Instalar_RCA_RAG_2026.11.16_v5_x64.exe` da versão `v0.3.4` e execute normalmente.
Windows 11 x64. A instalação ocorre por usuário, sem precisar de administrador.
O Python embutido e as bibliotecas acompanham o instalador; a instalação funciona
sem internet. LM Studio/Bionic e os modelos devem estar preparados separadamente.

Abra **Abrir RCA-RAG Lab** no menu Iniciar. O navegador acessa
`http://127.0.0.1:8765`. Mantenha a janela do servidor aberta; Ctrl+C encerra.
Ative a API local no LM Studio/Bionic, importe PDFs, clique em **Indexar PDFs**
e selecione um modelo de geração. A detecção automática consulta as portas 1234 e 1235.

## Alterações desta versão

- Top-K de 1 a 100, com sugestões e recomendações associadas ao contexto carregado.
- Saída máxima de 32 a 131.072 tokens; removida a instrução fixa de até 80 palavras.
- Entrada dos PDFs de 1.000 a 1.000.000 de caracteres, distinta da saída em tokens.
- Recomendações podem ser ultrapassadas com aviso. Por padrão, ajusta-se o envio
  quando ele não cabe no contexto, informando os valores solicitados e efetivos.
- A opção **Permitir extrapolar contexto estimado** tenta enviar sem esses ajustes
  quando a estimativa excede o contexto. Isso não aumenta a capacidade real do modelo:
  o LM Studio pode recusar ou truncar o pedido.
- Top-K é um máximo de trechos enviados, não uma obrigação de citar todos.
  Cinco trechos enviados podem resultar em quatro citações.
- Ausência de citações é um aviso de verificabilidade, não uma falha de geração.
- Mantidos os contextos de 1.024 a 131.072 tokens, a ajuda ao passar o mouse e
  a remoção seletiva/total de PDFs da base com arquivamento fora da busca.

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

## Tecnologias utilizadas

### Aplicação e interface

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)](https://developer.mozilla.org/pt-BR/docs/Web/HTML)
[![CSS](https://img.shields.io/badge/CSS-663399?style=flat-square&logo=css&logoColor=white)](https://developer.mozilla.org/pt-BR/docs/Web/CSS)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript)
[![JSON](https://img.shields.io/badge/JSON-475569?style=flat-square&logo=json&logoColor=white)](https://www.json.org/)

### Processamento documental e IA local

[![pypdf](https://img.shields.io/badge/pypdf-6.21.4-3776AB?style=flat-square)](https://pypi.org/project/pypdf/)
[![fonttools](https://img.shields.io/badge/fonttools-4.68.0-3776AB?style=flat-square)](https://pypi.org/project/fonttools/)
[![LM Studio](https://img.shields.io/badge/LM%20Studio-Local%20API-6254C8?style=flat-square)](https://lmstudio.ai/)
![Bionic](https://img.shields.io/badge/Bionic-Local%20API-6254C8?style=flat-square)

### Empacotamento e testes

[![Inno Setup](https://img.shields.io/badge/Inno%20Setup-7.1.1-475569?style=flat-square)](https://jrsoftware.org/isinfo.php)
[![Node.js](https://img.shields.io/badge/Node.js-Testes-339933?style=flat-square&logo=nodedotjs&logoColor=white)](https://nodejs.org/)
![unittest](https://img.shields.io/badge/unittest-Python-3776AB?style=flat-square)

| Componente | Implementação |
| --- | --- |
| Backend | Python e biblioteca padrão (`http.server`, `urllib.request`) para servidor HTTP e comunicação com a API local. |
| Frontend | HTML, CSS e JavaScript nativo, sem framework web. |
| Documentos | `pypdf` para extração de texto por página; `fonttools` incluído nas dependências. |
| Recuperação | BM25, similaridade de cosseno e fusão de rankings por Reciprocal Rank Fusion (RRF), implementados em Python. |
| Inferência | Integração HTTP com LM Studio/Bionic para geração e embeddings locais. |
| Persistência | Índices textuais e vetoriais em arquivos JSON na coleção local. |
| Distribuição | Python 3.14.10 embutido e Inno Setup 7.1.1 para instalação offline no Windows. |
| Validação | `unittest` para testes Python e Node.js para testes dos controles da interface (não é necessário para executar a aplicação). |

Tecnologias identificadas em [`requirements.txt`](requirements.txt), [`app.py`](app.py), [`rag_core.py`](rag_core.py), [`lmstudio_api.py`](lmstudio_api.py), [`web/`](web/) e no [guia de compilação](docs/COMPILAR_WINDOWS.md).

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

Para atualizar um repositório já publicado, veja [ATUALIZAR_NO_GITHUB.md](ATUALIZAR_NO_GITHUB.md).
