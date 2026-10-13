# Plano de execução — conclusão do MVP

Data: 13 de outubro de 2026. Estado: em execução; SPEC-006 a SPEC-011 concluídas.

## 1. Objetivo e referências

Concluir o fluxo de consulta: PDF cadastrado → trechos → índice persistente → recuperação → resposta em português com documento, página física e excerto verificável. O plano segue o [AGENTS.md](AGENTS.md), o [relatório de progresso](RELATORIO-PROGRESSO.md), o [README](README.md) e as SPEC-001 a SPEC-005.

Manter Python, LangChain, uv, pytest e a CLI existentes. Usar um fluxo de recuperação seguido de geração, adequado ao RAG simples descrito na [documentação oficial do LangChain](https://docs.langchain.com/oss/python/deepagents/retrieval#2-step-rag). O AGENTS.md continua sendo a referência para os requisitos específicos do produto.

Este documento planeja meu trabalho de implementação; não significa que o assistente do produto executará ações ou usará agentes autônomos.

## 2. Ponto de partida conferido no planejamento

| Item | Estado atual |
| --- | --- |
| Código | SPEC-001 a SPEC-005, commit `cd99297` |
| Testes | 22 aprovados em nova execução offline |
| Ingestão padrão | 4 PDFs completos; 85 páginas aproveitadas |
| Documentos | `doc1.pdf`: 9 páginas; `doc2.pdf`: 9; `doc3.pdf`: 35; `doc4.pdf`: 32 |
| OCR | Experimento externo realizado nesta conversa; sem integração no código ou nas dependências da aplicação |
| Arquivo após OCR | `data/documents/doc4.pdf` atualmente tem texto extraível; `output/pdf/` está vazio |
| Divisão, índice, busca e geração | Ainda não implementados |
| Provedor e modelos | Ainda não escolhidos |

Verificações executadas para preparar este plano:

```bash
uv run --extra dev --locked --offline pytest -q
uv run --locked --offline python -m academic_assistant ingest
```

O relatório é uma referência histórica de 8 de outubro e descreve apenas dois PDFs e 18 páginas. Não substituir suas evidências históricas por resultados novos. Registrar a evolução em seção posterior, com data, comandos e limitações. O sucesso de extração das 85 páginas não certifica vigência, aplicabilidade ou qualidade semântica do corpus.

## 3. Sequência de entregas

Cada etapa começa pela elaboração de uma spec usando o template existente, adaptando a verificação ao projeto Python: o item Maven do template não se aplica. A numeração abaixo é proposta para as próximas specs.

| Ordem | Spec proposta | Incremento observável | Dependência |
| --- | --- | --- | --- |
| 1 | SPEC-006 — Corpus e evidências de avaliação | Corpus selecionado e perguntas com evidências esperadas | SPEC-005 |
| 2 | SPEC-007 — Divisão por página | Trechos rastreáveis e configuração de divisão | SPEC-006 |
| 3 | SPEC-008 — Embeddings e índice persistente | Criar e reconstruir índice sem perder a última versão válida | SPEC-007 e escolha do modelo de embeddings |
| 4 | SPEC-009 — Recuperação de evidências | Buscar trechos aplicáveis e contexto de páginas vizinhas | SPEC-008 |
| 5 | SPEC-010 — Geração e validação | Retornar resposta e fontes, com abstenção e erros distintos | SPEC-009 e escolha do LLM |
| 6 | SPEC-011 — Consulta pela CLI | Fluxo completo de indexação e pergunta no terminal | SPEC-010 |
| 7 | SPEC-012 — Avaliação e entrega | Evidências revisadas com o modelo real e documentação reproduzível | SPEC-011 |

### SPEC-006 — Corpus e evidências de avaliação

Atividades:

- Identificar o conteúdo e contexto dos quatro PDFs: instituição, modalidade, cursos e versão quando explicitamente informados.
- Selecionar um corpus inicial de contexto conhecido. Quando houver mistura de contextos, separar os documentos ou registrar metadados explícitos para filtragem posterior.
- Conferir a observação do relatório sobre textos idênticos de `doc1.pdf` e `doc2.pdf`; decidir sua inclusão na seleção sem apagar arquivos ou alterar a identidade usada pela ingestão.
- Registrar a origem e a revisão da cópia de `doc4.pdf` com OCR. Não alegar preservação do original com base apenas no arquivo atual; identificar onde está o original digitalizado e sua associação à cópia, se disponível.
- Revisar nas imagens os trechos com percentuais, prazos, negações e exceções usados na avaliação, especialmente os provenientes de OCR.
- Preparar inicialmente cerca de 15 perguntas com evidências esperadas, incluindo variações de linguagem, falta de suporte, resposta parcial, continuação entre páginas e contexto insuficiente. Conflitos e instruções maliciosas podem ser construídos em documentos sintéticos claramente fictícios.

Artefatos previstos: `specs/006-corpus-e-avaliacao.md`, definição simples do corpus local, `evaluation/` com casos sintéticos versionáveis e atualização do README. Textos privados e seus casos de avaliação devem permanecer em arquivos locais ignorados.

Aceite: cada caso respondível tem documento, página física e evidência revisada; dúvidas de aplicabilidade ficam registradas, sem inferir que uma data mais recente revoga outra norma. A seleção acadêmica que não puder ser determinada pelos documentos deve ser esclarecida com o usuário; desenvolvimento com corpus sintético pode continuar.

### SPEC-007 — Divisão por página

Atividades:

- Criar `chunking.py`, consumindo os `Document` já produzidos pela ingestão.
- Usar divisão recursiva por caracteres, preservando separadores de parágrafos e artigos quando possível. Proposta inicial para experimentar: 1.000 caracteres com sobreposição de 200; esses valores são ajustáveis e não representam calibração concluída.
- Centralizar tamanho e sobreposição em `Settings`, validando seus limites.
- Preservar metadados existentes e atribuir `chunk_id` determinístico com documento, hash da versão e posição do trecho na página.
- Manter cada trecho em uma única página e preservar o texto evidencial, sem limpeza que altere regras.

Artefatos previstos: `chunking.py`, alterações em `config.py`, testes de divisão, dependência de divisão compatível no `pyproject.toml` e `uv.lock`, README e spec.

Aceite: nenhuma origem é perdida; regras fictícias, condições e negações sobrevivem à divisão; execuções com os mesmos documentos e configuração produzem os mesmos identificadores; mudar o documento ou a divisão exige reconstrução do índice.

### SPEC-008 — Embeddings e índice persistente

Atividades:

- Escolher um único modelo de embeddings e verificar sua integração com Python 3.10 e as dependências travadas. Usar substituto local determinístico nos testes.
- Adotar como proposta um índice Chroma local persistente, sujeito à verificação de compatibilidade. Evitar o carregamento de metadados com desserialização insegura.
- Registrar modelo, dimensão dos vetores, parâmetros de divisão, versão do formato, documentos, hashes e totais em um manifesto do índice.
- Construir cada reconstrução em um diretório de versão separado. Validar os artefatos antes de atualizar atomicamente a referência à versão ativa, sem renomear um banco ainda aberto.
- Se qualquer documento selecionado falhar ou ficar parcial, interromper a publicação por padrão e conservar o último índice utilizável. Eventual corpus parcial precisa ser declarado explicitamente.
- Na carga, conferir manifesto e configuração; rejeitar incompatibilidades com orientação para reindexação.
- Reconstruir por completo para alterações e remoções, evitando trechos antigos ou duplicados. Se os arquivos mudarem depois da indexação, informar que o índice corresponde à versão anterior e requer atualização.
- Implementar e documentar o futuro comando `index` nesta entrega.

Artefatos previstos: `indexing.py`, configuração do provedor quando escolhido, manifesto em `data/index/`, testes de persistência e falhas, CLI, README, `.env.example` quando necessário e spec.

Aceite: índice reutilizável depois de reiniciar o processo; consulta não recalcula embeddings do corpus; mesma configuração de embeddings em indexação e consulta; falha de reconstrução preserva a versão ativa; alteração ou remoção de PDF não deixa resíduos após reconstrução bem-sucedida.

### SPEC-009 — Recuperação de evidências

Atividades:

- Criar `retrieval.py` com quantidade de resultados configurável; iniciar os experimentos com quatro trechos, sem limiar arbitrário de similaridade.
- Aplicar o contexto definido na SPEC-006 por restrição do corpus ou filtros de metadados. Se faltar contexto necessário, retornar a limitação ou solicitar esclarecimento.
- Recuperar contexto de página vizinha quando uma regra continuar além do trecho ou página, mantendo fontes separadas e um limite de contexto.
- Atribuir `source_id` por consulta e manter um mapa entre identificador e trecho real recuperado.
- Avaliar recuperação separadamente: presença da evidência esperada e das condições relevantes. Resultados do mesmo assunto não bastam para comprovar resposta.

Artefatos previstos: `retrieval.py`, testes de recuperação e contexto, casos de avaliação atualizados e spec. Uma função de diagnóstico deve permitir inspecionar a recuperação sem chamar o LLM.

Aceite: evidências esperadas recuperadas nos casos revisados; filtros respeitados; referências de páginas vizinhas corretas; falhas de busca ou índice seguem erro técnico. Qualquer limiar futuro só entra após calibração e documentação da métrica e de seu sentido.

### SPEC-010 — Geração e validação

Atividades:

- Criar `prompts.py`, `generation.py` e `validation.py`, com LLM substituível nos testes por injeção simples.
- Enviar pergunta e evidências identificadas ao modelo. Tratar textos recuperados como dados; exigir português claro, condições, exceções, referências junto às afirmações, resposta parcial e apresentação de conflitos.
- Definir uma saída estruturada interna simples que distinga resposta sustentada, parcial, conflito, contexto insuficiente e ausência de evidência. O modelo seleciona identificadores fornecidos, sem produzir documento, página ou excerto.
- Montar o retorno público `answer` e `sources` pela aplicação. Cada fonte terá `source_id`, `document_id`, `document_name`, `page_number`, `chunk_id` e `excerpt`.
- Usar inicialmente o trecho recuperado completo como excerto. Validar estrutura, referências presentes no texto, identificadores existentes e associação de metadados/excertos às evidências, admitindo normalização de espaços.
- Exigir fontes para qualquer resposta que afirme regras. Bloquear respostas inválidas; começar sem repetição automática de geração. Documentar o limite de zero tentativas de correção.
- Usar exatamente a mensagem exigida quando faltar suporte: “Não encontrei evidências suficientes nos documentos cadastrados para responder a essa pergunta.”
- Distinguir ausência de evidência de indisponibilidade do provedor, saída inválida, configuração incorreta e falha de recuperação.

Artefatos previstos: módulos acima, integração com o LLM escolhido, testes de contrato, fontes falsas, excertos inventados, respostas parciais, conflitos e instruções maliciosas; README e spec.

Aceite: fontes são produzidas apenas a partir das evidências recuperadas; fontes/páginas/excertos inválidos são rejeitados; erros técnicos não viram abstenção. Testes simulados validam os mecanismos, mas o suporte semântico precisa da avaliação real na SPEC-012.

### SPEC-011 — Consulta pela CLI

Atividades:

- Integrar o futuro comando `ask` ao índice e ao núcleo de resposta, mantendo `ingest` e `index` utilizáveis separadamente.
- Apresentar resposta com referências e, para cada fonte, documento, página física do PDF e trecho literal, no formato do AGENTS.md.
- Permitir configurar caminhos e contexto aplicável conforme o mecanismo já definido nas etapas anteriores.
- Mostrar erros técnicos em `stderr` e usar códigos de saída distintos de uma consulta concluída com falta de evidência.
- Documentar instalação, configuração, cadastro, indexação, atualização e consulta. Exemplos dos comandos novos só serão apresentados como funcionais após execução.

Aceite: teste completo offline com documentos e modelos fictícios; indexar, encerrar o processo, consultar reutilizando o índice e obter resposta com fonte; mesma CLI distingue abstenção, resposta parcial, conflito e falha técnica.

### SPEC-012 — Avaliação e entrega

Atividades:

- Executar os casos revisados com o modelo de embeddings e o LLM escolhidos, separadamente de `pytest`.
- Registrar configuração, hashes do corpus, versão do código e dos prompts, chamadas, custo observado quando disponível e limites de gasto configurados para a avaliação.
- Medir separadamente recuperação das evidências, suporte semântico, precisão das citações e abstenção. Revisar também conflitos, condições, exceções e instruções maliciosas.
- Corrigir os problemas identificados na camada responsável e repetir apenas os casos afetados e a regressão pertinente.
- Atualizar README, evidências das specs e relatório de progresso, preservando a cronologia.

Aceite: cada critério do MVP no AGENTS.md tem evidência reproduzível; casos críticos não exibem regras sem suporte ou citações inventadas; casos fora do corpus se abstêm; erros técnicos são distintos. Se não houver chave, orçamento ou disponibilidade do provedor, registrar a avaliação real como pendente e não declarar o MVP validado de ponta a ponta.

## 4. Escolhas e dependências externas

- **Escolhas de implementação propostas:** CLI, divisão por página e por caracteres, reconstrução completa do índice, persistência local e validação determinística com excertos montados pela aplicação.
- **Escolhas realizadas:** NVIDIA como provedor de embeddings, `nvidia/nemotron-3-embed-1b` com 2.048 dimensões e autorização operacional para indexar o corpus selecionado no endpoint hospedado.
- **Escolha de geração:** `nvidia/nemotron-3-super-120b-a12b`, com saída estruturada. A geração envia pergunta, evidências recuperadas e limitações ao endpoint; a validação real desta spec usa somente dados sintéticos.


- **Antes das chamadas externas:** documentar que a indexação envia textos dos trechos; a consulta envia a pergunta para embeddings e a pergunta com evidências recuperadas para geração. Usar credenciais de ambiente e exemplos fictícios; manter logs e testes comuns sem conteúdo sensível.
- **Compatibilidade:** conferir as documentações oficiais das integrações ao implementar; declarar dependências no `pyproject.toml`, atualizar `uv.lock` e executar os testes pertinentes. Não adicionar observabilidade externa por padrão.
- **OCR futuro:** manter o experimento atual como pré-processamento externo documentado. Uma integração automática pode ser planejada depois do fluxo de consulta, com rastreabilidade do original, idioma, versão da ferramenta e falhas por página. O ambiente temporário usado nesta conversa não constitui instalação reproduzível da aplicação.

## 5. Como executarei as atividades

Para cada spec, vou conferir alterações existentes, ler o código afetado, implementar a menor entrega completa, executar as verificações relevantes e registrar resultados reais. Atualizarei o README quando houver mudança de uso ou comportamento e preservarei arquivos do usuário. Commits, publicações e chamadas externas serão realizados apenas quando incluídos no escopo autorizado.

A próxima atividade executável é a SPEC-012: executar e revisar o conjunto de avaliação real, corrigir falhas na camada responsável e consolidar a documentação de entrega do MVP.

O critério de parada é o MVP funcionando pelo terminal e avaliado conforme o AGENTS.md. Interface web, OCR automático, pesquisa web nas respostas, autenticação, agentes autônomos e infraestrutura distribuída ficam para planejamento posterior.
