# SPEC-004 — Ingestão de PDFs com origem por página

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-001, SPEC-002 e SPEC-003 concluídas.
- **Entrega:** PDFs locais convertidos em documentos LangChain por página, com origem verificável e relatório de processamento.

## 2. Objetivo

Extrair texto de regulamentos PDF preservando a associação entre conteúdo, arquivo e página física. Preparar a entrada das próximas etapas do RAG e informar quando a extração for incompleta ou impossível.

## 3. Contexto

O projeto possui configuração de caminhos, CLI e ambiente com uv validado. Ainda não há ingestão. Os requisitos de origem, extração parcial e preservação dos documentos estão em [AGENTS.md](../AGENTS.md).

Esta entrega produz páginas, ainda sem divisão em trechos ou indexação.

## 4. Pré-condições

- Ambiente sincronizado com as dependências de desenvolvimento.
- Pasta de entrada acessível, contendo PDFs locais.
- Acesso autorizado aos pacotes necessários à instalação da biblioteca de PDF. A execução da ingestão e dos testes deve funcionar offline.

## 5. Escopo

- Ler PDFs diretamente da pasta configurada, sem busca recursiva.
- Extrair texto por página e montar os metadados de origem.
- Retornar relatório de arquivos e páginas processados ou não processados.
- Expor a ingestão pela CLI e documentar seu uso.
- Criar testes com PDFs sintéticos claramente identificados como fictícios.

## 6. Fora do escopo

OCR, descriptografia de PDFs, divisão em trechos, embeddings, índice vetorial, consultas ao modelo, respostas acadêmicas e cadastro de vigência ou aplicabilidade das normas. Não persistir textos extraídos nesta etapa.

## 7. Requisitos funcionais

- **RF-01:** Usar `Settings.documents_dir` como pasta padrão e permitir substituí-la na CLI. Considerar arquivos com extensão `.pdf`, sem distinguir maiúsculas de minúsculas, em ordem determinística.
- **RF-02:** Produzir um `Document` por página com texto não vazio, sem unir páginas. Normalizar a página física uma única vez, começando em 1.
- **RF-03:** Preservar o texto devolvido pelo extrator, incluindo números, negações e condições. Não aplicar limpeza que altere seu conteúdo.
- **RF-04:** Identificar o documento pelo caminho relativo à pasta de entrada e registrar o hash SHA-256 dos bytes do PDF. Mudança de conteúdo no mesmo caminho mantém o identificador e altera o hash; renomeação representa outro documento nesta etapa.
- **RF-05:** Informar PDFs inválidos, protegidos, sem páginas ou sem texto extraível. Nenhuma página vazia deve ser produzida como evidência.
- **RF-06:** Em PDFs parcialmente extraíveis, retornar as páginas aproveitáveis e listar os números físicos e motivos das páginas não processadas. Não declarar processamento completo.
- **RF-07:** Falha em um arquivo não deve impedir o processamento dos demais. O relatório deve preservar o problema de cada arquivo.
- **RF-08:** A CLI deve apresentar resumo de arquivos, páginas aproveitadas e problemas, sem imprimir textos completos por padrão e sem alterar os PDFs originais.

## 8. Requisitos técnicos

- **RT-01:** Implementar a extração em módulo próprio, separado da CLI e da configuração.
- **RT-02:** Usar `langchain_core.documents.Document`, já disponível no projeto.
- **RT-03:** Adicionar apenas uma biblioteca de leitura de PDF adequada à extração por página e ao tratamento de arquivos protegidos; verificar sua documentação oficial e compatibilidade com Python 3.10 na implementação.
- **RT-04:** Declarar a dependência em `pyproject.toml` e atualizar `uv.lock` pelo uv. Não adicionar pacote amplo de integrações apenas para obter um leitor de PDF.
- **RT-05:** Usar funções pequenas, type hints e estruturas simples para o resultado. Não capturar exceções genericamente para simular sucesso.
- **RT-06:** Testes sem rede, credenciais ou provedor de modelos. Fixtures sintéticas podem ser versionadas em `tests/fixtures/`.

## 9. Modelo e contratos

A operação de ingestão recebe uma pasta e retorna páginas extraídas e um relatório por arquivo. Usar estruturas simples e tipadas, sem hierarquia de classes.

Cada página deve conter `page_content` com o texto extraído e estes metadados:

| Campo | Contrato |
| --- | --- |
| `document_id` | Identificador determinístico baseado no caminho relativo normalizado; independente do conteúdo |
| `document_name` | Nome do arquivo, incluindo a extensão, exibido como identificação legível |
| `document_hash` | SHA-256 do PDF original |
| `page_number` | Página física do PDF, começando em 1 |

`document_name` não deve ser apresentado como título institucional inferido. Numeração impressa não será inferida. `chunk_id` será introduzido na etapa de divisão em trechos.

O relatório deve distinguir arquivos completos, parciais e rejeitados; informar total de páginas quando conhecido, páginas aproveitadas, páginas não processadas com motivos e problemas de arquivo. Páginas em branco também entram no relatório; ausência de texto não comprova que uma página seja digitalizada.

