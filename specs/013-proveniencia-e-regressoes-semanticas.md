# SPEC-013 — Proveniência da avaliação e regressões semânticas

## 1. Metadados

- **Estado:** Finalizada — diagnóstico, candidato focal e nova regressão integral revisados por Manoel
- **Data:** 15 de outubro de 2026
- **Dependências:** SPEC-006 a SPEC-012; corpus e casos revisados, índice compatível e fluxo de consulta existentes.
- **Entrega:** Avaliações com origem verificável por resultado, revisão humana vinculada à saída examinada e correções avaliadas dos casos `IFMA-001`, `IFMA-002`, `IFMA-013` e `IFMA-011`.

A criação desta SPEC definiu trabalho futuro. A execução registrada na seção 16 implementou a infraestrutura e produziu novos experimentos; não declara aprovação semântica sem revisão humana vinculada.

## 2. Objetivo

Permitir identificar com qual código, configuração, documentos e casos cada resposta foi produzida, impedir consolidações que apresentem experimentos diferentes como uma única execução e corrigir quatro falhas semânticas já observadas sem enfraquecer fontes, abstenção ou tratamento de erros.

O sucesso exige duas provas independentes: integridade da avaliação demonstrada por testes offline e qualidade das respostas demonstrada por execução real com revisão das evidências. Uma não substitui a outra.

## 3. Contexto e evidências

### 3.1. Proveniência atual

Em [evaluation.py](../src/academic_assistant/evaluation.py):

- `run_evaluation()` registra hashes e parâmetros globalmente, depois de executar os casos; os resultados não possuem vínculo explícito com uma execução individual.
- `merge_retry_report()` compara prompt, nomes de modelos, índice, arquivos de casos e corpus. Não compara fingerprint do código, parâmetros de recuperação/geração, dimensão ou todos os demais campos de compatibilidade.
- A consolidação substitui o fingerprint global pelo da repetição mais recente e registra o anterior em `reruns`. Os resultados mantidos podem ter sido produzidos por código diferente daquele apresentado globalmente.
- A consolidação remove todas as revisões, inclusive de resultados não substituídos, e soma contagens sem detectar reaplicação da mesma repetição.
- `apply_manual_reviews()` associa decisões humanas pelo ID do caso. Uma revisão antiga com o mesmo ID pode ser aplicada a uma resposta nova sem que essa correspondência seja comprovada.

O relatório local da SPEC-012 reúne 21 casos e registra duas consolidações com fingerprints anteriores distintos. É uma referência histórica útil, mas não uma baseline homogênea cuja origem por resultado possa ser reconstruída apenas dos metadados finais. Não atribuir retrospectivamente o código atual aos registros antigos.

### 3.2. Quatro regressões observadas

| Caso | Falha registrada | Resultado exigido na nova avaliação |
| --- | --- | --- |
| `IFMA-001` | Resposta sobre frequência omitiu requisito cumulativo de aprovação direta | Preservar todos os requisitos materiais da evidência revisada; não apresentar frequência como requisito suficiente |
| `IFMA-002` | Abstenção apesar de recuperar a regra que responde à hipótese da pergunta | Responder à hipótese negativa e explicar a conjunção dos requisitos, com fonte pertinente |
| `IFMA-013` | Resposta parcial preservou a condição, mas inferiu exclusividade não demonstrada | Explicar somente o grupo coberto; declarar que a generalização solicitada não está sustentada, sem inferir regra para outros grupos |
| `IFMA-011` | Quatro fontes anexadas; revisão considerou apenas duas sustentadas | Cobrir procedimento e critérios, citar separadamente as páginas necessárias e excluir fontes que não sustentam nenhuma afirmação exibida |

Os IDs, estados esperados e observações foram conferidos em `evaluation/cases.local.json`, `evaluation/results.local.json` e `evaluation/reviews.local.json`. Os conteúdos normativos permanecem nesses artefatos locais, sem reprodução nesta SPEC.

As falhas são resultados observados, não causas já comprovadas. O prompt atual já orienta condições cumulativas e limites de generalização. Acrescentar instruções semelhantes ou novas tentativas sem diagnóstico não é evidência de correção.

## 4. Pré-condições

- Ler [AGENTS.md](../AGENTS.md), [README](../README.md), contratos de avaliação e testes relevantes.
- Preservar relatórios e revisões da SPEC-012; escolher novos caminhos locais para diagnóstico, candidato e regressão final.
- Conferir os requisitos dos quatro casos contra os excertos e páginas dos PDFs; mudanças de expectativa precisam de justificativa documental, nunca de adaptação à saída do modelo.
- Para testes offline, usar documentos/regras fictícios, modelos substitutos e diretórios temporários.
- Para avaliação real, dispor de credencial NVIDIA, corpus/casos locais, índice válido e limites explícitos de chamadas.

## 5. Escopo e sequência de implementação

### Etapa A — Tornar a avaliação auditável

