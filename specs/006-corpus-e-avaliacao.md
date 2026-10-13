# SPEC-006 — Corpus e evidências de avaliação

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-005 concluída.
- **Entrega:** Corpus acadêmico inicial delimitado e conjunto de avaliação com evidências revisadas por página, sem implementar as etapas posteriores do RAG.

## 2. Objetivo

Definir quais documentos locais podem alimentar inicialmente o assistente de regulamentos acadêmicos e preparar perguntas de avaliação capazes de medir recuperação, sustentação, preservação de condições e abstenção. Impedir que documentos duplicados ou fora do domínio sejam tratados como regras discentes e registrar aplicabilidade e proveniência antes da indexação.

## 3. Contexto

A ingestão processa quatro PDFs locais, mas sucesso de extração não comprova pertinência, vigência ou aplicabilidade. Dois arquivos contêm a mesma lei federal sobre carreira técnico-administrativa. Um guia de 2025 é específico do Campus São Luís–Monte Castelo. Uma resolução institucional de 2013 contém normas gerais de graduação; o arquivo cadastrado é a versão pós-OCR que o responsável pelo corpus colocou intencionalmente na pasta de documentos após apagar a cópia digitalizada anterior.

Esta entrega segue o AGENTS.md: nenhuma data mais recente é tratada como revogação automática, os excertos permanecem associados à página física e incerteza de contexto não é convertida em regra universal.

## 4. Pré-condições

- SPEC-005 e ingestão por página disponíveis.
- Quatro PDFs locais presentes em `data/documents/`, fora do versionamento.
- Testes e comandos executáveis offline pelo ambiente travado.
- Revisão do texto extraído e da imagem das páginas usadas nas evidências.

## 5. Escopo

- Identificar assunto, instituição, nível, campus, versão e modalidade quando explícitos.
- Comparar conteúdo extraído para detectar duplicidade textual.
- Selecionar o corpus discente inicial sem apagar ou renomear arquivos.
- Registrar hash, decisão de inclusão, papel e limites de aplicabilidade em inventário local.
- Registrar que `doc4.pdf` é a versão pós-OCR escolhida para a ingestão e que seu hash identifica essa versão atual.
- Criar cerca de 15 perguntas locais com evidências esperadas e cenários de resposta completa, parcial, falta de evidência, continuação entre páginas e contexto insuficiente.
- Criar casos sintéticos versionáveis para conflito e instrução maliciosa, além dos demais comportamentos essenciais.
- Documentar a organização e o uso dos artefatos de avaliação.

## 6. Fora do escopo

Divisão em trechos, embeddings, índice vetorial, filtros de recuperação, geração, validação de saída, comandos `index` ou `ask`, avaliação com LLM real, busca na web e comprovação jurídica de vigência. Não integrar OCR à aplicação, publicar PDFs locais ou versionar seus excertos.

## 7. Requisitos funcionais

- **RF-01:** Cada PDF deve ter decisão explícita de inclusão ou exclusão, sem remoção do arquivo.
- **RF-02:** Duplicatas textuais devem ser identificadas por comparação do texto normalizado, preservando identidades e hashes distintos.
- **RF-03:** O corpus inicial deve ser restrito a regras discentes de graduação do IFMA; fonte específica de campus só pode ser aplicada ao seu contexto.
- **RF-04:** Documento com vigência não comprovada deve manter essa limitação; datas não autorizam inferir revogação.
- **RF-05:** Cada caso local respondível deve indicar documento, página física e excerto literal revisado na imagem.
- **RF-06:** A avaliação deve incluir variação de linguagem, condição, exceção, negação, resposta parcial, falta de suporte, múltiplas páginas e falta de contexto.
- **RF-07:** Conflito e instrução maliciosa devem ser representados por dados claramente fictícios e versionáveis.
- **RF-08:** Evidências derivadas dos PDFs locais devem permanecer ignoradas pelo Git.

## 8. Requisitos técnicos

