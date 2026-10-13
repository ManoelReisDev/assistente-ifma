# SPEC-007 — Divisão por página

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-006 concluída.
- **Entrega:** Páginas extraídas podem ser divididas em trechos determinísticos e rastreáveis, sem cruzar a origem física.

## 2. Objetivo

Dividir os `Document` produzidos pela ingestão em trechos adequados às próximas etapas do RAG, preservando texto evidencial, documento, versão e página física. Tornar tamanho e sobreposição explícitos e impedir que entradas incompletas produzam evidências sem origem verificável.

## 3. Contexto

A ingestão já produz um `Document` por página com `document_id`, `document_name`, `document_hash` e `page_number`. A SPEC-006 delimitou o corpus e preparou casos de avaliação. Ainda não havia divisão, `chunk_id`, embeddings ou índice.

Os valores iniciais de 1.000 caracteres e 200 caracteres de sobreposição são parâmetros de desenvolvimento, não resultado de calibração. Sua adequação deverá ser medida nos casos de recuperação das próximas specs.

## 4. Pré-condições

- Ingestão por página e metadados da SPEC-004 disponíveis.
- Corpus e evidências de avaliação da SPEC-006 preparados.
- Ambiente sincronizável pelo `uv.lock` e testes comuns executáveis offline após o primeiro download.

## 5. Escopo

- Criar o módulo de divisão em trechos.
- Dividir recursivamente por caracteres, favorecendo parágrafos, artigos, linhas, frases e palavras.
- Configurar tamanho e sobreposição em `Settings` e validar seus limites.
- Processar cada página isoladamente.
- Copiar os metadados da página e atribuir `chunk_id` determinístico.
- Cobrir configuração, rastreabilidade, conteúdo e falhas de contrato com testes offline.
- Registrar a dependência e documentar o comportamento.

## 6. Fora do escopo

Embeddings, armazenamento vetorial, persistência dos trechos, reconstrução de índice, recuperação, limiar de similaridade, filtros por contexto, geração, validação de respostas, comandos `index` ou `ask` e calibração definitiva dos parâmetros. A divisão não seleciona quais documentos do diretório pertencem ao corpus e não comprova vigência ou aplicabilidade.

## 7. Requisitos funcionais

- **RF-01:** Receber uma sequência de páginas LangChain e retornar uma lista de trechos LangChain.
- **RF-02:** Nunca combinar conteúdo de páginas diferentes no mesmo trecho.
- **RF-03:** Preservar em cada trecho todos os metadados de origem e acrescentar `chunk_id`.
- **RF-04:** Preservar condições, negações, números e exceções; cada texto de trecho deve ser um excerto literal da página de origem.
- **RF-05:** Produzir os mesmos textos e identificadores para as mesmas páginas, versões e configuração.
- **RF-06:** Alterações de versão, posição ou configuração de divisão devem refletir-se na identidade do trecho e exigir reconstrução do futuro índice.
- **RF-07:** Uma entrada vazia deve produzir uma lista vazia, sem efeitos colaterais.

## 8. Requisitos técnicos

- **RT-01:** Usar `RecursiveCharacterTextSplitter` de `langchain-text-splitters` 1.x.
- **RT-02:** Medir `chunk_size` e `chunk_overlap` em caracteres, com padrões 1.000 e 200.
- **RT-03:** Exigir `chunk_size > 0`, `chunk_overlap >= 0` e `chunk_overlap < chunk_size`.
- **RT-04:** Usar separadores em ordem recursiva que priorize parágrafos e artigos antes de linhas, frases, palavras e caracteres.
- **RT-05:** Desabilitar remoção de espaços nas bordas para não reescrever o excerto devolvido pelo separador.
- **RT-06:** Calcular `chunk_id` com SHA-256 sobre identidade do documento, hash da versão, página física, posição e configuração de divisão.
- **RT-07:** Não modificar os `Document` recebidos nem criar arquivos durante a divisão.

## 9. Modelo e contratos