1. Definir o formato 2 de relatórios/revisões, identificação de execução, configuração imutável e vínculo por resultado.
2. Capturar a configuração antes das chamadas; verificar sua estabilidade ao final.
3. Implementar consolidação estrita, vínculo das revisões e proteção contra reaplicação de uma repetição.
4. Registrar as decisões inicial e revisada da geração exclusivamente na avaliação, para explicar abstenções e seleções de fontes.
5. Provar contratos e falhas com testes offline antes de produzir novos resultados reais.

### Etapa B — Diagnosticar e corrigir os quatro casos

1. Executar os quatro casos com a instrumentação da etapa A e o comportamento de geração ainda não alterado; registrar pergunta, contexto recuperado, fontes, decisões e revisão humana.
2. Localizar a falha: evidência ausente/incompleta, interpretação, decisão de estado, seleção de fontes, interpretação da saída ou revisão de abstenção.
3. Aplicar mudanças pequenas em prompt, geração ou validação apenas quando sustentadas pelo diagnóstico. Preservar o contrato público e o limite de duas invocações de geração.
4. Executar o mesmo subconjunto como experimento candidato separado. Comparar os casos, sem consolidá-lo à baseline de outro código/prompt.

### Etapa C — Verificar regressões e registrar o resultado

1. Congelar o candidato e executar os 21 casos em um relatório novo, com revisão humana vinculada às saídas.
2. Repetir somente falhas técnicas quando configuração e código permanecerem idênticos, preservando a execução original e o histórico de substituição.
3. Atualizar README, avaliação e relatório de progresso com resultados, contagens e limitações, distinguindo resolução comprovada de problema ainda aberto.

## 6. Fora do escopo

- Novo provedor/modelo, novas dependências, agente autônomo, juiz LLM ou verificador semântico adicional.
- Busca híbrida, reranking, OCR, troca de embeddings, chunking ou formato do índice; alterar recuperação nesta SPEC somente se o diagnóstico demonstrar uma falha responsável por um dos quatro casos e registrar a justificativa.
- Reforma geral do contrato para citações por afirmação, interface web, autenticação ou telemetria externa.
- Regras acadêmicas codificadas, resposta fixa por ID/pergunta, correção baseada em percentuais ou prazos conhecidos pelo desenvolvedor.
- Reclassificar expectativas para fazer métricas passarem, selecionar silenciosamente a melhor entre várias respostas ou aumentar tentativas até obter sucesso.
- Certificar vigência ou resistência universal a injeção de instruções.
- Reconstruir proveniência desconhecida de relatórios antigos ou sobrescrever seus arquivos.

## 7. Requisitos funcionais

- **RF-01:** Todo novo resultado, inclusive erro técnico e contexto ausente, deve apontar para uma execução registrada com configuração e hashes verificáveis.
- **RF-02:** Congelar metadados de execução antes das chamadas; uma mudança detectada durante a execução impede que o relatório seja publicado como concluído e consistente.
- **RF-03:** Consolidar repetições somente com igualdade da configuração de experimento definida na seção 9. Divergência produz erro sem modificar os arquivos de entrada.
- **RF-04:** Manter a origem dos casos não substituídos e registrar, para cada substituição, resultado anterior, resultado novo e execução de origem. Nunca atualizar a origem antiga para o código mais recente.
- **RF-05:** Reaplicar a mesma repetição deve ser rejeitado ou tornar-se uma operação sem efeito; não duplicar uso do provedor, histórico ou métricas.
- **RF-06:** Vincular revisão humana ao resultado exato, ao ID do caso e ao conteúdo revisado da expectativa. Revisão obsoleta ou de outro resultado deve ser rejeitada.
- **RF-07:** Preservar revisões dos resultados inalterados e invalidar apenas as dos substituídos. Identificação e data do revisor acompanham cada revisão preservada.
- **RF-08:** Identificar quais fontes foram julgadas sustentadas na revisão humana; a contagem deve corresponder aos IDs válidos desse resultado, não ser apenas um número desvinculado das fontes.
- **RF-09:** Registrar na avaliação a decisão de cada invocação de geração, finalidade da tentativa e erros de interpretação/validação, sem raciocínio interno do modelo, credenciais ou logs globais.
- **RF-10:** Atender ao comportamento esperado dos quatro casos da seção 3.2, sem depender de IDs ou texto da pergunta para escolher a resposta da aplicação.
- **RF-11:** Preservar resposta parcial, conflito, abstenção fora do corpus e distinção de falhas técnicas; fontes continuam montadas a partir dos trechos reais.
- **RF-12:** Não apresentar um conjunto focal de quatro casos como validação completa do MVP; reportar separadamente subconjunto e regressão integral.

## 8. Requisitos técnicos

