# SPEC-005 — Organização da estrutura do projeto

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-001, SPEC-002, SPEC-003 e SPEC-004 concluídas.
- **Entrega:** Estrutura de código, dados locais e testes organizada e documentada, preservando a CLI e o contrato de ingestão existentes.

## 2. Objetivo

Organizar o projeto para receber as próximas etapas do RAG sem misturar interface, processamento e dados locais. Tornar explícito onde cada responsabilidade pertence e permitir a ingestão pela pasta padrão, mantendo o comportamento já implementado.

## 3. Contexto

O pacote já utiliza o layout `src/academic_assistant/`, com configuração em `config.py` e extração em `ingestion.py`. A interface e a apresentação do relatório estão em `__main__.py`. Os testes estão separados em `tests/`, e instalação e dependências são gerenciadas por `pyproject.toml` e `uv.lock`.

Os caminhos padrão são `data/documents/` e `data/index/`, mas essas pastas ainda não estão presentes. Os PDFs locais `doc1.pdf` e `doc2.pdf` estão na raiz; o README orienta processá-los com `--documents-dir .`. O `.gitignore` ignora os dados nas pastas padrão, mas não esses PDFs da raiz nem permite marcadores das pastas.

A organização deve seguir [AGENTS.md](../AGENTS.md) e reaproveitar a estrutura existente. Esta spec organiza o incremento já disponível; não implementa as etapas restantes do RAG.

## 4. Pré-condições

- Ambiente com as dependências de desenvolvimento sincronizadas pelo uv.
- Implementação e testes da SPEC-004 disponíveis.
- Conferência das alterações locais antes de mover arquivos, preservando o trabalho do usuário.
- Registro dos hashes dos PDFs locais antes da movimentação, sem incluir seu conteúdo na documentação ou nos logs.

## 5. Escopo

- Extrair a interface de linha de comando para `cli.py` e manter `__main__.py` como ponto de entrada mínimo.
- Preservar os módulos de configuração e ingestão e suas interfaces públicas.
- Criar as pastas de documentos e índice com marcadores versionáveis.
- Mover os PDFs locais da raiz para a pasta padrão, sem modificar seus bytes nem versioná-los.
- Ajustar as regras de exclusão do Git para dados locais e segredos.
- Atualizar os testes afetados pela separação da CLI.
- Documentar no README a estrutura atual, as responsabilidades e o fluxo após a organização.

## 6. Fora do escopo

Divisão em trechos, embeddings, persistência de índice, recuperação, geração, validação de respostas, escolha de provedores, OCR, interface web, CI e novas dependências. Não criar módulos vazios para funcionalidades futuras, camadas genéricas, contêiner de injeção de dependências ou uma hierarquia de classes.

Não modificar PDFs, deduplicar documentos por texto, inferir aplicabilidade de normas nem reorganizar o histórico das SPECs anteriores. Não criar `.env.example` enquanto nenhuma variável de ambiente da aplicação for necessária.

## 7. Requisitos funcionais

- **RF-01:** Preservar a execução por `python -m academic_assistant`, incluindo ajuda, versão, subcomando `ingest`, opção `--documents-dir`, saída sem subcomando e rejeição de argumentos inválidos.
- **RF-02:** Manter o resumo, os relatórios de páginas e os códigos de saída: 0 para processamento completo, 1 para parcial ou rejeitado e 2 para pasta ou argumentos inválidos ou ausência de PDFs.
- **RF-03:** A pasta padrão de documentos deve existir no checkout mesmo sem PDFs versionados. Seu marcador não deve ser tratado como documento pela ingestão.
- **RF-04:** Mover `doc1.pdf` e `doc2.pdf`, quando presentes, para `data/documents/`, preservando os nomes e os hashes. Não sobrescrever um arquivo já existente no destino.
- **RF-05:** Continuar aceitando uma pasta personalizada sem copiar ou mover automaticamente seus documentos. Imports e construção de `Settings` não devem criar diretórios.
- **RF-06:** PDFs locais, conteúdo do índice, credenciais e caches devem permanecer fora do versionamento. Os marcadores das pastas devem poder ser versionados.
- **RF-07:** O README deve apresentar a árvore implementada e comandos coerentes com ela, distinguindo funcionalidades existentes das pendentes.

