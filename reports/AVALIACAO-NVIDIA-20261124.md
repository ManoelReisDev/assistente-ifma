# Avaliação NVIDIA real — 24/11/2026

> Registro da etapa anterior à troca de embeddings. A migração autorizada
> posteriormente e a nova avaliação têm [relatório próprio](MIGRACAO-EMBEDDINGS35.md).

## Resultado

**Geração real respondeu aos casos sintéticos; avaliação RAG completa bloqueada.**
O provedor retornou HTTP 410 para `nvidia/nemotron-3-embed-1b`, informando fim de
vida em **23/11/2026 às 09:00 UTC**. Não é falta de evidência documental nem
erro de credencial comprovado: o modelo de embeddings configurado não está
mais disponível nesse endpoint.

Não foram alterados modelo, prompts, PDFs, índice, casos ou expectativas.
Não houve reindexação nem tentativa de usar embeddings diferentes com o índice
existente. Os relatórios antigos foram preservados.

## Execuções e consumo

| Etapa | Escopo | Limite | Uso contado | Resultado |
| --- | --- | --- | --- | --- |
| Piloto RAG | IFMA-001 | 3 invocações | 1 tentativa de embedding, 0 gerações | Erro de recuperação antes da geração |
| Diagnóstico | Mesma recuperação, para inspecionar a causa encadeada | Uma tentativa adicional | 1 tentativa de embedding, 0 gerações | HTTP 410 confirmado |
| Geração sintética | SYN-001 a SYN-005 | 10 invocações | 0 embeddings, 4 gerações | 5 casos concluídos, nenhum erro técnico |

Total observado nessas etapas: **duas tentativas de embedding e quatro
invocações de geração**. A integração não informa custo monetário. A contagem
da aplicação não inclui consultas de catálogo/inicialização ou eventuais
requisições internas do SDK; não é um teto financeiro.

Não foi iniciada a avaliação completa de 21 casos após a falha do piloto.
Não houve repetição de respostas válidas para selecionar a melhor saída.

## Modelo de geração e verificações

- Modelo solicitado: `nvidia/nemotron-3.5-super-vl-120b-a12b`.
- Configuração padrão preservada: temperatura 0, `top_p` 0,95, limite de 1.024
  tokens de conclusão, JSON Schema estrito e raciocínio desabilitado no template.
- Fonte das evidências: os cinco cenários inteiramente fictícios versionados
  em `evaluation/synthetic-cases.json`, sem busca vetorial nessas consultas.
- Estado esperado: **5/5**; fontes esperadas encontradas nas saídas: **4/4**;
  precisão automática por rótulos de fonte: **4/4**; erros técnicos: **0**.
- SYN-001: resposta e exceção preservadas; SYN-002: resposta parcial sem inventar
  taxa; SYN-004: fonte prioritária do grupo curado usada com explicação por data;
  SYN-005: resposta apoiada no trecho, sem seguir a instrução maliciosa inserida.
- SYN-003: mensagem obrigatória de falta de evidência, sem fontes e **sem chamada
  ao LLM**. Não demonstra capacidade do modelo de se abster diante de trechos
  relacionados mas insuficientes.

A inspeção assistida das quatro respostas geradas encontrou compatibilidade
com seus trechos e requisitos fictícios. **Nenhuma aprovação humana foi
registrada ou transferida dos experimentos anteriores**: o relatório mantém
`manual_review_total: 0` e métricas de suporte semântico/requisitos/citações
revisadas como não calculadas.

O `retrieval_recall` automático desses sintéticos não mede recuperação real:
as evidências foram fornecidas diretamente. O conjunto atual também não testa
conflito sem precedência curada, cobertura de todos os contextos nem resistência
geral a prompt injection.

## Proveniência

Ambiente de execução: Python 3.10.22 em
`/tmp/opencode/assistente-ifma-tests`, com as dependências do lockfile. O modelo
NVIDIA foi realmente chamado; não foi substituído por mock. A `.venv` original
não foi reparada nem descartada, e o ambiente auxiliar foi preservado.

Execução sintética:

- `run_id`: `01e6affd5aa64277bae51ba0d50a9955`.
- Experimento: `c4529d9b3473daf7d8acfbf4c8fc533376b84c40bbf445195a6b88f268480365`.
- Configuração estável durante a execução; estrutura, hashes e vínculos
  conferidos pelo validador do relatório.
- Índice existente: `20261013T152802Z-a163be2c3fcf`.

Comando lógico do piloto:

```bash
python -m academic_assistant evaluate \
  --report evaluation/nvidia-super-vl-pilot-20261124T164705Z.local.json \
  --max-provider-calls 3 --only-case IFMA-001
```

Comando lógico da etapa sintética:

```bash
python -m academic_assistant evaluate \
  --report evaluation/nvidia-super-vl-synthetic-20261124T164705Z.local.json \
  --max-provider-calls 10 \
  --only-case SYN-001 --only-case SYN-002 --only-case SYN-003 \
  --only-case SYN-004 --only-case SYN-005
```

Esses argumentos foram executados por `cli.main()` no ambiente auxiliar,
carregando somente `NVIDIA_API_KEY` para o processo, sem imprimir a credencial
nem executar o conteúdo de `.env` como script.

Relatórios locais ignorados pelo Git:

- `evaluation/nvidia-super-vl-pilot-20261124T164705Z.local.json`.
- `evaluation/nvidia-diagnostic-20261124T164705Z.local.json`.
- `evaluation/nvidia-super-vl-synthetic-20261124T164705Z.local.json`.

## Próximo passo necessário

Selecionar e confirmar um modelo de embeddings disponível, verificar sua
integração/dimensão, reconstruir o índice sem destruir a versão anterior e só
então executar novamente a avaliação RAG completa com revisão humana. A troca
de embeddings exige reindexação; não basta mudar o nome na consulta.
Essa migração não foi realizada nesta avaliação.