- **RT-01:** Usar Python, biblioteca padrão e dependências existentes; manter testes comuns sem rede/chaves reais.
- **RT-02:** Concentrar proveniência, consolidação, métricas e revisão em `evaluation.py`; instrumentação de geração deve ser opcional e não alterar o retorno público de `answer_question()`.
- **RT-03:** Manter `AnswerResult` com `answer`, `sources` e `status`. Alterações internas em `ModelDecision` exigem evidência de necessidade, atualização do schema e testes; não criar contratos alternativos simultâneos.
- **RT-04:** Manter máximo de duas invocações da geração por consulta. Uma falha técnica não pode virar abstenção, e uma resposta inválida não pode ser exibida.
- **RT-05:** Usar JSON canônico e SHA-256 para identidade de configuração/resultado, definindo explicitamente campos incluídos e excluídos; não depender da ordem de dicionários ou de espaços na serialização.
- **RT-06:** Guardar conteúdo real somente em `evaluation/*.local.json`, ignorado pelo Git. Saída padrão da CLI continua sem trace detalhado.
- **RT-07:** Preservar escrita atômica. Disponibilizar destino distinto nas operações de revisão/consolidação para manter arquivos-fonte intactos, reutilizando `output_file` do núcleo de revisão e acrescentando equivalente onde necessário.
- **RT-08:** Não tratar fingerprint/IDs como autenticação criptográfica. Registrar nome do modelo solicitado e limites de reprodução quando o endpoint não expuser revisão imutável do modelo.
- **RT-09:** Não modificar algoritmo/definição de métricas sem justificativa. A correspondência textual existente não substitui revisão de suporte, condições e relevância das fontes.

## 9. Modelo e contratos

### 9.1. Relatório de formato 2

Estrutura simples em JSON, sem nova hierarquia de serviços:

| Campo/registro | Contrato |
| --- | --- |
| `format_version` | `2` para novos relatórios auditáveis |
| `runs` | Cadastro das execuções usadas: `run_id`, horários UTC, configuração congelada, fingerprint de experimento e uso do provedor |
| Resultado por caso | Campos atuais, `run_id`, hash do caso/expectativa e `result_sha256` |
| `manual_review` por caso | Resultado/expectativa a que se refere, revisor, data, suporte semântico, requisitos, IDs de fontes sustentadas e notas |
| Histórico de consolidação | Hash do relatório de origem, IDs das execuções e identidade dos resultados substituídos/novos |
| Métricas | Recalculadas sobre resultados selecionados, com totais de concluídos, erros e revisões; não reescrever execuções originais |

`run_id` identifica uma ocorrência de execução; não serve para comparar configurações. Casos de uma repetição possuem novo `run_id`, mesmo em experimento compatível. Cada referência deve resolver no cadastro de execuções.

### 9.2. Compatibilidade de experimento

O fingerprint de experimento inclui:

- Fingerprint de todos os módulos da aplicação relevantes ao fluxo, schema de saída e instruções de geração/revisão; o fingerprint atual de `src/academic_assistant/*.py` pode ser reutilizado.
- Hashes de `pyproject.toml`/`uv.lock`, runtime Python e versões instaladas das dependências utilizadas.
- Provedores/modelos, dimensão de embeddings, parâmetros de geração e configuração de saída estruturada.
- `retrieval_k`, janela de páginas, limite de trechos, coleção e parâmetros de chunking.
- Identidade e hash do manifesto do índice, seleção/hashes do corpus e hashes dos arquivos de casos completos.

Horário, caminho do relatório de saída, `run_id`, orçamento de chamadas, subconjunto escolhido, commit e estado dirty ficam como metadados da execução, fora da igualdade de experimento. Assim, um rerun focal pode ter orçamento/caminho próprios sem aparentar mudança de comportamento. Caminhos de entrada são registrados; sua identidade comparável depende do conteúdo, não somente do nome.

Os metadados devem identificar também falhas de inicialização quando for possível produzir um registro consistente. Não inventar índice ou hashes que não tenham sido obtidos.

Se código, prompt ou parâmetros mudarem, produzir outro experimento. Comparação antes/depois é permitida, com diferenças explícitas; consolidação homogênea não é. A regressão final precisa cobrir os 21 casos do candidato congelado, e não completar quatro respostas novas com 17 respostas históricas.

### 9.3. Identidade do resultado e da revisão

`result_sha256` cobre entrada/contexto, identidade do caso/expectativa, origem da execução, evidências recuperadas, resposta/fontes/estado, erro técnico e decisões de geração registradas. Exclui revisão humana, métricas agregadas e timestamps de consolidação para permitir anexar uma revisão sem mudar o resultado revisado.

A revisão do formato 2 informa ID do caso, `run_id`, `result_sha256`, hash do caso/expectativa, revisor/data, os campos semânticos existentes e `supported_source_ids`. IDs repetidos ou inexistentes e uma contagem diferente da quantidade de IDs são inválidos. A identificação de fontes sustentadas é humana; não se deve inferi-la automaticamente de similaridade.

### 9.4. Decisões de geração para diagnóstico

Registrar finalidade (`initial`, `correction` ou `abstention_review`), decisão estruturada recebida antes de normalizações, resultado da validação e decisão efetivamente selecionada. Em saída malformada, registrar o erro e somente o conteúdo textual de saída necessário ao diagnóstico local, sem objetos de SDK ou headers.