## 8. Requisitos técnicos

- **RT-01:** Manter o pacote `academic_assistant`, o layout `src/`, Python 3.10+, setuptools, uv e pytest. Não alterar dependências nem regenerar o lockfile para uma reorganização sem mudanças de dependências.
- **RT-02:** Concentrar parsing, despacho dos comandos e apresentação do relatório em `cli.py`. `__main__.py` deve apenas encaminhar a execução a `main` e propagar o código de saída.
- **RT-03:** Preservar a possibilidade atual de importar `main` e `build_parser` de `academic_assistant.__main__` por reexportação simples, sem duplicar a implementação. Os testes podem passar a usar `academic_assistant.cli` diretamente.
- **RT-04:** Manter `config.py` responsável pela configuração e `ingestion.py` pela extração e pelos relatórios, sem dependência do núcleo na CLI.
- **RT-05:** Manter os caminhos padrão relativos ao diretório de execução. Não passar a resolvê-los em relação ao arquivo Python ou à raiz descoberta do repositório.
- **RT-06:** Usar `.gitkeep` nas duas pastas de dados e exceções explícitas no `.gitignore`. Ignorar recursivamente seus demais conteúdos, inclusive subpastas, e proteger `.env` e variantes locais sem impedir um futuro `.env.example`.
- **RT-07:** Manter testes offline, com arquivos temporários e PDFs sintéticos. Os PDFs locais do usuário não devem ser fixtures nem pré-condição dos testes automatizados.

## 9. Modelo e contratos

Estrutura esperada após a implementação:

```text
assistente-ifma/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── uv.lock
├── uv.toml
├── .python-version
├── .gitignore
├── specs/
│   ├── SPEC-TEMPLATE.md
│   └── 001-...md a 005-...md
├── src/
│   └── academic_assistant/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       └── ingestion.py
├── tests/
│   ├── test_bootstrap.py
│   └── test_ingestion.py
└── data/
    ├── documents/
    │   ├── .gitkeep
    │   └── arquivos PDF locais (ignorados pelo Git)
    └── index/
        └── .gitkeep
```

Arquivos e diretórios auxiliares existentes, como `.skill-index/`, permanecem preservados. `.venv/` e caches continuam locais e ignorados.

| Elemento | Responsabilidade e contrato |
| --- | --- |
| `__init__.py` | Metadados do pacote e versão; sem inicialização de dados |
| `__main__.py` | Entrada de `python -m academic_assistant` e compatibilidade dos imports existentes |
| `cli.py` | `build_parser()` e `main(argv: Sequence[str] | None = None) -> int`; argumentos, despacho e apresentação em português |
| `config.py` | `Settings`, com os mesmos caminhos padrão e sem efeitos no sistema de arquivos |
| `ingestion.py` | `ingest_documents(Path) -> IngestionResult`, tipos de relatório e `IngestionError`; sem apresentação da CLI |
| `tests/` | Testes offline e documentos sintéticos gerados em diretórios temporários |
| `data/documents/` | PDFs de entrada locais; originais preservados e não versionados |
| `data/index/` | Local reservado ao índice futuro; nesta etapa contém apenas o marcador |
| `specs/` | Especificações numeradas e template, sem renomear entregas anteriores |

A movimentação dos dois PDFs deve manter `document_id` como `doc1.pdf` e `doc2.pdf`: ambos continuam diretamente na pasta selecionada, e o identificador é relativo a essa pasta. `document_name`, `document_hash`, `page_number`, texto extraído e relatórios permanecem com o contrato da SPEC-004.

As responsabilidades futuras de divisão, indexação, recuperação, geração e prompts devem ser descritas como pendentes no README. Seus módulos serão criados somente quando houver implementação nas próximas specs.