`chunk_documents(pages, settings=None) -> list[Document]` processa cada página na ordem recebida. A ordem dos trechos dentro da página é a ordem do texto.

Cada entrada deve ter texto não vazio e os metadados:

| Campo | Contrato |
| --- | --- |
| `document_id` | String não vazia com a identidade estável do documento |
| `document_name` | String não vazia com o nome exibível |
| `document_hash` | String não vazia com a versão do conteúdo |
| `page_number` | Inteiro começando em 1 |

Cada saída copia esses e quaisquer outros metadados recebidos, acrescentando `chunk_id` hexadecimal. A posição usada no identificador começa em zero dentro de cada página, mas não é exposta como metadado nesta etapa.

A configuração da divisão faz parte da identidade porque um índice construído com parâmetros diferentes não pode misturar trechos antigos e novos. O hash do documento identifica conteúdo, não vigência normativa.

## 10. Tratamento de erros

- Configuração com limites inválidos lança `ValueError` ao construir `Settings`.
- Página sem metadados obrigatórios, texto, página física válida ou strings de identidade válidas lança `ChunkingError`.
- Essas falhas são erros técnicos de preparação do corpus e não representam ausência de evidência para uma pergunta.
- A função não captura indiscriminadamente falhas inesperadas da biblioteca.

## 11. Arquivos afetados

- `specs/007-divisao-por-pagina.md`
- `src/academic_assistant/chunking.py`
- `src/academic_assistant/config.py`
- `tests/test_chunking.py`
- `tests/test_bootstrap.py`
- `pyproject.toml`
- `uv.lock`
- `README.md`

## 12. Estratégia de testes

- Validar padrões e combinações inválidas de tamanho e sobreposição.
- Dividir duas páginas e conferir que nenhum trecho cruza a origem.
- Conferir metadados extras, página, texto literal e ausência de mutação da entrada.
- Usar regras fictícias com condição, negação, prazo e exceção.
- Repetir a divisão e comparar identificadores.
- Alterar hash e configuração separadamente e conferir mudança da identidade.
- Rejeitar metadados ausentes, texto vazio e página física inválida.
- Executar a suíte completa offline e dividir o corpus local como prova adicional, sem persistir seu conteúdo.

## 13. Critérios de aceite

- **CA-01:** Todo trecho permanece vinculado a exatamente um documento, versão e página física.
- **CA-02:** Condições, negações, números e exceções fictícias permanecem no conteúdo dividido.
- **CA-03:** Todos os trechos são excertos literais da página de origem e respeitam o tamanho configurado.
- **CA-04:** IDs são únicos na execução e determinísticos para a mesma entrada e configuração.
- **CA-05:** Mudanças no hash da versão ou nos parâmetros de divisão alteram os IDs.
- **CA-06:** Configuração e páginas inválidas são rejeitadas explicitamente.
- **CA-07:** Dependências, testes, lockfile e documentação permanecem reproduzíveis.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Testes relevantes implementados e aprovados
- [x] Lockfile conferido em modo offline
- [x] Nenhum item fora do escopo implementado
- [x] README atualizado
- [x] Evidências de execução registradas

O item Maven do template foi substituído pelas verificações Python e uv aplicáveis ao projeto.

## 15. Critério de parada

Encerrar quando páginas puderem ser divididas de forma determinística, literal e rastreável, com configuração validada e testes aprovados. Não iniciar embeddings, persistência ou recuperação; a próxima etapa é a SPEC-008.

## 16. Evidências de execução — 2026-10-13

- `langchain-text-splitters` 1.1.3 foi resolvido e registrado no `uv.lock`.
- `uv run --extra dev --locked --offline pytest -q`: **32 testes aprovados**.
- A divisão dos 85 `Document` do lote local gerou **293 trechos**, todos limitados a uma página, com metadados obrigatórios e IDs únicos.
- Uma segunda divisão do mesmo corpus e configuração produziu os mesmos textos e identificadores.
- `uv lock --check --offline` e `git diff --check` foram aprovados.
