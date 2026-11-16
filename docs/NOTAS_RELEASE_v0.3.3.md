RCA-RAG Lab 0.3.3 — Windows x64 — 16/11/2026

- Correção do top-K: o espaço de evidências é dividido entre os trechos selecionados.
- Exibição do top-K solicitado, trechos enviados ao modelo e trechos citados.
- Ajuste do texto das evidências para caber no contexto efetivamente carregado.
- Avisos da resposta deixam de aparecer com aparência de falha.
- Contextos de 1.024 a 131.072 tokens, respeitando o máximo declarado pelo modelo.
- Ajuda ao passar o mouse sobre os controles e opções.

Instalação por usuário, sem administrador, com Python embutido. Feche a versão
anterior antes de atualizar. Os documentos e índices existentes são preservados.
LM Studio/Bionic e modelos continuam sendo pré-requisitos externos.

Top-K é o máximo de trechos enviados como evidência, não a quantidade obrigatória
de citações na resposta. Aumentar o contexto exige mais memória e recarregar o modelo.

Validação: 40 testes do código, controles da interface, instalação e reinstalação
com token Windows não elevado. Teste real no LM Studio: top-K 5 enviou cinco trechos;
o modelo respondeu com uma citação válida, sem avisos nessa execução.
Teste de instalação nesta máquina de desenvolvimento, sem VM limpa. A execução
do desinstalador desta rodada foi bloqueada pela política de Controle de Aplicativo
do Windows (erro 4551), inclusive ao repetir a execução normal. A desinstalação
desta versão não foi validada. Nenhuma política de segurança foi alterada.
Executável sem assinatura digital de editor.

Arquivo: `Instalar_RCA_RAG_2026.11.16_v4_x64.exe`

SHA-256: `54ee67393995335ce6ebec116e287dc257fae3a92c7ff07092627ed65c0b4f17`
