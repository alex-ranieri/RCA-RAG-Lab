# Atualizar o GitHub para a versão 0.3.3

A pasta RCA-RAG-Lab já está atualizada com os fontes e o novo instalador v4.
O repositório e o remote existentes foram preservados. Não execute git init nem
git remote add novamente.

## 1. Conferir e enviar o código

Abra o PowerShell dentro da pasta RCA-RAG-Lab que você já publicou e execute:

```powershell
git status --short
git remote -v
```

O remote origin deve ser `https://github.com/alex-ranieri/RCA-RAG-Lab.git`.
Confira as alterações e envie:

```powershell
git add .
git status --short
git commit -m "Corrige top-K e adiciona contexto e ajuda - v0.3.3"
git push origin main
```

Se aparecer novamente o aviso de propriedade da pasta, execute somente esta
exceção no SEU PowerShell e repita os comandos anteriores:

```powershell
git config --global --add safe.directory "C:/Users/VIPER/Documents/RCA_2026_tool/publicar_github/RCA-RAG-Lab"
```

O `.exe` e o arquivo SHA-256 ficam em `release/` e são ignorados pelo Git. Eles
serão enviados como anexos na próxima etapa. Não use `git add -f` para os binários.

## 2. Publicar o novo instalador

Abra [as releases do repositório](https://github.com/alex-ranieri/RCA-RAG-Lab/releases)
e clique em **Draft a new release**.

1. Crie a tag **v0.3.3**, apontando para **main**, após o push do código.
2. Título: **RCA-RAG Lab 0.3.3 — Windows x64**.
3. Copie a descrição de [docs/NOTAS_RELEASE_v0.3.3.md](docs/NOTAS_RELEASE_v0.3.3.md).
4. Anexe os arquivos locais `release/Instalar_RCA_RAG_2026.11.16_v4_x64.exe`
   e `release/Instalar_RCA_RAG_2026.11.16_v4_x64.exe.sha256`.
5. Marque **Set as latest release**, se essa opção aparecer, e publique.

Crie uma release nova para que a tag antiga continue correspondendo à versão
anterior. A pasta local `release/` contém apenas o instalador atual.

## 3. Atualizar a ferramenta instalada

Encerre a janela do servidor anterior e execute o instalador v4 normalmente,
sem executar como administrador. Abra novamente pelo menu Iniciar e recarregue
a página do navegador. Os documentos e índices são preservados.

Na interface, ajuste o contexto e clique em **Aplicar ao modelo** para recarregar
o modelo com esse tamanho. Contextos maiores precisam de mais memória; opções
acima do máximo declarado pelo modelo ficam desabilitadas.

Veja também a [documentação de releases do GitHub](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