## 10. Tratamento de erros

- Se houver arquivo homônimo no destino, interromper a movimentação desse arquivo e informar a colisão; não sobrescrever nem apagar nenhuma cópia.
- Se uma movimentação falhar, informar a origem e o destino e conferir quais arquivos foram movidos. Não afirmar que a reorganização dos dados terminou.
- Se o hash após a movimentação divergir, tratar a migração como falha e preservar os arquivos disponíveis para investigação, sem limpeza automática.
- Se os PDFs locais não estiverem presentes, registrar que essa verificação não foi executada; a estrutura e os testes sintéticos ainda devem funcionar.
- Pasta padrão vazia deve continuar produzindo o erro de ausência de PDFs e código 2, sem gerar documentos vazios a partir de `.gitkeep`.
- Falhas da ingestão devem manter o tratamento próprio da SPEC-004; a separação da CLI não pode convertê-las em sucesso.

## 11. Arquivos afetados

- `src/academic_assistant/cli.py` — novo módulo de interface.
- `src/academic_assistant/__main__.py` — delegação e reexportações.
- `tests/test_bootstrap.py` e `tests/test_ingestion.py` — ajustes de imports e verificações de compatibilidade, quando necessários.
- `data/documents/.gitkeep` e `data/index/.gitkeep` — novos marcadores.
- `doc1.pdf` e `doc2.pdf` — movimentação local para `data/documents/`, sem inclusão no Git.
- `.gitignore` — proteção de dados, segredos e exceções dos marcadores.
- `README.md` — mapa da estrutura, cadastro de PDFs e comandos atualizados.
- `specs/005-organizacao-da-estrutura-do-projeto.md` — estado e evidências após implementação.

Mudanças fora desta lista exigem justificativa dentro do escopo. `config.py`, `ingestion.py`, manifests, lockfile e alterações pré-existentes devem ser preservados quando não houver necessidade concreta de ajuste.

## 12. Estratégia de testes

Executar a suíte existente pelo ambiente travado: `uv run --extra dev --locked --offline pytest -q`. Ajustar apenas os testes afetados e verificar a delegação pelo ponto de entrada real, além de `main` diretamente. Não criar testes que apenas confiram nomes de pastas ou reproduzam a árvore.

Confirmar ajuda, versão, ausência de subcomando, argumentos inválidos, ingestão com pasta padrão e personalizada, resumo e códigos 0, 1 e 2. Reutilizar os casos sintéticos da SPEC-004, acrescentando cobertura somente para lacunas introduzidas pela reorganização. Usar diretório temporário como diretório de execução para testar os caminhos relativos e uma pasta contendo somente `.gitkeep`.

Para os PDFs locais disponíveis, comparar hashes antes e depois, conferir os identificadores e executar a ingestão sem `--documents-dir` a partir da raiz. Esta conferência é separada dos testes automatizados e não valida a aplicabilidade acadêmica dos documentos.

Verificar as exclusões com `git check-ignore`, usando caminhos representativos de PDFs, subpastas do índice, segredos e caches. Confirmar que os marcadores não são ignorados e revisar `git status --short` e `git diff --check`, incluindo a nova spec. Não adicionar arquivos ao staging nem remover dados para realizar essas verificações.

## 13. Critérios de aceite