A instrumentação não solicita cadeia de pensamento, não acrescenta chamadas e não deixa traces em consultas normais. Pode usar um callback opcional ou um coletor restrito ao executor, mantendo a lógica única de geração.

### 9.5. Compatibilidade histórica e comandos

Relatórios/revisões de formato 1 permanecem preservados como evidências históricas. Não migrar automaticamente atribuindo `run_id`, código ou identidade de resultado desconhecidos. Operações que exigem proveniência do formato 2 rejeitam legados com orientação para nova execução em outro arquivo.

Reutilizar `evaluate`, `evaluate-review`, `evaluate-merge` e `--only-case`. Está prevista a opção `--output` para revisão/consolidação, ainda não implementada, com destino separado dos relatórios-fonte. Caminhos históricos nunca devem ser usados como destino nesta entrega. Comandos novos só aparecerão como funcionais no README após implementação/verificação.

## 10. Tratamento de erros

- Relatório, caso, execução, referência ou hash inválido: `EvaluationError`, código 1, sem alteração das entradas.
- Experimentos incompatíveis: erro identifica os campos divergentes, sem imprimir documentos ou segredos.
- Revisão obsoleta: rejeitar antes de anexar decisões ou recalcular métricas.
- Repetição ainda com erro técnico: manter o erro visível e não substituir silenciosamente um resultado válido.
- Orçamento excedido: interromper antes da próxima chamada contada; não declarar execução completa. Esta SPEC não exige checkpoint incremental.
- Configuração/arquivos relevantes mudaram durante a execução: registrar inconsistência como falha, não publicar resultado como experimento estável.
- Provider/saída inválida: conservar os caminhos atuais de erro, sem recorrer à mensagem de insuficiência.
- Legado sem origem suficiente: explicar limitação; não preencher lacunas com suposições.

## 11. Arquivos afetados

- `specs/013-proveniencia-e-regressoes-semanticas.md` — esta especificação e futuras evidências.
- `src/academic_assistant/evaluation.py` — formato, snapshots, hashes, consolidação e revisão.
- `src/academic_assistant/generation.py`, `prompts.py`, `validation.py` — diagnóstico opcional e correções justificadas dos quatro casos.
- `src/academic_assistant/cli.py` — destinos de saída e resumos, se necessários ao contrato.
- `tests/test_evaluation.py`, `test_generation.py`, `test_query.py`, `test_cli_ask.py`, `test_evaluation_data.py` — provas pertinentes; criar arquivo de teste focado se melhorar organização.
- `evaluation/synthetic-cases.json` — preservar os cinco cenários da regressão real; alterar expectativas apenas diante de erro comprovado no caso, com justificativa e novo experimento.
- `evaluation/README.md`, `README.md`, `reports/RELATORIO-PROGRESSO.md` — contratos, comandos e resultados verificados.
- `evaluation/cases.local.json` — somente correções justificadas de expectativa; relatórios/revisões/diagnósticos novos em `evaluation/*.local.json`.

`retrieval.py` e seus testes só entram mediante diagnóstico documentado de falha responsável. Manter PDFs, índice e dependências existentes; alterações fora da lista precisam de justificativa dentro do escopo.

## 12. Estratégia de testes e avaliação

### 12.1. Provas offline da proveniência

- Consolidar duas execuções de mesmo experimento, preservando origem/revisão de caso não substituído e invalidando revisão do substituído.
- Recusar diferenças isoladas de código, prompt, dimensão, parâmetro de geração/recuperação, índice, corpus, casos ou dependências; permitir diferenças apenas operacionais previstas.
- Reaplicar rerun sem duplicar contagens; rejeitar ID de caso desconhecido, referência de execução ausente ou hash adulterado.
- Rejeitar revisão antiga de resposta diferente com o mesmo ID; aceitar revisão do resultado exato e validar os IDs sustentados.
- Recalcular métricas sem modificar resultados; comprovar preservação dos relatórios-fonte e escrita atômica diante de falha.
- Confirmar snapshot anterior às chamadas, detecção de mudança e recusa de legado em operações do formato 2.

### 12.2. Provas offline da geração

Criar fixtures nos testes com cenários fictícios equivalentes a conjunção de requisitos, pergunta que tenta dispensar um deles, condição que não autoriza exclusividade e fontes relacionadas sem sustentar a resposta. Preservar os cinco casos da suíte real sintética para manter a regressão de 21 casos. Verificar construção do prompt, contrato, limite de tentativas, trace opcional e preservação dos caminhos de erro.

Modelos simulados não provam resolução semântica. Não criar teste cuja resposta esteja codificada no substituto e apresentá-lo como evidência de que o LLM real melhorou.

### 12.3. Avaliação real controlada

| Etapa | Casos | Limite de invocações contadas |
| --- | --- | ---: |
| Diagnóstico com geração anterior | Os quatro casos-alvo | 12 |
| Avaliação do candidato | Os mesmos quatro | 12 |
| Regressão final do candidato congelado | 16 reais e cinco sintéticos | 60 |

