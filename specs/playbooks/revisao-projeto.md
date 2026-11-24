# Playbook — revisão do projeto

**Identificador:** `revisao-projeto`. Adaptado de `plan-big-execute-small`.
**Estado:** preparado; agentes ainda não executados.

## Objetivo e fluxo

Revisar o projeto existente com **três agentes em uma única onda paralela**:

| Agente | Responsabilidade | Entradas principais |
| --- | --- | --- |
| Estrutura | Organização, dependências e limites do fluxo RAG | `src/academic_assistant/*.py`, `pyproject.toml`, `tests/` |
| Frontend | Comportamento, acessibilidade e exibição das evidências | `src/academic_assistant/static/`, `web.py`, `tests/test_web.py` |
| Limpeza | Conteúdo redundante, obsoleto ou aparentemente não utilizado | Arquivos rastreados, documentação, empacotamento e referências |

O coordenador prepara os briefs e depois confere e consolida os resultados.
Os agentes não recebem os relatórios uns dos outros. Sobreposições são resolvidas
na consolidação, não por novas delegações automáticas.

Este playbook **diagnostica e propõe limpeza**, mas não modifica código nem remove
arquivos. Correções e exclusões precisam de aprovação posterior com caminhos explícitos.
Não cria commits, pushes ou PRs.

## Preparação e execução pelo coordenador

1. Ler `AGENTS.md`, `README.md`, `pyproject.toml` e instruções locais aplicáveis.
   Registrar `git status --short` e o commit atual. Não descartar mudanças existentes.
2. Usar o [fragmento YAML](revisao-projeto.yaml) como definição do fluxo.
   Para cadastrá-lo no Alethe, mesclar somente a entrada `revisao-projeto` no mapa
   `playbooks` da cópia do usuário, preservando os outros playbooks e preferências.
   **O fragmento não é uma configuração completa nem um plano executável.**
   O cadastro global não foi realizado por esta entrega.
3. Antes de lançar agentes, seguir o skill Alethe: verificar backend e providers
   disponíveis, quota atual e preços; resolver `standard` para cada agente e fixar
   modelo e esforço explicitamente no plano. Não assumir que leituras antigas
   representam quota disponível. Pedir autorização se quota/custo exigirem.
4. Criar fora do repositório o plano JSON v1 e os três briefs, com
   `strategy: research`, exatamente três workers, `mode: read-only` e
   `maxConcurrent: 3`. Usar `cwd` deste checkout. Não há escritores concorrentes;
   worktrees não são necessárias nesta revisão. Manter MCP desabilitado, exceto
   se uma verificação de navegador realmente o exigir e houver ferramenta disponível.
5. Definir orçamento antes da onda. Proposta para aprovação na execução:
   três chamadas, até 900 segundos e até 30.000 tokens reportados no total.
   Isso não é preferência persistente nem estimativa de preço. Sem retries
   automáticos: evidência insuficiente vira lacuna no relatório.
6. Validar o plano e conferir o `dry-run`, exibindo modelos, custo estimado e
   quota/forecast, inclusive quando desconhecidos. Criar uma orquestração com
   `new`, executar a onda com `run --detach` e aguardar conforme o skill.
   Não interpretar a simples criação deste playbook como pedido de execução.
7. Conferir `outcome.json` (status, falha e violação de leitura) e `result.md`
   de cada agente. Não carregar transcripts completos sem necessidade.
   Conferir o estado Git final contra o inicial; o coordenador pode salvar
   relatórios somente no diretório externo da orquestração.
8. Conferir as evidências dos achados importantes, marcar os resultados como
   `used`, `partial` ou `discarded` e emitir `report` do Alethe.
   Entregar também a síntese técnica com prioridades e itens não verificados.

## Contrato comum dos três briefs

- Ler `AGENTS.md` e o README; código atual prevalece sobre descrições históricas
  para determinar o que está implementado. Não usar isso para ignorar requisitos.
- Somente leitura do projeto. Sem edições, exclusões, instalação de dependências,
  reindexação, chamadas ao provedor real ou acesso à rede por padrão.
  Não delegar nem iniciar outro agente. Não fazer commit, push, tag, release ou PR.
- Não abrir `.env`, credenciais, PDFs privados, índices, conversas ou avaliações
  locais privadas. Para candidatos locais ignorados, consultar apenas caminhos
  e metadados necessários; não enviar seu conteúdo aos agentes.
  Código e documentação selecionados serão enviados ao provedor do worker.
- Testes permitidos usam dependências existentes, sem chaves e sem rede.
  Direcionar caches e arquivos temporários para a pasta externa da orquestração.
  Se o sandbox impedir a execução, registrar o impedimento; não enfraquecê-lo.
- Cada achado deve conter ID, severidade (`alta`, `média`, `baixa`), arquivo e
  linha quando aplicável, cenário de falha, evidência, impacto, recomendação
  mínima e teste sugerido. Para arquivos candidatos à limpeza, o caminho basta,
  acompanhado das buscas feitas. Separar achado confirmado de hipótese.
- Relatório de até 1.500 palavras por agente. Não preencher cota de achados:
  “nenhum achado confirmado” é válido. Informar comandos, códigos de saída,
  falhas e pontos não verificados. Não afirmar execução visual por ler HTML.
- Encerrar com `VERDICT: PASS | FAIL | NOT_PROVEN`, `NOT CHECKED: ...`,
  `STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT` e `SUMMARY: ...`.
  `PASS` exige todos os critérios do escopo demonstrados; falta de evidência
  é `NOT_PROVEN`, não aprovação nem defeito confirmado.

## Brief 1 — Estrutura

