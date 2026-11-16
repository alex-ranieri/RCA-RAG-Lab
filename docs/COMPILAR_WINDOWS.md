# Recriar o instalador Windows

O código nesta pasta corresponde ao instalador 0.3.2. A preparação usa Python
3.14.10 embed x64 e Inno Setup 7.1.1. O instalador tem `PrivilegesRequired=lowest`,
usa `%LOCALAPPDATA%\Programs\RCA-RAG Lab` e registra a desinstalação por usuário.

## Preparar as ferramentas

Instale um Python 3.14 para desenvolvimento e o Inno Setup. Obtenha também
`python-3.14.10-embed-amd64.zip`; mantenha esse ZIP fora do repositório, por
exemplo em Downloads. O Python para desenvolvimento executa o build; o ZIP
embed é o runtime que será distribuído com a ferramenta.

Na raiz do projeto:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Os pacotes são fixados em `pypdf==6.21.4` e `fonttools==4.68.0`. O build confere
essas versões e copia os pacotes e seus metadados/licenças para o runtime.
O Python embed é isolado por `python314._pth`; não depende de Python no PATH
da máquina de destino. O instalador mantém LM Studio/Bionic e modelos externos.

## Compilar

O exemplo assume o ZIP em Downloads e o Inno Setup na pasta padrão indicada.
Ajuste os caminhos se necessário. Execute na raiz:

```powershell
.\.venv\Scripts\python.exe packaging_rag\build_installer.py --embed "$env:USERPROFILE\Downloads\python-3.14.10-embed-amd64.zip" --packages .venv\Lib\site-packages --iscc "C:\Program Files\Inno Setup 7\ISCC.exe"
```

O resultado será `distribuicao/Instalar_RCA_RAG_2026.11.16_v3_x64.exe`.
O build prepara o payload em uma subpasta nova de `tmp/instalador_rag/` e
sobrescreve o EXE de mesmo nome em `distribuicao/`.

Para testar instalação, atualização e desinstalação reais:

```powershell
.\.venv\Scripts\python.exe packaging_rag\test_installer.py
```

Execute com usuário Windows não elevado e sem uma instalação real da ferramenta
nesse perfil. O teste recusa substituir uma instalação existente. Ele usa PDFs
fictícios, verifica remoção seletiva/total, hashes e preservação dos dados, e
desinstala a própria cópia temporária. O relatório fica em `docs/`, ignorado pelo Git.

## Preparar a publicação

O EXE já presente em `release/` é a entrega validada. Ao recompilar e decidir
substituí-lo, copie o novo EXE de `distribuicao/` para `release/` e gere seu SHA-256.
Se modificar o código, altere a versão e o nome do instalador antes de publicar
uma nova versão. Não apresente um EXE recompilado como se fosse o arquivo original.

O pacote de publicação não inclui os ambientes de desenvolvimento, o ZIP embed,
o compilador Inno Setup ou dados de usuários.
