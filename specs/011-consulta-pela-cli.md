# SPEC-011 — Consulta pela CLI

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-010 concluída; índice ativo e credencial NVIDIA configurados para uso real.
- **Entrega:** O terminal executa o fluxo completo pergunta → recuperação → geração → resposta com fontes verificáveis por meio do comando `ask`.

## 2. Objetivo

Disponibilizar a consulta do MVP sem exigir código Python. A CLI deve coletar a pergunta e o contexto aplicável, reutilizar o índice persistido, apresentar resposta e fontes no formato institucional e distinguir consulta concluída, contexto inválido e falha técnica.

## 3. Contexto

As SPEC-008 a SPEC-010 já fornecem índice persistente, recuperação filtrada, geração estruturada e validação determinística. Faltava uma entrada pública que coordenasse essas camadas sem misturar regras de apresentação ao núcleo.

## 4. Pré-condições

- PDFs e inventário correspondem ao índice ativo.
- Índice construído com a configuração atual.
- `NVIDIA_API_KEY` carregada no ambiente para consultas reais.
- Instituição e nível do curso informados pelo usuário.

## 5. Escopo

- Criar uma função de núcleo que coordena recuperação e geração.
- Adicionar o subcomando `ask` à CLI existente.
- Aceitar pergunta, instituição, nível do curso, campus, modalidade e caminhos configuráveis.
- Evitar inicializar serviços externos para pergunta vazia ou contexto ausente.
- Evitar criar o LLM quando a recuperação não retornar evidências.
- Imprimir resposta, documento, página física e excerto literal.
- Usar códigos de saída distintos para sucesso, erro técnico e entrada/contexto inválido.
- Documentar o fluxo operacional completo.

## 6. Fora do escopo

Sessão interativa, histórico de conversa, streaming, saída JSON, interface web, autenticação, observabilidade externa, avaliação completa do corpus real e publicação. A avaliação e a entrega final pertencem à SPEC-012.

## 7. Requisitos funcionais

- **RF-01:** `ask` recebe a pergunta como argumento posicional.
- **RF-02:** `--institution` e `--course-level` fornecem o contexto mínimo; `--campus` e `--modality` são opcionais.
- **RF-03:** `--documents-dir`, `--index-dir` e `--corpus-file` devem substituir os caminhos padrão sem copiar dados.
- **RF-04:** Pergunta vazia ou contexto ausente deve falhar antes da inicialização dos provedores.
- **RF-05:** O índice ativo deve ser carregado sem recalcular embeddings do corpus.
- **RF-06:** Recuperação vazia deve produzir abstenção sem criar o modelo de chat.
- **RF-07:** Consulta concluída deve imprimir `Resposta:` e, quando existentes, blocos `Fonte [n]` com documento, página e trecho.
- **RF-08:** Abstenção é consulta concluída e retorna código 0.
- **RF-09:** Contexto ausente ou não coberto retorna código 2; falha técnica retorna código 1 e não imprime resposta em `stdout`.

## 8. Requisitos técnicos

- **RT-01:** Manter `cli.py` responsável apenas por parsing, despacho, apresentação e mapeamento de erros.
- **RT-02:** Implementar a orquestração reutilizável em `query.py`.
- **RT-03:** Reutilizar `Settings`, `RetrievalContext`, `create_embeddings`, `retrieve_from_active_index`, `create_chat_model` e `generate_answer`.
- **RT-04:** Manter modelos e embeddings injetáveis para testes offline.
- **RT-05:** Não adicionar dependências nem alterar o formato do índice.
- **RT-06:** Não imprimir chaves, distâncias, hashes ou rastros de exceção por padrão.

## 9. Modelo e contratos

Uso padrão:

```bash
uv run --locked python -m academic_assistant ask \
  "Como funciona o aproveitamento de estudos?" \
  --institution IFMA \
  --course-level graduação
```