- **RT-01:** Usar JSON UTF-8 legível e validável pela biblioteca padrão, com `format_version` igual a 1.
- **RT-02:** Usar os mesmos `document_id`, `document_name`, `document_hash` e `page_number` produzidos pela ingestão.
- **RT-03:** Aceitar apenas normalização de espaços ao conferir que um excerto local pertence ao texto extraído da página citada.
- **RT-04:** Manter casos sintéticos e locais separados. Nomes terminados em `.local.json` devem ser ignorados pelo Git.
- **RT-05:** Não adicionar dependências nem alterar o lockfile.
- **RT-06:** Os artefatos não devem ser carregados automaticamente em imports nem criar efeitos no sistema de arquivos.

## 9. Modelo e contratos

`evaluation/corpus.local.json` contém uma lista `documents`. Cada item registra identidade de ingestão, título identificado, escopo conhecido, decisão de seleção e limitações. A seção `selection` define o conjunto inicial e sua política de aplicação.

`evaluation/cases.local.json` e `evaluation/synthetic-cases.json` contêm uma lista `cases`. Cada caso possui:

| Campo | Contrato |
| --- | --- |
| `id` | Identificador único e estável no arquivo |
| `category` | Capacidade avaliada |
| `question` | Pergunta em linguagem natural |
| `context` | Instituição, campus, nível ou regime disponível |
| `expected.status` | `answerable`, `partial`, `insufficient_evidence`, `context_required` ou `conflict` |
| `expected.answer_requirements` | Pontos semânticos que a resposta deve preservar |
| `expected.evidence` | Evidências esperadas; vazia quando não há fonte aplicável |

Cada evidência local contém `document_id`, `document_name`, `page_number` e `excerpt`. `source_id` não é fixado nos casos locais porque será atribuído pela aplicação por consulta em uma spec posterior.

### 9.1. Seleção do corpus

| Documento | Decisão | Contexto e motivo |
| --- | --- | --- |
| `doc1.pdf` | Excluído | Lei nº 11.091/2005 sobre carreira técnico-administrativa; fora do domínio discente |
| `doc2.pdf` | Excluído | Mesmo texto normalizado de `doc1.pdf`; hash de arquivo distinto; fora do domínio discente |
| `doc3.pdf` | Incluído como complemento | Guia do Estudante da Graduação, 2ª edição, 2025, específico do Campus São Luís–Monte Castelo |
| `doc4.pdf` | Incluído como norma geral | Anexo à Resolução nº 117/2013, Normas Gerais dos Cursos de Graduação do IFMA; vigência atual não comprovada |

O corpus selecionado não pode responder automaticamente a pós-graduação, ensino técnico, outro campus quando a evidência for específica de Monte Castelo ou outra instituição. A modalidade geral de aplicação não foi identificada com segurança e permanece sem valor no inventário.

### 9.2. Proveniência do OCR

Os metadados de `doc4.pdf` identificam `OCRmyPDF 17.13.0 / OCRmyPDF fpdf2 + Tesseract OCR 4.1.1`. O responsável pelo corpus confirmou que moveu intencionalmente a versão pós-OCR para `data/documents/doc4.pdf` e apagou o arquivo digitalizado anterior. O hash cadastrado identifica a versão pós-OCR atual, que é o documento selecionado para ingestão. As evidências usadas foram comparadas visualmente às páginas renderizadas dessa versão.

## 10. Tratamento de erros

- JSON inválido impede usar o conjunto e deve ser relatado como erro de artefato, não como falta de evidência.
- Documento ou página ausente invalida o caso correspondente.
- Excerto que não pertença à página citada, após normalização de espaços, invalida o caso.
- Hash divergente indica que a evidência local pertence a outra versão e exige nova revisão.
- Falta de contexto aplicável produz `context_required`; ausência de suporte produz `insufficient_evidence`.
- Proveniência ou vigência desconhecida deve continuar explícita e não bloquear o uso de casos sintéticos.

## 11. Arquivos afetados

- `specs/006-corpus-e-avaliacao.md`
- `evaluation/README.md`
- `evaluation/synthetic-cases.json`
- `evaluation/corpus.local.json` — local e ignorado
- `evaluation/cases.local.json` — local e ignorado
- `.gitignore`
- `README.md`

