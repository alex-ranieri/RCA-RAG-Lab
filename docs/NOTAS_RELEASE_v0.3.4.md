RCA-RAG Lab 0.3.4 — Windows x64

Novidades:

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


Feche a versão anterior antes de instalar. Instalação por usuário, sem
administrador, com Python embutido. Documentos e índices são preservados.
LM Studio/Bionic e modelos continuam sendo pré-requisitos externos.

Validação: 43 testes do código e testes dos controles da interface. Incluem
top-K 50, saída de 8.192 tokens, recomendações flexíveis, extrapolação explícita
e a diferença entre cinco trechos enviados e quatro citados. As chamadas de
geração desses testes são simuladas. A API local estava indisponível para repetir
uma geração real nesta rodada.
Instalação e reinstalação validadas com token Windows não elevado. A execução do desinstalador foi bloqueada pela política de Controle de Aplicativo do Windows (4551); esta etapa não foi validada. Nenhuma política de segurança foi alterada.
Teste de instalação nesta máquina de desenvolvimento, sem VM limpa.
Executável sem assinatura digital de editor.

Arquivo: `Instalar_RCA_RAG_2026.11.16_v5_x64.exe`

SHA-256: `d711ae09fb5f0f80deb73943abaa255846aea008eb1cb7fa65c9bf877e432c67`
