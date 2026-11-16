# Publicar o RCA-RAG Lab no GitHub

Se este repositório já está publicado, use [ATUALIZAR_NO_GITHUB.md](ATUALIZAR_NO_GITHUB.md). O roteiro abaixo é para um repositório novo.

Esta pasta contém o código-fonte da versão 0.3.3 e somente o instalador mais
recente, dentro de `release/`. Os binários dessa pasta são ignorados pelo Git:
o código vai para o repositório e o EXE é anexado em **Releases**.

## 1. Criar um repositório vazio

Entre na sua conta em [GitHub](https://github.com), escolha **New repository**,
use o nome `RCA-RAG-Lab` e selecione a visibilidade desejada.
Deixe desmarcadas as opções de criar README, `.gitignore` e licença: esta pasta
já tem README e `.gitignore`. Clique em **Create repository** e copie a URL HTTPS.
Este procedimento assume um repositório novo e vazio.

## 2. Enviar o código-fonte

Instale o Git para Windows, caso ainda não tenha. No Explorador de Arquivos,
abra esta pasta `RCA-RAG-Lab`, clique na barra de endereço, digite `powershell`
e pressione Enter. O terminal abrirá na pasta correta.

Execute os comandos abaixo. Troque `SEU_USUARIO` pelo usuário ou organização
da sua conta; se escolheu outro nome, troque também `RCA-RAG-Lab` na URL.

```powershell
git init
git branch -M main
git add .
git status --short
git commit -m "RCA-RAG Lab 0.3.3"
git remote add origin https://github.com/SEU_USUARIO/RCA-RAG-Lab.git
git push -u origin main
```

O Git pode solicitar que você entre na conta pelo navegador. Se o primeiro commit
pedir nome e email, configure-os apenas neste repositório e repita o commit:

```powershell
git config user.name "SEU NOME"
git config user.email "EMAIL DA SUA CONTA OU EMAIL NOREPLY DO GITHUB"
```

A pasta `release/` não aparecerá no commit por causa do `.gitignore`. Ela continua
no computador com o EXE para a etapa seguinte. Não use `git add -f` nesse fluxo.

## 3. Publicar somente a release atual

No repositório criado, abra **Releases > Draft a new release**.

1. Em **Choose a tag**, crie `v0.3.3` apontando para a branch `main`.
2. Título: `RCA-RAG Lab 0.3.3 — Windows x64`.
3. Copie a descrição de [docs/NOTAS_RELEASE_v0.3.3.md](docs/NOTAS_RELEASE_v0.3.3.md).
4. Na área de anexos, adicione estes dois arquivos da pasta local `release/`:
   `Instalar_RCA_RAG_2026.11.16_v4_x64.exe` e
   `Instalar_RCA_RAG_2026.11.16_v4_x64.exe.sha256`.
5. Marque **Set as latest release**, quando essa opção aparecer. Deixe
   **This is a pre-release** desmarcado para apresentar esta versão como estável.
6. Confira os anexos e clique em **Publish release**.

O GitHub disponibiliza automaticamente os arquivos do código-fonte em ZIP/tar.gz
na release. Não é preciso enviar um ZIP de código manualmente.
Nesta pasta de entrega não há instaladores das versões anteriores.

## 4. Conferir o resultado

- O repositório deve mostrar o README, o código, a interface e os testes.
- A release `v0.3.3` deve mostrar apenas o EXE v3 e o SHA-256 como anexos manuais.
- Para distribuir a ferramenta, compartilhe o endereço dessa release.

Você pode conferir o arquivo local no PowerShell:

```powershell
Get-FileHash .\release\Instalar_RCA_RAG_2026.11.16_v4_x64.exe -Algorithm SHA256
Get-Content .\release\Instalar_RCA_RAG_2026.11.16_v4_x64.exe.sha256
```

Os dois hashes devem ser iguais, desconsiderando maiúsculas e minúsculas.

## Referências

- [Enviar código local para o GitHub](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).
- [Criar e gerenciar releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
- [Distribuir binários por releases](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github#distributing-large-binaries).