## 12. Estratégia de testes

- Validar os três arquivos JSON com `uv run --locked --offline python -m json.tool`.
- Conferir unicidade dos identificadores e estados permitidos.
- Ingerir os PDFs e verificar hashes, páginas e correspondência literal dos excertos locais com normalização de espaços.
- Comparar os textos normalizados de `doc1.pdf` e `doc2.pdf`.
- Renderizar e revisar as páginas citadas que contêm percentuais, prazos, condições e negações, sobretudo no documento com OCR.
- Executar a suíte offline existente para provar ausência de regressão.
- Verificar exclusões do Git e `git diff --check`.

## 13. Critérios de aceite

- **CA-01:** Os quatro PDFs têm contexto e decisão de seleção registrados; nenhum foi apagado ou renomeado.
- **CA-02:** A duplicidade textual de `doc1.pdf` e `doc2.pdf` está comprovada sem confundir hash de conteúdo binário com hash de texto normalizado.
- **CA-03:** O corpus inicial contém apenas `doc3.pdf` e `doc4.pdf`, com escopos e incerteza de vigência explícitos.
- **CA-04:** A substituição intencional pelo arquivo pós-OCR está registrada, e o hash é atribuído somente à versão atual.
- **CA-05:** Há aproximadamente 15 casos locais; todos os respondíveis possuem evidências reais revisadas e válidas.
- **CA-06:** Há casos versionáveis para resposta, parcialidade, abstenção, conflito e instrução maliciosa, identificados como fictícios.
- **CA-07:** Arquivos locais com conteúdo dos PDFs não aparecem no versionamento.
- **CA-08:** JSON, correspondência das evidências e testes existentes passam offline.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Corpus inicial delimitado
- [x] Evidências locais revisadas e não versionadas
- [x] Casos sintéticos versionáveis criados
- [x] Testes e verificações pertinentes aprovados
- [x] Nenhum item fora do escopo implementado
- [x] README atualizado

O item Maven do template foi substituído pelas verificações Python e uv aplicáveis ao projeto.

## 15. Critério de parada

Encerrar quando a seleção, as limitações e os casos estiverem registrados e verificáveis. Não iniciar divisão, indexação ou integração com provedores nesta entrega. A próxima etapa é a SPEC-007.

## 16. Evidências de execução — 2026-10-13

- Os quatro PDFs foram ingeridos: 85 páginas aproveitadas, sem páginas rejeitadas nesta execução.
- `doc1.pdf` e `doc2.pdf` produziram o mesmo SHA-256 do texto normalizado (`12a94c8fc285ed28abcbc9b16bca5d79169449f614d90f26ee44e7ce2eb9097d`), embora os hashes binários permaneçam distintos.
- Foram criados 16 casos locais: 12 respondíveis diretos, um entre páginas, um parcial, um sem evidência e um que exige contexto. Alguns casos acumulam mais de uma capacidade.
- Foram criados cinco casos sintéticos versionáveis: resposta com exceção, parcial, sem evidência, conflito e instrução maliciosa.
- As páginas físicas 10, 13, 14, 22 e 23 de `doc4.pdf` e 17, 19 e 20 de `doc3.pdf` foram renderizadas e comparadas com o texto extraído usado nas evidências.
- O responsável pelo corpus confirmou que substituiu manualmente a cópia digitalizada anterior por `doc4.pdf` pós-OCR e apagou a versão antiga; o inventário registra essa decisão.
- `uv run --locked --offline python -m json.tool` validou os três arquivos JSON.
- A validação local confirmou quatro hashes, 85 pares documento/página e a presença literal de todos os excertos nas páginas citadas após normalização de espaços.
- `uv run --extra dev --locked --offline pytest -q`: **23 testes aprovados**, incluindo a estrutura dos cinco casos sintéticos.
- `git check-ignore -v` confirmou que `corpus.local.json` e `cases.local.json` estão ignorados; `git diff --check` e a verificação equivalente dos arquivos novos não encontraram erros de whitespace.
