# SPEC-012 — Avaliação e entrega

## 1. Metadados

- **Estado:** Concluída com limitações semânticas registradas
- **Dependências:** SPEC-006 a SPEC-011 concluídas; índice ativo e credencial NVIDIA configurados.
- **Entrega:** Avaliação reproduzível do MVP com casos reais e sintéticos, métricas separadas, revisão humana e relatório final consolidado.

## 2. Objetivo

Verificar o fluxo completo com os modelos escolhidos e as evidências revisadas, medir capacidades distintas sem reduzir qualidade a uma única nota e registrar provas suficientes para decidir se o MVP atende aos critérios do `AGENTS.md`.

## 3. Contexto

Os testes offline comprovam contratos e caminhos de erro usando dados fictícios. Eles não demonstram que a recuperação real encontra as páginas esperadas nem que o LLM preserva condições, exceções, negações e abstenção. Esta etapa executa os casos revisados separadamente do `pytest` e mantém perguntas, respostas e excertos reais em arquivos locais ignorados pelo Git.

## 4. Pré-condições

- `evaluation/corpus.local.json` e `evaluation/cases.local.json` revisados.
- `evaluation/synthetic-cases.json` versionado.
- Índice ativo compatível com os PDFs e a configuração.
- `NVIDIA_API_KEY` disponível no ambiente.

## 5. Escopo

- Executar uma tentativa por caso com os modelos NVIDIA configurados.
- Medir recuperação, estado da resposta, citações, abstenção e contexto.
- Revisar manualmente suporte semântico e preservação dos requisitos de cada caso.
- Registrar configuração, hashes, prompt, índice, versão do código, chamadas e disponibilidade de custo.
- Permitir repetir casos específicos após uma correção.
- Atualizar documentação, relatório de progresso e evidências das specs.

## 6. Fora do escopo

Interface web, múltiplos provedores, juiz LLM adicional, telemetria externa, comprovação jurídica de vigência, atualização automática do corpus e benchmark Harbor.

## 7. Requisitos funcionais

- **RF-01:** O comando `evaluate` executa casos reais e sintéticos fora do `pytest`.
- **RF-02:** O relatório local preserva entrada, recuperação, resposta, fontes, erros e verificações por caso.
- **RF-03:** O executor mede recuperação das evidências, estado esperado, precisão e cobertura das citações, abstenção e contexto.
- **RF-04:** A revisão semântica é aplicada por comando separado sem repetir chamadas externas.
- **RF-05:** `--only-case` permite repetir somente casos afetados.
- **RF-06:** Um limite de chamadas interrompe a execução antes de exceder o orçamento configurado.
- **RF-07:** Falhas técnicas permanecem distintas de abstenção.

## 8. Requisitos técnicos

- **RT-01:** Não incluir chave NVIDIA nem conteúdo local do relatório em arquivos versionados.
- **RT-02:** Registrar hash do prompt, código, corpus e arquivos de casos.
- **RT-03:** Registrar modelo, parâmetros, índice, hashes dos documentos e contagem de chamadas.
- **RT-04:** Registrar custo como indisponível quando o provedor não fornecer esse dado.
- **RT-05:** Usar somente biblioteca padrão e dependências existentes.
- **RT-06:** Testes automatizados usam embeddings, índice, documentos e modelo fictícios offline.

## 9. Modelo e contratos

`evaluation/results.local.json` contém metadados, uso do provedor, métricas agregadas e registros por caso. Ele pode reproduzir perguntas, respostas e excertos dos PDFs e, por isso, permanece ignorado.

`evaluation/reviews.local.json` contém `format_version`, identificação do revisor, data e uma entrada por caso com `semantic_support`, `requirements_preserved`, `supported_citation_count` e uma nota curta. O comando `evaluate-review` incorpora essas decisões ao relatório sem chamar os provedores.

As métricas não são probabilidades. Recuperação e citações comparam documento, página física e correspondência literal normalizada do excerto revisado. A revisão humana avalia se a conclusão é sustentada e se condições, exceções e negações foram preservadas.

## 10. Tratamento de erros

- Caso, relatório ou revisão incompatível produz erro técnico e código 1.
- Limite de chamadas atingido interrompe antes da próxima chamada.
- Falhas de índice, recuperação, geração ou validação são registradas por caso e não viram falta de evidência.
- Revisão ausente mantém as métricas semânticas incompletas.

## 11. Arquivos afetados

- `specs/012-avaliacao-e-entrega.md`
- `src/academic_assistant/evaluation.py`
- `src/academic_assistant/cli.py`
- `tests/test_evaluation.py`
- `evaluation/results.local.json` — local e ignorado
- `evaluation/reviews.local.json` — local e ignorado
- `README.md`
- `RELATORIO-PROGRESSO.md`
- `PLANO-EXECUCAO.md`

## 12. Estratégia de testes

- Validar métricas com índice, modelo e regras fictícios.
- Confirmar interrupção pelo limite de chamadas.
- Confirmar aplicação de revisão sem chamadas externas.
- Executar a suíte completa offline, compilação, lockfile e whitespace.
- Executar a avaliação real separadamente e revisar todas as respostas e fontes.
- Repetir apenas casos afetados por correções e depois a regressão pertinente.

## 13. Critérios de aceite

- **CA-01:** Relatório registra configuração e proveniência suficientes para reprodução.
- **CA-02:** Cada caso tem resultado automatizado ou erro técnico explícito.
- **CA-03:** Recuperação, suporte semântico, citações e abstenção são medidos separadamente.
- **CA-04:** Casos de conflito, condição, exceção, negação e instrução maliciosa são revisados.
- **CA-05:** Casos sem suporte não exibem regra acadêmica sem fonte.
- **CA-06:** Todos os critérios do MVP têm evidência ou limitação explícita.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Testes relevantes implementados e aprovados
- [x] Avaliação real executada e revisada
- [x] Problemas encontrados corrigidos ou registrados
- [x] Documentação e relatório atualizados

## 15. Critério de parada

Encerrar quando a execução real, a revisão humana e as verificações offline produzirem evidências suficientes para declarar o estado do MVP sem ocultar falhas ou limitações.

## 16. Evidências de execução — 2026-10-13

- O executor concluiu 21 casos: 16 locais revisados e cinco sintéticos.
- Uma falha transitória do provedor em IFMA-012 foi repetida isoladamente e consolidada somente após conferir compatibilidade de prompt, índice, corpus, modelos e arquivos de casos.
- O relatório consolidado registrou 38 chamadas: 16 de embeddings e 22 de geração, sob limites explícitos. O custo monetário não foi fornecido pela integração.
- Recuperação: 100%; cobertura das citações esperadas: 95%; precisão semântica das citações: 91,67%; estados: 95,24%; abstenção e contexto: 100%; suporte semântico e requisitos preservados: 90,48%.
- Conflito, resposta parcial, exceção, negação e instrução maliciosa sintéticos foram aprovados.
- IFMA-002 apresentou abstenção indevida; IFMA-013 generalizou além da evidência antes da ressalva; IFMA-001 omitiu uma condição cumulativa; IFMA-011 sobrecitou duas fontes relacionadas. Por isso, a avaliação foi concluída, mas o MVP não foi declarado semanticamente validado a 100%.
- A verificação final aprovou 80 testes offline, compilação, lockfile, JSONs locais, whitespace e exclusões do Git.