Planejamento total: **até 84 invocações contadas**, incluindo repetições técnicas dentro do saldo de cada etapa. Para os quatro casos, 12 permite quatro embeddings e até oito gerações. O limite de 60 comporta a regressão com a política atual de até duas gerações por caso e margem para falha técnica. Não aumentar automaticamente esses limites ou iniciar novos experimentos ao esgotá-los.

O executor conta invocações da aplicação, não todas as requisições do SDK/catálogo, e não informa custo monetário. Nenhuma chamada externa faz parte da criação desta SPEC. Se orçamento, chave ou serviço impedirem a validação real, registrar pendência e manter a entrega semântica aberta.

Em cada etapa, usar arquivos distintos, vincular revisões aos resultados exatos e registrar também reprovações. Rever os quatro casos com os requisitos locais completos, sem exigir redação idêntica ou exatamente a mesma quantidade de fontes quando houver alternativas igualmente pertinentes.

Ao modificar o candidato após regressão, seus resultados anteriores deixam de representar validação completa da nova versão. Produzir experimento novo; não consolidar snapshots distintos para declarar sucesso.

### 12.4. Verificações finais da implementação

Executar suíte offline com `uv run --extra dev --locked --offline pytest -q`, `uv lock --check --offline`, compilação Python, validação dos JSONs, ajuda/argumentos da CLI, links/Markdown e `git diff --check`. Não antecipar contagem final de testes ou percentuais de aprovação.

## 13. Critérios de aceite

- **CA-01:** Cada resultado novo possui origem resolvível; metadados globais não atribuem execução nova a resultados antigos.
- **CA-02:** Diferenças de experimento são rejeitadas na consolidação e diferenças operacionais aceitas conforme contrato; reaplicação não duplica histórico/uso.
- **CA-03:** Revisão antiga de outra saída é rejeitada; revisões de resultados inalterados são preservadas, e fontes sustentadas são identificadas.
- **CA-04:** Formato 1 permanece intacto e não recebe proveniência inferida; novas avaliações usam formato 2.
- **CA-05:** Diagnóstico identifica a camada responsável de cada um dos quatro casos com dados observados; traces ficam locais e não acrescentam chamadas.
- **CA-06:** `IFMA-001` preserva requisitos cumulativos; `IFMA-002` responde à hipótese sem abstenção indevida; `IFMA-013` limita a conclusão sem universalidade/exclusividade inventada; `IFMA-011` cobre evidências necessárias sem fontes meramente relacionadas.
- **CA-07:** Os quatro casos do candidato têm estado esperado, suporte semântico e requisitos aprovados; todas as fontes exibidas são consideradas sustentadas na revisão humana vinculada.
- **CA-08:** Regressão dos 21 casos do candidato congelado é concluída e revisada, sem erros técnicos restantes e sem nova falha de suporte, requisitos, estados ou citações nos casos anteriormente aprovados. Abstenção, contexto, conflito e instrução maliciosa permanecem aprovados nos cenários existentes.
- **CA-09:** Testes e checks pertinentes passam; limites de chamadas, resultados históricos e contrato público permanecem preservados.
- **CA-10:** Documentação registra comparação por caso, proveniência, denominadores/métricas, chamadas e limitações; nenhum percentual é apresentado como garantia geral.

## 14. Definition of Done

- [x] Requisitos funcionais e técnicos de proveniência atendidos.
- [x] Causas e intervenções dos quatro casos documentadas.
- [x] Testes offline e verificações Python/uv aprovados.
- [x] Relatórios-fonte e dados privados preservados.
- [x] Diagnóstico e candidato focal executados/revisados dentro dos limites.
- [x] Regressão integral do candidato congelado executada e revisada.
- [x] Critérios semânticos dos quatro casos e ausência de regressões comprovados.
- [x] README, contrato de avaliação e progresso atualizados com evidências.
- [x] Nenhuma funcionalidade fora do escopo implementada.

O item Maven do template foi substituído por verificações compatíveis com o projeto Python. Concluir a infraestrutura de avaliação sem executar/aprovar a validação real não encerra a entrega semântica: registrar as etapas concluídas e manter a SPEC em validação ou bloqueada pela condição real, conforme o estado do trabalho.

## 15. Critério de parada

Concluir quando proveniência/revisões forem verificáveis, os quatro problemas passarem na avaliação real e a regressão integral não revelar novas falhas. Registrar o resultado sem declarar confiabilidade fora dos cenários avaliados.

Se os limites de chamadas forem atingidos ou a qualidade permanecer abaixo dos critérios, encerrar aquele experimento, preservar os resultados e registrar diagnóstico/pendências. Não marcar a SPEC como concluída por esgotamento de orçamento, somente por testes simulados ou por melhora da média agregada. Novos modelos, reranking, contratos por afirmação e estudos estatísticos ficam para especificações posteriores.