**Meta:** verificar se a organização atual sustenta o fluxo completo sem
complexidade desnecessária e sem quebrar os contratos do `AGENTS.md`.

**Escopo de leitura:** módulos Python de `src/academic_assistant/`,
`pyproject.toml`, `uv.lock`, testes e documentação relacionada. Ler `web.py`
somente para limites da interface com o núcleo; UX pertence ao agente Frontend.

**Verificar:**

- Separação entre configuração, ingestão, chunking, índice, recuperação, geração,
  validação, CLI e interface web; dependências circulares ou acoplamento com
  consequências concretas. Não propor framework ou camadas por preferência.
- Coerência de configuração e metadados; reuso do índice e publicação segura;
  distinção entre erro técnico, resposta parcial, conflito e falta de evidência.
- Preservação de fontes reais, condições e exceções; tratamento do texto
  recuperado como dados, não instruções. Distinguir validação estrutural de
  suporte semântico: mocks não provam confiabilidade de um LLM real.
- Empacotamento, dependências realmente usadas e adequação dos testes ao fluxo.
  Candidatos a remoção vão para a síntese, sem exclusão.

**Checagem prevista:** `.venv/bin/python -m pytest -q -p no:cacheprovider`.
Executar com `PYTHONDONTWRITEBYTECODE=1` e `TMPDIR` externo, se o ambiente
existente permitir; caso contrário, registrar o motivo. Não executar avaliações
com modelo real. Não atualizar números de testes no README.

**Concluído quando:** mapa curto das responsabilidades e contratos revisados,
achados comprováveis e lacunas de teste identificadas, sem modificar arquivos.

## Brief 2 — Frontend

**Meta:** revisar a interface atual de consulta, não redesenhá-la.

**Escopo de leitura:** `src/academic_assistant/static/`, `web.py`,
`tests/test_web.py` e contratos públicos de resultado/erro usados pela interface.
Não refatorar nem revisar novamente o pipeline interno.

**Verificar:**

- Envio por formulário/teclado, contexto acadêmico, validação de entrada,
  estados de carregamento, erro, abstenção e nova tentativa.
- Requisições duplicadas, respostas fora de ordem e histórico visual;
  não representar perguntas independentes como memória conversacional real.
- Documento, página física, excerto e vínculo entre resposta e fonte.
  Respostas parciais e conflitos não podem perder suas limitações na interface.
- Semântica HTML, labels, foco, navegação por teclado, anúncio de estados,
  contraste e responsividade. Diferenciar suspeita estática de medida real.
- Renderização segura de texto não confiável, incluindo respostas, fontes e
  mensagens de erro; fronteiras entre frontend e API.

**Checagem prevista:** `.venv/bin/python -m pytest -q tests/test_web.py -p no:cacheprovider`,
com as mesmas restrições de temporários e caches do contrato comum.
Se houver navegador e servidor de teste com dados sintéticos, conferir
360×800 e 1280×800, teclado, carregamento, erro e fontes. Não consultar o
provedor real nem apresentar a inspeção estática como teste visual.
Sem ambiente visual seguro, listar esses casos como não verificados.

**Concluído quando:** fluxos e estados revisados, achados com reprodução ou
evidência estática e limitações visuais explícitas, sem modificar arquivos.

## Brief 3 — Limpeza

**Meta:** identificar material dispensável sem perder evidência, dados ou
comportamento. Neste playbook, “limpar” significa produzir proposta revisável.

**Escopo de leitura:** inventário rastreado pelo Git, `.gitignore`, README,
`specs/`, `reports/`, `evaluation/`, referências em código, testes, configuração
e assets. Para arquivos ignorados/não rastreados, somente inventário de caminhos.

**Verificar:**

- Módulos, funções, assets e dependências aparentemente sem consumidores.
  Procurar imports, rotas, entrypoints, acesso dinâmico, URLs de assets,
  configuração de package-data, testes e comandos documentados.
- Documentação duplicada, comandos obsoletos e divergências com o código.
  Especificações históricas e relatórios não são inúteis apenas por serem antigos.
- Gerados, caches e artefatos de build: distinguir rastreados de ignorados.
  Um cache ignorado não é automaticamente um problema de manutenção do código.

**Checagens de leitura:** `git ls-files`, `git status --short --ignored`,
buscas direcionadas com `git grep -n` e leitura dos consumidores encontrados.
Excluir lockfile e documentos históricos não é consequência automática de uma
busca sem resultados. Não instalar ferramentas de detecção de código morto.

**Saída adicional obrigatória:**

| Caminho | Classe | Referências verificadas | Risco | Proposta |
| --- | --- | --- | --- | --- |
| Caminho real | gerado / redundante / possivelmente sem uso / preservar | Buscas e resultados | baixo / médio / alto | manter / investigar / propor remoção |

Nunca propor exclusão automática de `data/`, `.env`, `uv.lock`, fixtures,
relatórios de avaliação, arquivos não rastreados ou material privado.
Não usar `rm`, `git clean` ou exclusões recursivas.

**Concluído quando:** cada candidato tem evidência e risco, materiais que
precisam ser preservados estão identificados e nenhuma exclusão foi executada.

## Critérios de entrega da consolidação

- Contabilizar os três agentes, inclusive falhas e bloqueios.
- Deduplicar achados e resolver divergências por evidência; não por votação.
- Priorizar falhas de fontes, dados e fluxo antes de estilo ou reorganização.
- Entregar uma lista curta de correções sugeridas e uma tabela separada de
  remoções propostas, com caminhos explícitos e aprovação ainda pendente.
- Listar comandos realmente executados, resultados e verificações ausentes.
- Não declarar o MVP validado nem ausência de bugs com base nesta revisão.