- **CA-01:** A CLI reside em `cli.py`; a execução pelo pacote e os imports anteriores de `main` e `build_parser` continuam funcionando.
- **CA-02:** Argumentos, textos relevantes, relatórios e códigos de saída mantêm o comportamento existente, com os testes de bootstrap e ingestão aprovados offline.
- **CA-03:** As duas pastas de dados possuem marcadores versionáveis; seus demais conteúdos, inclusive em subpastas, permanecem ignorados pelo Git.
- **CA-04:** Os PDFs locais presentes foram movidos sem colisões, preservando nomes, hashes e identificadores, e a ingestão usa a pasta padrão. Ausência ou impedimento deve ser registrado como limitação, sem declarar a movimentação concluída.
- **CA-05:** A construção de `Settings` e os imports continuam sem criar pastas; pastas personalizadas e pasta padrão sem PDFs mantêm seus contratos.
- **CA-06:** README descreve a estrutura implementada, as responsabilidades e o fluxo de cadastro e ingestão, sem apresentar o RAG futuro como disponível.
- **CA-07:** Não foram adicionados provedores, dependências, módulos vazios ou funcionalidades fora do escopo; alterações pré-existentes foram preservadas.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Testes relevantes aprovados offline pelo uv
- [x] CLI verificada pelo ponto de entrada do pacote
- [x] Dados locais conferidos e exclusões do Git verificadas
- [x] Nenhum item fora do escopo implementado
- [x] README atualizado e limitações reais registradas
- [x] Evidências de verificação registradas nesta spec antes de alterar seu estado

O item de build Maven do template foi adaptado às verificações da aplicação Python. A geração desta especificação não conclui sua implementação nem comprova os critérios de aceite.

## 15. Critério de parada

Encerrar a implementação quando a estrutura estiver organizada, a compatibilidade da ingestão estiver verificada e os critérios de aceite estiverem atendidos. Qualquer impedimento na movimentação dos dados deve permanecer explicitamente registrado. Divisão em trechos e as demais etapas do RAG ficam para specs posteriores; esta entrega não valida o MVP de ponta a ponta.


## 16. Evidências de execução — 2026-10-08

- CLI extraída para `cli.py`; `__main__.py` delega e reexporta `main` e `build_parser`. Configuração, ingestão, dependências e lockfile preservados.
- `uv run --extra dev --locked --offline pytest -q`: **22 testes aprovados**. Incluem entrada real pelo pacote, ajuda, versão, ausência de subcomando, argumento inválido, compatibilidade dos imports, pastas padrão e personalizada, marcador sem PDFs e códigos 0, 1 e 2. Apenas PDFs sintéticos temporários nos testes.
- `uv run --extra dev --locked --offline python -m academic_assistant ingest`: código **0**, dois arquivos completos e **18 páginas aproveitadas** (9 por arquivo), pela pasta padrão.
- `doc1.pdf` movido para `data/documents/doc1.pdf`; SHA-256 antes, depois e após ingestão: `9e90b9119bb5025ae3360ce93f30e9c48b61bf619dc74fded53a6f13bd020f40`.
- `doc2.pdf` movido para `data/documents/doc2.pdf`; SHA-256 antes, depois e após ingestão: `00aad6a9e7e6bcb7d1bee66040c6d51742528dee7147582d8a6f08686ca8259c`.
- Sem colisões. Metadados conferidos sem imprimir textos: identificadores e nomes `doc1.pdf` e `doc2.pdf`, hashes correspondentes e páginas físicas 1–9 em cada arquivo.
- Pastas de dados criadas com `.gitkeep`. `git check-ignore --no-index` confirmou PDFs, conteúdo em subpastas dos dados, `.env`, variantes locais e caches ignorados; marcadores e futuro `.env.example` não ignorados.
- Os PDFs estavam previamente adicionados ao staging. Apenas esses caminhos foram retirados com `git restore --staged -- doc1.pdf doc2.pdf` para proteger dados locais; originais preservados no destino. Nenhum arquivo adicionado ao staging; demais alterações pré-existentes preservadas.
- `git diff --check` sem problemas desta entrega; novos arquivos conferidos por `git diff --no-index --check`. `git status --short` revisado. A conferência adicional `git diff --cached --check` aponta linhas em branco no fim de `__init__.py` e `config.py` já presentes no staging antes desta tarefa; arquivos preservados conforme o escopo.
- README atualizado com estrutura, responsabilidades, cadastro, comandos e pendências. Sem novas dependências, provedores ou módulos futuros vazios.
- Nenhum impedimento na movimentação dos dados. Esta entrega não valida o MVP RAG de ponta a ponta.
