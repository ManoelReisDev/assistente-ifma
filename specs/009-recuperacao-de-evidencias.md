# SPEC-009 — Recuperação de evidências

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-008 concluída e índice ativo compatível.
- **Entrega:** Perguntas podem recuperar trechos rastreáveis do índice ativo, restritos ao contexto aplicável e ampliados com contexto local de páginas vizinhas, sem chamar um LLM.

## 2. Objetivo

Recuperar evidências relevantes sem confundir semelhança textual com aplicabilidade normativa. Cada consulta deve produzir identificadores de fonte vinculados a trechos reais, preservar limitações do corpus e permitir inspeção independente da futura geração de respostas.

## 3. Contexto

A SPEC-008 publicou um índice Chroma com 169 trechos de `doc3.pdf` e `doc4.pdf`. O primeiro documento é específico do Campus São Luís–Monte Castelo; o segundo é uma norma geral de graduação cuja vigência atual não foi comprovada. A busca precisa aplicar essas restrições antes da similaridade e não pode interpretar a distância vetorial como probabilidade de correção.

## 4. Pré-condições

- Índice ativo, manifesto e fontes atuais válidos.
- Mesmo modelo de embeddings usado na indexação e na consulta.
- Inventário do corpus com instituição e nível de curso dos documentos selecionados.
- Instituição e nível do curso informados para a consulta.

## 5. Escopo

- Configurar quantidade de resultados, janela de páginas e limite total de contexto.
- Resolver documentos aplicáveis por instituição, nível, campus e modalidade conhecidos.
- Buscar por similaridade somente nos documentos aplicáveis, sem limiar arbitrário.
- Acrescentar trechos da mesma página e das páginas vizinhas dentro de um limite.
- Deduplicar trechos e atribuir `source_id` por consulta.
- Preservar distância somente para resultados primários e apresentá-la como diagnóstico, não como confiança.
- Retornar limitações de aplicabilidade registradas no inventário.
- Expor função de diagnóstico que carrega o índice e recupera evidências sem LLM.

## 6. Fora do escopo

Geração de respostas, prompts, validação de citações do modelo, mensagem final de abstenção, comando `ask`, calibração de limiar, reranking, busca híbrida, atualização do índice e comprovação de vigência. Esses itens pertencem às SPEC-010 a SPEC-012.

## 7. Requisitos funcionais

- **RF-01:** Exigir instituição e nível do curso antes da busca vetorial.
- **RF-02:** Excluir fonte específica de campus quando o campus informado não corresponder ou estiver ausente; fontes gerais compatíveis permanecem disponíveis.
- **RF-03:** Retornar até `retrieval_k` resultados primários, sem limiar de distância.
- **RF-04:** Acrescentar contexto da mesma página e de páginas adjacentes sem cruzar documento e respeitando `retrieval_max_chunks`.
- **RF-05:** Cada evidência deve conter `source_id`, origem completa, excerto literal, indicação de resultado primário e distância diagnóstica quando aplicável.
- **RF-06:** IDs de fonte devem ser únicos e apontar somente para trechos efetivamente recuperados do índice.
- **RF-07:** Contexto ausente ou não coberto deve ser distinguido de falha técnica e ocorrer antes da chamada de embeddings.
- **RF-08:** Limitações registradas para os documentos aplicáveis devem acompanhar o resultado.

## 8. Requisitos técnicos

- **RT-01:** Usar `similarity_search_with_score` do Chroma com filtro de `document_id` e o mesmo objeto de embeddings da carga do índice.
- **RT-02:** Tratar a pontuação retornada como distância, em que valores menores indicam maior proximidade; não convertê-la em probabilidade.
- **RT-03:** Manter testes comuns offline com embeddings determinísticos e documentos fictícios.
- **RT-04:** Não enviar evidências ao provedor nesta etapa; apenas a pergunta é enviada para gerar seu embedding na execução real.
- **RT-05:** Não introduzir dependências nem alterar o formato do índice da SPEC-008.

## 9. Modelo e contratos

`RetrievalContext` recebe `institution`, `course_level`, `campus` e `modality`. Os dois primeiros são obrigatórios. Campos específicos dos documentos restringem a seleção; documento sem campus é tratado como institucional, enquanto limitações desconhecidas continuam explícitas no retorno.