Comando implementado e verificado:

```bash
uv run --locked python -m academic_assistant ingest --documents-dir data/documents
```

Sem `--documents-dir`, usar a configuração padrão. Código de saída 0 indica processamento completo; 1 indica arquivo rejeitado ou processamento parcial; 2 indica pasta inválida, ausência de PDFs ou argumento inválido. Preservar `--help` e `--version` existentes.

## 10. Tratamento de erros

- Pasta inexistente, caminho que não seja diretório, pasta inacessível ou ausência de PDFs: mensagem objetiva e status de falha.
- Arquivo ilegível, PDF inválido ou protegido: rejeitar o arquivo e registrar a causa sem expor seu conteúdo.
- Página sem texto ou falha de extração recuperável por página: registrar número e motivo, preservando as demais páginas extraíveis.
- Se a biblioteca não permitir continuar após uma falha de leitura, registrar a rejeição do arquivo, sem declarar suas páginas como processadas.
- PDF sem nenhuma página aproveitável: rejeitar e indicar que páginas digitalizadas podem exigir OCR, sem afirmar essa causa sem evidência.

## 11. Arquivos afetados

- `src/academic_assistant/ingestion.py`
- `src/academic_assistant/__main__.py`
- `tests/test_ingestion.py`
- `tests/test_bootstrap.py`, se necessário para compatibilidade da CLI
- `tests/fixtures/`
- `pyproject.toml` e `uv.lock`
- `README.md`
- `specs/004-ingestao-pdfs-por-pagina.md`

Mudanças fora desta lista exigem justificativa dentro do escopo desta spec.

## 12. Estratégia de testes

Usar PDFs sintéticos de múltiplas páginas com textos diferentes e regras explicitamente fictícias. Verificar extração, página física, metadados, estabilidade do identificador, mudança do hash e preservação dos bytes originais.

Cobrir PDF protegido, inválido, sem texto, sem páginas e parcialmente extraível, além de pasta inválida, pasta sem PDFs e lote misturando arquivos válidos e inválidos. Confirmar resumo e códigos de saída da CLI. Simulações locais podem complementar falhas de leitura difíceis de reproduzir; a extração principal deve ser testada com PDFs reais sintéticos.

## 13. Critérios de aceite

- **CA-01:** PDF sintético de múltiplas páginas retorna texto por página, sem mistura de origens, com todos os metadados corretos.
- **CA-02:** Identificador permanece estável ao alterar o conteúdo no mesmo caminho, hash muda e PDFs originais permanecem intactos.
- **CA-03:** Arquivos inválidos, protegidos ou sem texto são informados; processamento parcial lista as páginas não aproveitadas.
- **CA-04:** CLI utiliza pasta padrão ou personalizada, apresenta resumo correto e retorna os códigos definidos, inclusive em lote misto.
- **CA-05:** Testes de ingestão e bootstrap passam com `uv run --extra dev --locked pytest`, sem rede ou credenciais.
- **CA-06:** README contém dependência escolhida, convenção de páginas, política de identificação, limitações e comando de ingestão executado e verificado.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Testes relevantes implementados e aprovados
- [x] Instalação e ingestão pela CLI verificadas com PDF sintético
- [x] Nenhum item fora do escopo implementado
- [x] README e lockfile atualizados

O item de build Maven do template foi adaptado à instalação e execução da aplicação Python.

Evidências da execução:

- Dependência escolhida: pypdf 6.x, versão instalada 6.19.0, API `PdfReader.pages` e `extract_text()`. Instalação e atualização do lockfile realizadas pelo desenvolvedor após bloqueio de DNS no ambiente do assistente.
- `uv run --extra dev --locked --offline pytest -q`: 16 testes aprovados, incluindo bootstrap, PDFs sintéticos reais, falhas simuladas de leitura e códigos da CLI.
- `uv run --locked --offline python -m academic_assistant ingest --documents-dir .`: código 0, dois documentos completos, 9 páginas cada e 18 páginas aproveitadas.
- Metadados e páginas físicas 1–9 verificados nos dois documentos. Hashes originais preservados: `doc1.pdf` = `9e90b9119bb5025ae3360ce93f30e9c48b61bf619dc74fded53a6f13bd020f40`; `doc2.pdf` = `00aad6a9e7e6bcb7d1bee66040c6d51742528dee7147582d8a6f08686ca8259c`.
- Textos das páginas idênticos entre os dois PDFs, mantendo identificadores distintos por caminho conforme o contrato desta etapa.
- `uv lock --check --offline`: código 0, 49 pacotes; `git diff --check`: sem problemas.

## 15. Critério de parada

Encerrar quando PDFs puderem ser extraídos por página, com metadados verificáveis e problemas reportados, e os seis critérios de aceite passarem. Divisão em trechos, embeddings, persistência do índice e respostas ficam para SPECs futuras. Esta entrega não valida o RAG de ponta a ponta.
