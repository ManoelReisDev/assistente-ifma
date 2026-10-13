# SPEC-008 — Embeddings e índice persistente

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-007 concluída.
- **Entrega:** O corpus selecionado pode ser reconstruído em um índice Chroma local, versionado e reutilizável, com publicação atômica e manifesto verificável.

## 2. Objetivo

Transformar os trechos rastreáveis em embeddings persistidos e disponibilizar uma única versão ativa do índice sem recalcular o corpus em cada consulta. Impedir que falhas de reconstrução, mudanças de configuração ou alterações nos PDFs sejam confundidas com um índice válido e atual.

## 3. Contexto

A SPEC-007 produz trechos literais por página com `chunk_id` determinístico. A SPEC-006 mantém a seleção revisada do corpus em `evaluation/corpus.local.json`. Ainda não havia modelo de embeddings, armazenamento vetorial, manifesto, publicação segura ou comando de indexação.

Esta entrega escolhe `nvidia/nemotron-3-embed-1b`, da NVIDIA, com 2.048 dimensões, e Chroma local persistente. A integração real requer `NVIDIA_API_KEY` e envia o texto dos trechos selecionados ao endpoint hospedado da NVIDIA. Os testes comuns substituem o provedor por embeddings locais determinísticos e permanecem offline.

## 4. Pré-condições

- Inventário local do corpus válido, com ao menos um documento selecionado.
- PDFs selecionados presentes, legíveis, integralmente extraíveis e com os hashes revisados.
- Ambiente sincronizado com as dependências travadas.
- `NVIDIA_API_KEY` disponível apenas para a execução real do comando `index`.

## 5. Escopo

- Configurar um único provedor e modelo de embeddings.
- Adotar Chroma local por meio da integração dedicada do LangChain.
- Ler a seleção do corpus e rejeitar documentos selecionados ausentes, parciais ou alterados.
- Reconstruir todos os trechos selecionados em um novo diretório de versão.
- Validar IDs, dimensão e totais antes da publicação.
- Persistir manifesto com configuração, documentos, hashes e contagens.
- Atualizar atomicamente a referência `active.json` somente após o sucesso.
- Carregar o índice ativo sem recalcular embeddings dos documentos.
- Detectar incompatibilidade de configuração e divergência dos documentos atuais.
- Expor o comando `index` e documentar credenciais, dados enviados e limitações.

## 6. Fora do escopo

Recuperação por similaridade na interface, limiar de relevância, filtros de aplicabilidade, geração, prompts, validação de respostas, cache separado de embeddings, atualização incremental, remoção automática de versões inativas, rollback por comando, múltiplos provedores, execução de OCR e comprovação de vigência. A SPEC-009 será responsável pela recuperação.

## 7. Requisitos funcionais

- **RF-01:** Indexar somente os identificadores incluídos no inventário do corpus.
- **RF-02:** Interromper a reconstrução se qualquer documento selecionado faltar, estiver parcial ou divergir do hash revisado.
- **RF-03:** Criar uma nova versão completa; nunca acrescentar trechos ao índice ativo existente.
- **RF-04:** Publicar a nova versão somente depois de validar todos os trechos persistidos e sua dimensão.
- **RF-05:** Preservar a referência ativa anterior quando embeddings, Chroma, manifesto ou publicação falharem.
- **RF-06:** Carregar a versão ativa após nova instanciação do processo sem chamar `embed_documents` novamente.
- **RF-07:** Rejeitar índices com configuração, formato, totais, artefatos ou origens incompatíveis.
- **RF-08:** Uma reconstrução bem-sucedida após alteração ou remoção deve apresentar apenas os trechos do corpus atual na versão ativa.

## 8. Requisitos técnicos

