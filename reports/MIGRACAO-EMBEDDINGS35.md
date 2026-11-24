# Migração para Nemotron 3.5 Embed — 24/11/2026

## Configuração e segurança da migração

Modelo padrão atualizado em `Settings.embedding_model` para
`nvidia/nemotron-3.5-embed-1b`, mantendo **2.048 dimensões** e a mesma integração
LangChain, coleção, chunking e modelo de geração. Nenhuma dependência ou
lockfile foi alterado. Trabalho realizado diretamente, sem agentes Astra.

A [API oficial NVIDIA](https://build.nvidia.com/nvidia/nemotron-3_5-embed-1b/apireference)
documenta `passage` para documentos, `query` para perguntas e dimensão nativa
2.048. Duas chamadas reais com texto inteiramente fictício confirmaram esses
caminhos, vetores finitos, dimensões 2.048/2.048 e normas aproximadamente unitárias.

Embora a dimensão seja a mesma, trocar o modelo exige reconstruir os embeddings.
O teste `test_embedding_model_migration_requires_rebuild_even_with_same_dimension`
confirma a rejeição do índice antigo pela nova configuração, a preservação da
referência antiga se a reconstrução falhar e a publicação de uma nova versão
sem duplicar trechos nem apagar o manifesto anterior.

## Reconstrução real

| Item | Resultado |
| --- | --- |
| Modelo anterior | `nvidia/nemotron-3-embed-1b`, indisponível no endpoint por HTTP 410 |
| Novo modelo | `nvidia/nemotron-3.5-embed-1b` |
| Índice anterior preservado | `20261013T152802Z-a163be2c3fcf` |
| Novo índice ativo | `20261124T165648Z-facc42ff414c` |
| Documentos selecionados | 2 |
| Páginas físicas com trechos | 67 |
| Trechos únicos | 169 |
| Lotes de embeddings | 50 + 50 + 50 + 19 entradas |
| Respostas HTTP dos quatro lotes | 200 em todos |

O índice foi construído pelo fluxo existente `build_index()`, com nova pasta
de versão e publicação atômica da referência ativa. Após a publicação,
`load_active_index()` conferiu configuração, dimensão, IDs, contagens e fontes.
Os hashes dos PDFs permaneceram iguais e o manifesto anterior foi preservado.
Não foram alterados inventário, casos, expectativas ou prompts.

Preservar os arquivos do índice anterior não torna o modelo aposentado novamente
disponível: essa versão é histórico, não um fallback remoto funcional.

## Verificação do código

- RED: dois testes de configuração/fábrica falharam exigindo o novo nome.
- GREEN: **191 testes Python aprovados**, incluindo a migração e suas falhas
  seguras; **três testes Node aprovados**.
- `uv lock --check --offline`, `uv build --offline` e `git diff --check`:
  concluídos com código zero.
- Build desta etapa: `/tmp/opencode/assistente-ifma-build-embedding35`.
- Python 3.10.22 no ambiente auxiliar; `.venv` original preservada.
- Nenhum commit, push ou remoção de arquivos/dependências.

## Avaliação RAG real

A execução dos 21 casos usou o modelo de geração
`nvidia/nemotron-3.5-super-vl-120b-a12b` e limite operacional de **60 invocações**
contadas pelo executor. Na primeira execução, 20 casos concluíram e IFMA-015
teve erro do provedor na revisão de abstenção: 35 invocações. Foi repetido
somente esse erro técnico, uma vez, com limite de três invocações; o caso
concluiu como `insufficient_evidence`. As respostas válidas não foram repetidas.

| Resultado consolidado | Valor |
| --- | --- |
| Casos concluídos | 21/21 |
| Erros técnicos restantes | 0 |
| Estados esperados | 21/21 |
| Evidências esperadas recuperadas nos casos reais | 15/15 |
| Evidências esperadas recuperadas/citadas, incluindo sintéticos | 19/19 |
| Precisão automática por correspondência aos rótulos de referência | 20/32 — 62,5% |
| Revisões humanas aplicadas | 0/21 |
| Consumo incluindo a tentativa que falhou | 38 invocações: 16 embeddings e 22 gerações |

Os limites individuais de 60 e três foram preservados nos metadados. Sua soma
automática no consolidado é 63; o consumo efetivo de **38** foi conferido contra
o teto operacional autorizado de **60**, não aumentado.

Há fontes adicionais em nove casos: IFMA-001, IFMA-003, IFMA-004, IFMA-005,
IFMA-006, IFMA-008, IFMA-009, IFMA-011 e IFMA-013. Precisão por rótulos não é
suporte semântico: as fontes adicionais podem sustentar informações ou ser
sobrecitação, e precisam de revisão. Não se deve interpretar os 62,5% como
percentual de respostas corretas nem declarar o MVP semanticamente aprovado.

Execuções: `0c580e2172c14daea2e0ada8204b94ab` e
`0e5815cf310447f296b4599a8e5fddbc`. Mesmo experimento
`22ccdfbfccb85f19f9725c97cb36420519e50d15740e58ca348d31202b3db7ed`;
relatórios validados, configurações estáveis e substituição registrada com
preservação de ambos os relatórios-fonte.

Os cinco sintéticos fornecem evidências diretamente e não medem busca vetorial.
O caso sem contexto é resolvido antes de embeddings; o sintético sem evidência
não invoca o LLM. A execução não transfere revisões humanas anteriores.

## Artefatos locais e consumo

Arquivos ignorados pelo Git:

- `evaluation/embedding35-preflight-20261124T165256Z.local.json`:
  duas invocações de embeddings com texto fictício.
- `evaluation/embedding35-migration-20261124T165256Z.local.json`:
  metadados, preservação de fontes e quatro requisições HTTP de indexação
  observadas, sem registrar corpos ou credenciais.
- `evaluation/nvidia35-rag-20261124T165256Z.local.json`:
  execução completa original, separada dos relatórios anteriores.
- `evaluation/nvidia35-rag-retry-ifma015-20261124T165256Z.local.json`:
  repetição técnica de IFMA-015.
- `evaluation/nvidia35-rag-final-20261124T165256Z.local.json`:
  consolidação dos 21 resultados, sem sobrescrever os originais.

Testes e indexação são adicionais ao orçamento de 60 invocações da avaliação.
Consultas de catálogo e requisições internas do SDK não fazem parte do contador
do executor. O custo financeiro não é informado pela integração.

## Inicialização web em um comando

Criado `scripts/run-web.sh`, executável, que entra na raiz do projeto, usa
`.venv-web` (ou `.venv` como alternativa) e inicia Uvicorn em loopback.
Lê somente a chave NVIDIA de `.env` como dado quando ausente no ambiente,
sem executar shell do arquivo nem imprimir a chave.

Foi preparado `.venv-web` persistente com Python 3.10.22 instalado em
`~/.local/share/uv/python`, mantendo a `.venv` antiga. A execução web pelo
script não depende do ambiente temporário em `/tmp/opencode`.

```bash
./scripts/run-web.sh
# Porta alternativa, se 8000 estiver ocupada:
PORT=8001 ./scripts/run-web.sh
```

Quatro testes do launcher passaram: execução fora da raiz/caminho com espaços,
leitura da chave sem execução de `.env`, precedência da chave de ambiente e
erros de ambiente/chave ausentes. Antes da implementação, os quatro falharam
porque o script não existia; depois, os quatro passaram. A primeira fixture
foi corrigida para reutilizar o interpretador do ambiente de teste com seus
pacotes, em vez de criar um link que perdia o contexto da virtualenv.

Verificação real do script, a partir de diretório externo, na porta 8001:
página, JavaScript e `/api/context` retornaram HTTP 200. O processo de teste
foi encerrado sem chamada ao provedor. `bash -n`, `git diff --check` e a suíte
completa (**195 testes Python**) passaram. O servidor anterior na porta 8000
foi mantido; o script não encerra processos existentes.
