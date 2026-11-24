# Correções da revisão — 24/11/2026

## Escopo

Correções dos nove achados confirmados da revisão de estrutura, frontend e
documentação. Trabalho realizado diretamente, sem novas chamadas de agentes.
Não houve exclusão de arquivos/dependências, alteração de PDFs/índice, leitura
de credenciais, chamada NVIDIA, commit ou publicação.

| Achado | Correção | Garantia automatizada |
| --- | --- | --- |
| EST-01 | `load_corpus_selection()` rejeita campus/modalidade que não sejam texto ou `null` | Oito entradas inválidas rejeitadas; valores válidos preservados; erro antes da busca e HTTP 503 no cadastro inválido |
| EST-02 | Teste de abstenção muda para diretório temporário e substitui a resolução de aplicabilidade | Não precisa do inventário privado nem cria modelo sem evidência |
| EST-03 | Conferência do limite antes de acrescentar vizinho | Primários ocupando exatamente o máximo não recebem trecho extra |
| F-01 | Repetição substitui o cartão no turno original; só envio novo limpa o compositor | Rascunho, pergunta, contexto e fontes preservados mesmo após nova falha |
| F-02 | Placeholder `#626d66`, opacidade 1 | Contraste calculado 5,386:1 sobre branco |
| L-01 | Template pede build Python com `uv build` | Build executado nesta tarefa |
| L-02 | Correção dos 21 links relativos quebrados; referência inexistente redirecionada para a seção de avaliação do README | Destinos Markdown locais conferidos por pytest |
| L-03 | README descreve FastAPI/recursos web; relatório geral identifica seu recorte histórico | Inspeção documental e teste de destinos |
| L-04 | README incorpora o encerramento registrado da SPEC-013 e preserva etapas históricas | Inspeção documental; sem nova auditoria dos artefatos privados |

## Evidência RED → GREEN

As jornadas de regressão vieram dos achados confirmados: impedir mistura de
contextos por metadados inválidos, respeitar o limite de evidências, repetir uma
consulta antiga sem perder seu turno/rascunho e executar testes sem corpus privado.

- Antes das correções Python: **13 falhas e três aprovações**, no recorte de
  inventário/recuperação/API. Falhas por ausência de rejeição dos tipos inválidos,
  resposta HTTP 200 indevida e acréscimo além do limite.
- O teste de abstenção existente, executado a partir de `/tmp/opencode`, falhou
  pela tentativa de abrir `evaluation/corpus.local.json`. Após o ajuste, passou
  no mesmo diretório externo.
- Antes das correções JavaScript/CSS: **três falhas**, por rascunho apagado,
  erro deslocado para outro turno e contraste 4,023:1. Após: **três aprovações**.
- Teste de links antes das correções: **três falhas e uma aprovação**.
  Após: os quatro documentos passaram.
- Recorte Python após as correções: **63 aprovações**.
- Suíte Python completa final: **190 aprovações**, sem skips.
- Cobertura Python com branches: **85% global**; `indexing.py` tem 72% e não
  deve ser apresentado como coberto integralmente.

Testes principais: `tests/test_indexing.py`, `tests/test_retrieval.py`,
`tests/test_query.py`, `tests/test_web.py`, `tests/test_documentation.py` e
`tests/frontend.test.cjs`. Não foram criados commits de checkpoint; o usuário
autorizou correções, não commits.

## Ambiente e comandos executados

O ambiente original foi preservado: `.venv/bin/python` aponta para
`/usr/bin/python3.10`, ausente nesta máquina. Python 3.14 não satisfaz o limite
atual de `onnxruntime`; a primeira tentativa de instalação isolada falhou.

Foi instalado Python **3.10.22** e criado um ambiente separado em
`/tmp/opencode/assistente-ifma-tests`. A sincronização com **uv 0.13.9** usou
`--locked --extra dev --extra web`, sem mudar `uv.lock` ou `pyproject.toml`.
`coverage` foi instalado apenas nesse ambiente temporário, como ferramenta de
medição; não é uma nova dependência do projeto.

Comandos de verificação executados na raiz, salvo indicação:

```bash
PYTHONDONTWRITEBYTECODE=1 ANONYMIZED_TELEMETRY=False \
  /tmp/opencode/assistente-ifma-tests/bin/python -m pytest -q -p no:cacheprovider
node --test tests/frontend.test.cjs
node --check src/academic_assistant/static/app.js
UV_PYTHON=/tmp/opencode/assistente-python/cpython-3.10.22-linux-x86_64-gnu/bin/python3.10 \
  /tmp/opencode/assistente-ifma-fixes/bin/uv lock --check --offline
UV_PYTHON=/tmp/opencode/assistente-python/cpython-3.10.22-linux-x86_64-gnu/bin/python3.10 \
  /tmp/opencode/assistente-ifma-fixes/bin/uv build --offline --out-dir /tmp/opencode/assistente-ifma-build
git diff --check
```

Todos concluíram com código zero. Cobertura medida com
`coverage run --branch --source=src/academic_assistant -m pytest -q -p no:cacheprovider`
e `coverage report --fail-under=80`, usando
`COVERAGE_FILE=/tmp/opencode/assistente-ifma.coverage`.

Wheel e sdist construídos. Inspeção do wheel confirmou HTML/CSS/JS atuais e
ausência de `.env`, corpus, índice e avaliações privadas. O lockfile permaneceu
compatível; não foi atualizado.

## Conferência em navegador

Servidor temporário FastAPI em loopback com inventário e respostas inteiramente
fictícios, sem modelo real. No navegador Chromium do OpenCode:

1. Pergunta A no campus Norte falhou.
2. Pergunta B no campus Sul foi enviada por Enter e recebeu resposta/fontes.
3. Digitado “Rascunho C”; repetição de A falhou novamente no turno de A.
4. Outra repetição de A concluiu no mesmo turno, com contexto Norte e fontes
   de A; B permaneceu no Sul, sem alteração.
5. Rascunho C preservado; quatro cartões na ordem pergunta A, resposta A,
   pergunta B, resposta B. Placeholder computado `rgb(98, 109, 102)`, opacidade 1.

Viewport observado: **800×618**, sem overflow horizontal. O servidor temporário
foi encerrado; não é o servidor da aplicação com configuração real.

## Limitações preservadas

- Não houve avaliação semântica nova nem transferência de aprovação entre modelos.
- Não foram conferidos todos os breakpoints, leitores de tela ou navegadores.
- Os testes Node usam DOM mínimo; a conferência Chromium cobre o fluxo acima,
  não uma suíte E2E completa nem conformidade WCAG integral.
- Não foi reparado/substituído o ambiente `.venv` original.
- A dependência `langchain` foi preservada: a revisão não comprovou que sua
  remoção é segura.