- **RT-01:** Usar `langchain-nvidia-ai-endpoints` 1.x e `NVIDIAEmbeddings` com `nvidia/nemotron-3-embed-1b`; validar a saída fixa de 2.048 dimensões antes da publicação.
- **RT-02:** Usar `langchain-chroma` 1.x com persistência local e telemetria anonimizada desabilitada.
- **RT-03:** Limitar `onnxruntime` a `<1.24` enquanto o projeto suporta CPython 3.10, pois a versão 1.24.3 resolvida inicialmente não oferecia wheel para esse runtime.
- **RT-04:** Não usar pickle nem habilitar desserialização insegura.
- **RT-05:** Armazenar versões em `data/index/versions/<index_id>/`, sem renomear um banco Chroma aberto.
- **RT-06:** Gravar JSON em arquivo temporário no mesmo diretório, sincronizá-lo e usar `os.replace` para publicação atômica.
- **RT-07:** Manter a integração de embeddings injetável pela interface `Embeddings` do LangChain.
- **RT-08:** Não registrar chaves, textos completos ou perguntas em logs.

## 9. Modelo e contratos

### 9.1. Configuração

`Settings` passa a fornecer:

| Campo | Padrão |
| --- | --- |
| `corpus_file` | `evaluation/corpus.local.json` |
| `embedding_provider` | `nvidia` |
| `embedding_model` | `nvidia/nemotron-3-embed-1b` |
| `embedding_dimensions` | `2048` |
| `collection_name` | `academic-regulations` |

### 9.2. Armazenamento

```text
data/index/
├── active.json
└── versions/
    └── <index_id>/
        ├── manifest.json
        └── chroma/
```

`active.json` contém somente a versão do formato e o identificador publicado. Diretórios sem referência ativa são inativos e não podem ser carregados implicitamente.

O manifesto registra `index_id`, data UTC, coleção, provedor, modelo, dimensão, unidade e parâmetros de divisão, documentos, hashes, páginas, trechos, totais e checksum do conjunto de `chunk_id`.

### 9.3. Migração do provedor

O caminho de avanço mantém os diretórios antigos, troca a configuração para NVIDIA e executa uma reconstrução completa. Um manifesto de outro provedor, modelo ou dimensão é rejeitado antes da carga. A nova versão só substitui `active.json` depois da validação.

O rollback não é automatizado nesta spec. Os diretórios anteriores não são apagados; para voltar ao provedor anterior seria necessário restaurar a versão correspondente do código e das dependências e republicar deliberadamente sua referência ativa. Nenhum diretório antigo deve ser removido durante a migração.

### 9.4. Operações

- `prepare_index_documents(settings)` valida a seleção, ingere e divide o corpus.
- `rebuild_index(chunks, embeddings, settings)` persiste, valida e publica uma nova versão.
- `build_index(settings, embeddings)` executa as duas operações anteriores.
- `load_active_index(settings, embeddings)` valida manifesto, fontes e Chroma antes de retornar o armazenamento.
- `validate_index_sources(manifest, settings)` confere seleção e SHA-256 atuais sem gerar embeddings.

## 10. Tratamento de erros

- Chave ausente, inventário inválido, documento incompleto, hash divergente, falha do provedor, falha de disco ou Chroma inválido produzem `IndexingError` e código 1 na CLI.
- Configuração divergente produz `IncompatibleIndexError` com orientação para reconstrução.
- Mudança, remoção ou seleção diferente produz `StaleIndexError` com orientação para reconstrução.
- Nenhuma dessas falhas deve ser apresentada como falta de evidência acadêmica.
- Uma versão incompleta pode permanecer sem publicação para diagnóstico; somente `active.json` define a versão utilizável.

## 11. Arquivos afetados

- `specs/008-embeddings-e-indice-persistente.md`
- `src/academic_assistant/indexing.py`
- `src/academic_assistant/config.py`
- `src/academic_assistant/cli.py`
- `tests/test_indexing.py`
- `tests/test_bootstrap.py`
- `pyproject.toml`
- `uv.lock`
- `.env.example`
- `README.md`

## 12. Estratégia de testes