`RetrievedEvidence` contém `source_id`, `document_id`, `document_name`, `document_hash`, `page_number`, `chunk_id`, `excerpt`, `is_primary` e `distance`. Contexto vizinho tem `distance=None` porque não foi classificado pela busca vetorial.

`RetrievalResult` contém a pergunta normalizada, o contexto recebido, evidências imutáveis, limitações de aplicabilidade e `source_map`, derivado dos próprios resultados.

Configuração padrão:

| Campo | Valor |
| --- | --- |
| `retrieval_k` | 4 |
| `retrieval_page_window` | 1 |
| `retrieval_max_chunks` | 12 |

## 10. Tratamento de erros

- Pergunta vazia produz `ValueError` antes da busca.
- Instituição ou nível ausente produz `ContextRequiredError`.
- Contexto sem documento aplicável produz `ContextNotCoveredError`.
- Inventário incompleto, retorno sem metadados, filtro violado ou falha do Chroma produz `RetrievalError`.
- Índice ausente, incompatível ou desatualizado mantém os erros próprios da indexação.
- Busca válida sem resultados retorna evidências vazias; a decisão de abstenção será da SPEC-010.

## 11. Arquivos afetados

- `specs/009-recuperacao-de-evidencias.md`
- `src/academic_assistant/retrieval.py`
- `src/academic_assistant/config.py`
- `src/academic_assistant/indexing.py`
- `tests/test_retrieval.py`
- `tests/test_bootstrap.py`
- `evaluation/corpus.local.json`
- `README.md`

## 12. Estratégia de testes

- Construir índice temporário Chroma com regulamentos fictícios e embeddings determinísticos.
- Comprovar resultado primário, IDs de fonte, mapa de fontes e contexto das páginas anterior e posterior.
- Comprovar que documento específico de outro campus é filtrado e que fonte institucional permanece.
- Comprovar que contexto ausente ou não coberto interrompe antes do embedding da pergunta.
- Comprovar `top-k` sem vizinhos e validação dos limites de configuração.
- Executar toda a suíte offline, checar lockfile e whitespace.
- Fazer diagnóstico controlado no índice real sem imprimir excertos locais.

## 13. Critérios de aceite

- **CA-01:** Resultados primários respeitam quantidade configurada e filtros de aplicabilidade.
- **CA-02:** Páginas vizinhas são recuperadas separadamente e preservam documento, página e trecho.
- **CA-03:** Toda fonte é vinculada a um `chunk_id` real e único na consulta.
- **CA-04:** Contexto insuficiente não dispara embedding nem é apresentado como ausência de regra.
- **CA-05:** Distâncias não são tratadas como probabilidade nem usadas em limiar não calibrado.
- **CA-06:** A recuperação pode ser executada sem LLM e os testes permanecem offline.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Testes offline implementados e aprovados
- [x] Diagnóstico sem LLM disponível
- [x] Nenhum item fora do escopo implementado
- [x] Documentação afetada atualizada

O item Maven do template foi substituído pelas verificações Python e uv aplicáveis ao projeto.

## 15. Critério de parada

Encerrar quando a busca filtrada produzir fontes rastreáveis e contexto vizinho sob limite configurado. Não produzir respostas acadêmicas; a próxima etapa é a SPEC-010 — Geração e validação.

## 16. Evidências de execução — 2026-10-13

- O teste focado de configuração, índice e recuperação aprovou 23 casos; a suíte completa aprovou 44 testes offline.
- O corpus local recebeu identificador institucional e campus explícitos onde aplicáveis, sem alterar seleção, hashes ou PDFs.
- `uv lock --check --offline`, a validação JSON e `git diff --check` foram aprovados.
- O diagnóstico real enviou somente a pergunta de teste à NVIDIA e recuperou quatro resultados primários de `doc4.pdf` nas páginas 13 e 14, além de contexto local das páginas 12, 14 e 15, totalizando o limite configurado de 12 fontes. Nenhum excerto foi impresso durante essa verificação.
- A integração voltou a emitir o aviso conhecido de catálogo para `nvidia/nemotron-3-embed-1b`, sem impedir a inferência.