## 16. Execução de 14 de outubro de 2026

### Infraestrutura e provas

Formato 2 implementado em `evaluation.py`: snapshot anterior à leitura/execução dos casos, configuração verificada ao término, identidade canônica de experimento/resultado, cadastro de execuções por resultado, revisão vinculada à saída/expectativa e IDs sustentados, consolidação estrita com histórico completo e proteção de reaplicação. Revisões dos resultados inalterados mantêm identidade/data do revisor; somente as substituídas são invalidadas. Inicialização malsucedida registra metadados conhecidos, sem manifesto inferido. `evaluate-review` e `evaluate-merge` aceitam `--output`. Formato 1 é rejeitado com orientação, sem migração retrospectiva.

Trace opcional no executor registra decisões antes/depois da normalização, finalidade e validação/seleção, conservando contexto mesmo em erros. Não altera `AnswerResult`/`answer_question()`, não solicita raciocínio interno e não acrescenta chamadas. A segunda saída inválida agora é erro técnico, em vez de manter silenciosamente a primeira abstenção. Não foram alterados modelo, recuperação, embeddings, chunking, dependências, PDFs, índice ou expectativas.

126 testes offline aprovados; lockfile conferido, compilação Python, JSONs, ajuda/argumentos de CLI, links/Markdown alterados e whitespace verificados. Fixtures usam regras fictícias. Os testes provam os contratos de software, não suporte semântico do modelo.

### Diagnóstico observado e intervenção

Expectativas dos quatro casos conferidas contra texto dos PDFs: todos os cinco excertos correspondem às páginas físicas indicadas, normalizando espaços. Não houve alteração de expectativa.

| Caso | Diagnóstico local | Mudança genérica | Observação no candidato/regressão |
| --- | --- | --- | --- |
| IFMA-001 | Regra completa recuperada; decisão inicial omitiu requisito cumulativo | Composição exige demais requisitos do mesmo dispositivo mesmo em pergunta sobre um valor; exemplo fictício | Requisito cumulativo incluído com fonte pertinente |
| IFMA-002 | Evidência recuperada; decisão inicial abstém; revisão negativa retorna partial sem parte ausente e é rejeitada; abstenção inicial era selecionada | Instrução/exemplo de hipótese negativa sustentada; partial exige parte ausente; segunda saída inválida é erro técnico | Resposta negativa supported, com conjunção documentada |
| IFMA-013 | Decisão inicial partial afirma exclusividade e nega universalidade sem evidência de exceção | Composição parte do grupo documentado; não nega regra universal nem exclui outros grupos sem suporte; exemplo fictício | Grupo documentado e lacuna explicitados, sem exclusividade |
| IFMA-011 | Procedimento/critérios recuperados e explicados; fonte adicional de recurso não sustenta nenhuma afirmação exibida | Cada fonte precisa sustentar texto efetivamente exibido; exemplo pedido/critério/recurso | Duas fontes necessárias, de páginas separadas, sem fonte de recurso não usado |

A instrumentação identifica a camada observada (interpretação/composição/estado/seleção de fontes), não revela causa interna do modelo. O diagnóstico não justificou alterar recuperação. A conferência/inspeção feita pelo agente não equivale à revisão humana requerida.

### Execuções e limites

| Etapa | Artefato local novo | Casos | Embeddings/geração | Total/limite | Estado correto | Evidências recuperadas/citadas |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Diagnóstico | spec013-diagnostic.local.json | 4 | 4/5 | 9/12 | 3/4 | 5/5 e 4/5 |
| Candidato | spec013-candidate-v1.local.json | 4 | 4/4 | 8/12 | 4/4 | 5/5 e 5/5 |
| Regressão | spec013-regression-v1.local.json | 21 | 15/20 | 35/60 | 21/21 | 20/20 e 20/20 |

Todas as execuções completas terminaram sem erro técnico. As tentativas de inicialização no ambiente restrito falharam sem chamadas contadas; registros incompletos em `spec013-candidate.local.json` e `spec013-regression.local.json` foram preservados. O diagnóstico inicial também falhou antes de haver instrumentação de falha de inicialização, sem relatório publicado. Execuções completas usaram acesso remoto aprovado. Total contado: 52/84; não houve rerun semântico nem aumento de limite, e custo monetário continua desconhecido.

Fingerprint do diagnóstico: `2a4220048038e07e6933ba792255b6305d21758ccb655150faed8b146862babc`. Candidato e regressão: `2d092cd57900b3797b7ac7023a0e054d435f38df1270be9457bf064b4d2f27f9`, conferido com o código atual. Código/parâmetros ficaram congelados entre candidato e regressão. Não se consolidaram experimentos diferentes nem resultados da SPEC-012.

Regressão: recuperação/cobertura de citações 20/20; precisão por rótulos 21/22 (95,45%); estados 21/21; abstenção 2/2 e contexto ausente 1/1. Cinco sintéticos preservados, incluindo conflito e instrução maliciosa. A fonte extra por rótulo em IFMA-006 acompanha afirmação adicional que precisa de revisão humana. Nenhuma dessas razões comprova suporte semântico ou preservação de requisitos.

