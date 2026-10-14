# SPEC-010 — Geração e validação

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-009 concluída; modelo de geração NVIDIA selecionado.
- **Entrega:** Evidências recuperadas podem produzir resposta estruturada em português, com fontes montadas e validadas pela aplicação, abstenção obrigatória e erros técnicos distintos.

## 2. Objetivo

Transformar evidências recuperadas em uma resposta acadêmica sem permitir que o modelo invente documento, página ou excerto. A aplicação deve bloquear saídas inválidas, preservar condições e conflitos por instrução explícita e retornar a mensagem obrigatória quando não houver suporte.

## 3. Contexto

A SPEC-009 fornece trechos reais com `source_id` e limitações do corpus. Esta entrega escolhe o endpoint gratuito `nvidia/nemotron-3-super-120b-a12b`, confirmado no catálogo da credencial como modelo de chat com saída estruturada. O Nemotron 3 Nano não foi escolhido porque seu endpoint gratuito foi descontinuado.

O modelo decide somente o estado, o texto e os identificadores citados. Metadados e excertos públicos são sempre reconstruídos a partir da recuperação. Testes comuns usam um modelo simulado e não acessam rede.

## 4. Pré-condições

- Resultado de recuperação com contexto e fontes identificadas.
- `NVIDIA_API_KEY` disponível somente para chamadas reais.
- Autorização adequada antes de enviar pergunta e evidências institucionais ao endpoint externo.

## 5. Escopo

- Centralizar prompt de sistema e construção do contexto.
- Tratar pergunta e evidências recuperadas como dados não confiáveis.
- Configurar um único LLM NVIDIA com saída JSON estruturada.
- Definir estados `supported`, `partial`, `conflict` e `insufficient_evidence`.
- Validar estrutura, referências no texto, IDs declarados e existência das fontes.
- Montar documento, página, `chunk_id` e excerto somente a partir da recuperação.
- Exigir fontes em respostas acadêmicas e ao menos duas em conflitos.
- Retornar abstenção exata sem chamar o modelo quando não houver evidências.
- Distinguir indisponibilidade do provedor de saída inválida.
- Acrescentar limitações do corpus de forma determinística às respostas sustentadas.

## 6. Fora do escopo

Comando `ask`, formatação terminal, histórico de conversa, segundo LLM verificador, avaliação completa do corpus real, limiar de recuperação, autenticação de usuários e interface web. A integração da consulta à CLI pertence à SPEC-011; a avaliação real completa e a repetição corretiva limitada acrescentada depois pertencem à SPEC-012.

## 7. Requisitos funcionais

- **RF-01:** Enviar ao modelo somente a pergunta, contexto, limitações e evidências identificadas da consulta.
- **RF-02:** Instruir resposta em português baseada exclusivamente nas evidências, preservando condições, exceções, negações, parcialidade e conflitos.
- **RF-03:** O modelo seleciona `source_ids` fornecidos; a aplicação valida e acrescenta as referências textuais `[source_id]` à resposta.
- **RF-04:** O modelo não pode fornecer metadados de fonte; campos adicionais tornam a saída inválida.
- **RF-05:** Respostas `supported`, `partial` e `conflict` exigem ao menos uma fonte válida; conflito exige duas.
- **RF-06:** `insufficient_evidence` não aceita referências e sempre retorna exatamente a mensagem exigida pelo AGENTS.md.
- **RF-07:** Recuperação sem evidências retorna abstenção sem chamar o provedor.
- **RF-08:** Saída inválida ou falha do provedor não pode ser convertida em abstenção.
- **RF-09:** A entrega original não realizava repetição; após a SPEC-012, estrutura inválida ou abstenção com evidências admite somente uma tentativa adicional.

## 8. Requisitos técnicos

- **RT-01:** Usar `ChatNVIDIA` de `langchain-nvidia-ai-endpoints` 1.x com `nvidia/nemotron-3-super-120b-a12b`.
- **RT-02:** Usar o `response_format` OpenAI compatível com JSON Schema e validação Pydantic estrita, conforme suporte do endpoint hospedado.
- **RT-03:** Configurar `temperature=0.0`, `top_p=0.95`, máximo de 1.024 tokens e `enable_thinking=False` para reservar a saída ao JSON e reduzir variação em respostas normativas.
- **RT-04:** Fazer uma chamada inicial e, após a alteração da SPEC-012, no máximo uma segunda chamada para correção estrutural ou revisão de abstenção.
- **RT-05:** Usar injeção simples do modelo para testes offline.
- **RT-06:** Não registrar pergunta, evidências, resposta ou chave por padrão.

## 9. Modelo e contratos

`ModelDecision`, validado com campos adicionais proibidos:

| Campo | Tipo | Responsabilidade |
| --- | --- | --- |
| `status` | enum | Estado semântico da resposta |
| `answer` | string | Texto em português sem metadados; citações são acrescentadas pela aplicação |
| `source_ids` | lista de strings | Seleção entre IDs fornecidos |
| `unsupported_parts` | lista de strings | Partes pedidas sem suporte; não vazia somente em resposta parcial |

`AnswerResult` contém `answer`, `sources` e `status`. Cada `AnswerSource` possui `source_id`, `document_id`, `document_name`, `page_number`, `chunk_id` e `excerpt`, todos copiados da recuperação correspondente.

Configuração padrão:

| Campo | Valor |
| --- | --- |
| `llm_provider` | `nvidia` |
| `llm_model` | `nvidia/nemotron-3-super-120b-a12b` |
| `llm_temperature` | `0.0` |
| `llm_top_p` | `0.95` |
| `llm_max_tokens` | `1024` |

## 10. Tratamento de erros

- Chave ausente ou provedor não suportado produz `GenerationError`.
- Falha ao inicializar ou invocar a NVIDIA produz `GenerationProviderError`.
- JSON inválido, campos extras, tipo inesperado, fonte falsa, citação ausente, ID repetido ou conflito com uma só fonte produz `GenerationValidationError`.
- Esses erros impedem a exibição da resposta e preservam sua causa encadeada.
- Ausência de evidência é um resultado válido e usa caminho próprio, não uma exceção técnica.

## 11. Arquivos afetados

- `specs/010-geracao-e-validacao.md`
- `src/academic_assistant/prompts.py`
- `src/academic_assistant/generation.py`
- `src/academic_assistant/validation.py`
- `src/academic_assistant/config.py`
- `tests/test_generation.py`
- `tests/test_bootstrap.py`
- `.env.example`
- `README.md`
- `PLANO-EXECUCAO.md`

## 12. Estratégia de testes

- Simular respostas sustentada, parcial, conflitante e sem evidência.
- Confirmar abstenção sem chamada ao modelo quando a recuperação estiver vazia.
- Rejeitar fonte inexistente, citação ausente, ID repetido, conflito incompleto, metadados e excertos fornecidos pelo modelo.
- Comprovar que falha do provedor continua erro técnico.
- Inspecionar prompt com instrução maliciosa dentro do conteúdo fictício.
- Confirmar configuração NVIDIA sem usar chave real.
- Executar suíte completa offline, lockfile, compilação e whitespace.
- Fazer uma chamada real separada apenas com evidências sintéticas, sem enviar PDFs locais.

## 13. Critérios de aceite

- **CA-01:** Resposta sustentada contém fontes reais montadas pela aplicação.
- **CA-02:** Fonte, página ou excerto inventado pelo modelo não chega ao retorno público.
- **CA-03:** Abstenção usa a mensagem exata e fontes vazias.
- **CA-04:** Resposta parcial e conflito preservam seus estados e fontes.
- **CA-05:** Instruções presentes em evidências são delimitadas como dados não confiáveis.
- **CA-06:** Falha técnica e saída inválida são distinguíveis da falta de evidência.
- **CA-07:** Testes comuns passam offline e sem credenciais.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Testes offline implementados e aprovados
- [x] Prompt e contrato estruturado identificáveis
- [x] Nenhum item fora do escopo implementado
- [x] Documentação afetada atualizada

O item Maven do template foi substituído pelas verificações Python e uv aplicáveis ao projeto.

## 15. Critério de parada

Encerrar quando evidências sintéticas puderem gerar e validar uma resposta real com fontes montadas pela aplicação. Não adicionar o comando `ask`; a próxima etapa é a SPEC-011 — Consulta pela CLI.

## 16. Evidências de execução — 2026-10-13

- O catálogo NVIDIA confirmou `nvidia/nemotron-3-super-120b-a12b` como `chat` com suporte a saída estruturada.
- Os testes focados foram aprovados e a suíte completa terminou com **59 testes offline aprovados**.
- A SPEC-012 ampliou o contrato com `unsupported_parts`, `temperature=0.0`, normalização segura de abstenção e uma única tentativa adicional limitada; os resultados reais estão registrados na SPEC-012.
- `uv lock --check --offline`, compilação de `src` e `tests` e `git diff --check` foram aprovados.
- O primeiro smoke test real mostrou que o modelo selecionou corretamente `source_ids=["1"]`, mas não escreveu `[1]` no texto; o validador bloqueou a saída, sem exibi-la nem convertê-la em abstenção.
- A responsabilidade de renderizar `[source_id]` foi então movida deterministicamente para a aplicação. O modelo continua selecionando apenas IDs existentes, e qualquer referência escrita por ele é rejeitada.
- O smoke test final enviou somente uma regra fictícia à NVIDIA e retornou `supported`, resposta em português com `[1]` acrescentado pela aplicação e fonte fictícia correta (`Regulamento fictício`, página 1, `ficticio-1`). Nenhum PDF ou excerto local foi enviado nessa validação.