- Usar uma implementação local determinística de `Embeddings`, sem rede ou credenciais.
- Persistir trechos fictícios, carregar outra instância e consultar sem recalcular embeddings dos documentos.
- Falhar uma reconstrução e comprovar que `active.json` não mudou.
- Reconstruir com conteúdo novo e comprovar que a versão ativa não contém IDs antigos.
- Alterar o arquivo de origem e rejeitar o índice como desatualizado.
- Alterar parâmetros de divisão e rejeitar o índice como incompatível.
- Simular documento selecionado parcialmente processado.
- Validar ausência da chave e o despacho da CLI.
- Executar a suíte offline, conferir o lockfile e construir temporariamente o lote local com embeddings determinísticos.

## 13. Critérios de aceite

- **CA-01:** O índice pode ser carregado de novo e consultado sem recalcular embeddings do corpus.
- **CA-02:** Manifesto e Chroma concordam em IDs, dimensão e totais.
- **CA-03:** A mesma configuração de modelo é exigida na construção e na carga.
- **CA-04:** Falhas não substituem a referência ativa anterior.
- **CA-05:** Uma reconstrução completa não mistura trechos antigos na versão ativa.
- **CA-06:** PDFs ou seleção alterados tornam o índice explicitamente desatualizado.
- **CA-07:** Testes automatizados funcionam offline e sem chave real.
- **CA-08:** O README permite configurar e executar o comando real sem omitir o envio de conteúdo ao provedor.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Testes offline implementados e aprovados
- [x] Manifesto e publicação atômica implementados
- [x] Lockfile aprovado em modo offline
- [x] Nenhum item fora do escopo implementado
- [x] README e `.env.example` atualizados
- [x] Evidências e limitação externa registradas

O item Maven do template foi substituído pelas verificações Python e uv aplicáveis ao projeto.

## 15. Critério de parada

Encerrar quando o corpus selecionado puder gerar uma versão persistente, validada e reutilizável do índice, mantendo a versão ativa após falhas. Não implementar recuperação ou geração; a próxima etapa é a SPEC-009.

## 16. Evidências de execução — 2026-10-13

- Dependências resolvidas: `langchain-chroma` 1.1.0, `langchain-nvidia-ai-endpoints` 1.4.3, ChromaDB 1.5.9 e `onnxruntime` 1.23.2.
- A tentativa inicial com `onnxruntime` 1.24.3 falhou por ausência de wheel para CPython 3.10; a restrição compatível foi registrada no manifesto do projeto.
- `uv run --extra dev --locked --offline pytest -q`: **40 testes aprovados**.
- O corpus selecionado (`doc3.pdf` e `doc4.pdf`) produziu 67 páginas e 169 trechos: 35 páginas/66 trechos para `doc3.pdf` e 32 páginas/103 trechos para `doc4.pdf`.
- Esse índice foi reconstruído em diretório temporário com embeddings determinísticos, recarregado e consultado sem recalcular embeddings dos documentos.
- A mesma reconstrução foi repetida com o manifesto padrão NVIDIA de 2.048 dimensões; os 169 trechos foram carregados e consultados, e um manifesto de outro provedor foi rejeitado como incompatível.
- `uv lock --check --offline` e `git diff --check` foram aprovados.
- A configuração anterior de OpenAI foi substituída pela NVIDIA sem apagar diretórios de índice existentes. Manifestos antigos permanecem incompatíveis e exigem reconstrução completa.
- A credencial e a inferência real foram verificadas: `embed_query` retornou as 2.048 dimensões esperadas.
- A indexação real publicou `20261013T144645Z-1304d1326486`, com 2 documentos, 67 páginas e 169 trechos.
- `langchain-nvidia-ai-endpoints` 1.4.3 emitiu um aviso porque seu catálogo estático ainda não classifica `nvidia/nemotron-3-embed-1b`; a descoberta do modelo e a inferência real funcionaram corretamente.