### Pendências que impedem conclusão

Revisões humanas ainda não aplicadas: zero no diagnóstico, candidato e regressão; suporte/requisitos/precisão semântica sem métricas. Foram preparados três `spec013-*-reviews-draft.local.json` com identidade do resultado, pergunta, expectativa, evidências, resposta e trace. Revisor/data e decisões estão pendentes; o validador não os aceita como revisão concluída. Revisar também reprovações do diagnóstico.

IFMA-003 tem redação potencialmente ambígua sobre cálculo da média final e deve ser examinado contra a evidência, sem aprovação automática pela correspondência textual. A SPEC mantém CA-07/CA-08 e os itens de revisão/qualidade da Definition of Done abertos. Não declarar os quatro problemas definitivamente resolvidos ou ausência de regressões até registrar revisão humana vinculada aos resultados. Se ela identificar falha, preservar este experimento e registrar a pendência; não misturar nova implementação com seus resultados.

## 17. Correções decorrentes da revisão humana

Manoel concluiu a revisão dos 21 casos da regressão anterior na conversa. Registro em `evaluation/spec013-regression-reviews.local.json`, aplicado a `spec013-regression-reviewed.local.json`, com o original preservado: 19 aprovados e duas solicitações de mudança de produto. IFMA-003 foi aprovado expressamente após a apresentação da possível ambiguidade. Diagnóstico e candidato focal anteriores continuam sem revisão humana aplicada.

As duas novas decisões substituem as expectativas anteriores somente nos próximos experimentos:

1. **IFMA-016:** a instituição é implicitamente IFMA; instituição omitida/nula/vazia assume esse valor. Outra instituição explícita é recusada. Nível do curso continua obrigatório antes dos provedores; campus/modalidade mantêm seus filtros e o regime deve ser explicado ou solicitado quando a regra depender dele. Não se presume graduação a partir da instituição.
2. **SYN-004:** priorizar a versão mais recente quando existir cadastro revisado de data e substituição integral entre versões do mesmo escopo. O inventário recebe `publication_date` (data documental ISO) e `precedence_group` (versões integralmente substitutas). Não inferir prioridade por nome, upload ou similaridade; não equiparar guia complementar a versão substituta de norma. A escolha é explicitada na resposta e não comprova revogação legal. Sem cadastro suficiente ou entre versões empatadas, preservar conflito com fontes.

A seleção da versão é determinística e anterior à busca vetorial; portanto uma versão antiga não ocupa os resultados no lugar da nova. Grupos que misturam escopos de campus/modalidade são rejeitados. Data/grupo seguem do inventário para as evidências, sem reindexação. Na geração direta, versões anteriores ficam fora do prompt e sua citação é rejeitada pelo validador. `AnswerResult`, fontes reais, limite de duas invocações e caminhos de erro são preservados. Nenhuma data foi presumida para os PDFs locais.

A expectativa local de IFMA-016 agora exige pedir apenas o nível. SYN-004 foi alterado por decisão explícita de produto, com datas/grupo fictícios identificados na curadoria do cenário; sua entrada contém as duas versões e a evidência esperada apenas a recente. Isso exige novo fingerprint, sem reescrever as expectativas nem as revisões dos relatórios antigos. A revisão anterior de suporte/requisitos em 19/21 e fontes em 21/22 inclui essas mudanças de preferência; não deve ser apresentada como medida do candidato corrigido.

### Verificação das correções

148 testes offline aprovados, cobrindo instituição implícita/nula, filtros de escopo, metadados do inventário sem reindexação, exclusão da versão antiga antes do top-k, preferência por data, ausência/empate de datas, grupos diferentes, nomes enganosos, datas inválidas, conflito sem precedência e rejeição/correção limitada de citação antiga. Modelos substitutos verificam contratos, não qualidade semântica do endpoint.

Nova avaliação real, `evaluation/spec013-corrections-focal.local.json`, com limite de 12 invocações: IFMA-016 e os cinco sintéticos, seis casos concluídos, zero erros e quatro invocações de geração. Todos os checks automáticos passaram: estados 6/6, evidências esperadas recuperadas/citadas 4/4. IFMA-016 retornou “Informe nível do curso para selecionar os documentos aplicáveis.”; SYN-004 respondeu com a fonte recente e justificativa por data. Nenhum embedding de consulta foi necessário nessa seleção: um caso é bloqueado por contexto e os demais usam contexto sintético.

Fingerprint novo: `6cd43786b306c0ea1688817ec58e6d5a506f80e2a59db0c73a95ab41f1a320e3`. Total contado acumulado: 56/84. Sem transferência automática de aprovações antigas e sem consolidação entre experimentos. O subconjunto não é uma nova validação integral dos 21 casos; regressão completa deste código e revisões restantes permanecem pendentes. CA-08 e a Definition of Done continuam abertos. Lockfile, compilação, JSONs, CLI, links novos/estrutura Markdown e whitespace também foram conferidos.