Opções de contexto adicionais: `--campus` e `--modality`. Os caminhos usam os mesmos padrões dos comandos anteriores e podem ser alterados com `--documents-dir`, `--index-dir` e `--corpus-file`.

Códigos de saída:

| Código | Significado |
| --- | --- |
| `0` | Consulta concluída, com resposta ou abstenção |
| `1` | Erro técnico de índice, recuperação, provedor ou validação |
| `2` | Pergunta ou contexto inválido/não coberto |

Formato:

```text
Resposta: <texto fundamentado> [1]

Fonte [1]
Documento: <nome real>
Página do PDF: <número físico>
Trecho: "<excerto literal>"
```

## 10. Tratamento de erros

- Pergunta vazia, contexto ausente ou contexto não coberto usam `Contexto inválido:` em `stderr` e código 2.
- Índice ausente, incompatível ou desatualizado, falha de embeddings, busca, LLM ou validação usam `Erro de consulta:` em `stderr` e código 1.
- A causa original permanece encadeada no núcleo, mas traceback e segredos não são exibidos pela CLI.
- A falta de evidência usa `stdout`, fontes vazias e código 0.

## 11. Arquivos afetados

- `specs/011-consulta-pela-cli.md`
- `src/academic_assistant/query.py`
- `src/academic_assistant/cli.py`
- `src/academic_assistant/indexing.py`
- `tests/test_query.py`
- `tests/test_cli_ask.py`
- `tests/test_indexing.py`
- `README.md`
- `PLANO-EXECUCAO.md`

## 12. Estratégia de testes

- Construir índice Chroma temporário com regra fictícia, encerrar a construção e consultar por nova carga.
- Comprovar que consulta não chama `embed_documents` e usa uma chamada de query.
- Validar resposta, fonte, página, excerto e limitação pelo fluxo integrado.
- Comprovar que recuperação vazia não cria o LLM.
- Comprovar pergunta/contexto inválido antes de serviços externos.
- Testar formatação e códigos 0, 1 e 2 da CLI.
- Executar a suíte completa offline, compilação, lockfile e whitespace.
- Executar o comando real em subprocesso separado, inspecionando somente estrutura e metadados da saída para não registrar excertos locais.

## 13. Critérios de aceite

- **CA-01:** O comando `ask` aparece na ajuda e aceita contexto e caminhos documentados.
- **CA-02:** Um índice persistido é reutilizado sem reindexação.
- **CA-03:** Uma pergunta sustentada produz resposta e fonte no formato exigido.
- **CA-04:** Uma consulta sem suporte conclui com a mensagem obrigatória e código 0.
- **CA-05:** Falhas técnicas usam `stderr` e código 1; contexto inválido usa código 2.
- **CA-06:** Testes comuns permanecem offline e sem chave.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Fluxo integrado offline aprovado
- [x] Formatação e códigos de saída testados
- [x] Nenhum item fora do escopo implementado
- [x] README atualizado

O item Maven do template foi substituído pelas verificações Python e uv aplicáveis ao projeto.

## 15. Critério de parada

Encerrar quando o terminal puder reutilizar o índice e apresentar uma resposta validada com fontes, mantendo abstenção e erros em caminhos distintos. Não executar a avaliação completa; a próxima etapa é a SPEC-012 — Avaliação e entrega.

## 16. Evidências de execução — 2026-10-13

- Os testes focados de consulta, CLI, geração, recuperação, índice e configuração aprovaram 45 casos antes das verificações finais.
- A suíte completa aprovou 70 testes offline.
- A ajuda de `ask`, a compilação de `src` e `tests`, o lockfile offline e a verificação de whitespace foram aprovados.
- Uma consulta real em subprocesso reutilizou o índice ativo, retornou código 0, manteve `stderr` vazio e produziu resposta com cinco blocos de fonte contendo documento, página física e excerto. O verificador registrou somente esses indicadores estruturais, sem expor o conteúdo dos PDFs.