Manoel aprovou explicitamente as duas novas saídas corrigidas (IFMA-016 e SYN-004) na conversa. A aprovação foi registrada em `evaluation/spec013-corrections-reviews.local.json`, com revisor, data UTC, `run_id`, hashes do resultado/caso e os IDs de fontes sustentadas. Aplicação validada em `spec013-corrections-reviewed.local.json`, sem modificar o relatório-fonte ou a identidade dos resultados: dois casos aprovados entre seis, quatro ainda sem revisão nova. Nenhuma chamada ao provedor foi necessária para registrar essas decisões. A aprovação focal não encerra a SPEC.

## 18. Nova regressão integral solicitada por Manoel

Após o pedido “vamos fazer isso”, foi executada nova etapa integral, com limite anunciado de 60 chamadas, preservando código, prompt, dependências, corpus, índice e casos do experimento focal corrigido. Fingerprint `6cd43786b306c0ea1688817ec58e6d5a506f80e2a59db0c73a95ab41f1a320e3`, conferido com a configuração atual. Os 148 testes offline passaram novamente, assim como lockfile e compilação.

| Execução | Conclusões/erros | Chamadas | Origem |
| --- | --- | ---: | --- |
| Integral inicial | 19/2 | 35 — 15 embeddings + 20 gerações | spec013-corrections-regression.local.json |
| Repetição técnica de IFMA-014 e SYN-004 | 2/0 | 3 — um embedding + duas gerações | spec013-corrections-regression-retry.local.json |
| Consolidado de mesmo experimento | 21/0 | 38 — 16 embeddings + 22 gerações | spec013-corrections-regression-final.local.json |

As duas falhas foram de geração no provedor, sem decisão estruturada recebida. Somente erros técnicos foram repetidos, com teto individual de cinco chamadas e sem alteração de configuração. A consolidação usou destino novo e verificou preservação dos arquivos-fonte, igualdade de experimento, referências de execução e hashes dos resultados. O histórico registra cada substituição. Não foram substituídas respostas válidas para escolher a melhor redação.

O cadastro conserva os limites individuais 60 e cinco, cuja soma operacional em `max_calls` é 65. O uso efetivo de 38 foi verificado contra o limite de etapa 60. Essa nova etapa foi solicitada após as correções: total acumulado de 94 chamadas (56 anteriores + 38 novas), sem afirmar que cabe no planejamento histórico de 84.

Checks automáticos do consolidado: estados 21/21, evidências esperadas recuperadas/citadas 19/19, precisão por rótulos 20/21 (95,24%), abstenção 2/2, contexto ausente 1/1 e zero erros técnicos restantes. Não há métricas humanas desse consolidado: zero revisões aplicadas. A fonte adicional fora do rótulo esperado e a redação das respostas ainda exigem revisão semântica.

Comparação exata em `evaluation/spec013-corrections-regression-final-comparison.local.json`: 14 casos com caso/expectativa, resposta/mensagem/estado e fontes iguais às referências humanas anteriores; sete com diferenças (IFMA-001, IFMA-002, IFMA-003, IFMA-006, IFMA-008, IFMA-011 e IFMA-013). O arquivo registra as duas identidades para facilitar nova confirmação, sem transferir aprovação. Não se presume que mudanças de redação sejam semanticamente irrelevantes; IFMA-001 e IFMA-003 merecem atenção à interpretação dos requisitos e do cálculo.

A regressão técnica foi concluída e a revisão humana foi registrada no encerramento da seção seguinte. Relatórios anteriores, revisões e PDFs continuam preservados, e nenhuma reindexação foi executada.

## 20. Encerramento

Manoel concluiu a revisão humana dos quatro casos do diagnóstico e dos quatro casos do candidato focal. No diagnóstico, IFMA-001 e IFMA-011 foram aprovados; IFMA-002 foi reprovado por abstenção indevida e IFMA-013 por extrapolação da evidência. No candidato focal, os quatro casos foram aprovados. As decisões estão vinculadas aos `run_id`, hashes de resultado e hashes de caso em `evaluation/spec013-diagnostic-reviews.local.json` e `evaluation/spec013-candidate-reviews.local.json`, com relatórios revisados separados dos originais.

A nova regressão integral corrigida também foi revisada integralmente: 21/21 casos, suporte semântico de 100%, requisitos preservados em 100%, citações sustentadas em 100% e zero erros técnicos restantes. Os checks automatizados e a revisão humana confirmaram a ausência de regressão nos casos avaliados. A infraestrutura, os relatórios-fonte, os históricos de repetição e os documentos privados foram preservados.

Com essas evidências, CA-07, CA-08 e os itens correspondentes da Definition of Done estão concluídos. A SPEC-013 está finalizada; os percentuais registrados descrevem somente estes conjuntos avaliados e não constituem garantia geral para perguntas fora do corpus.
