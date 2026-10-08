# Assistente de Regulamentos Acadêmicos

Aplicação em Python e LangChain para preparar documentos locais de um futuro assistente de consulta a regulamentos acadêmicos. As primeiras entregas incluem ambiente reproduzível, CLI, testes e ingestão de PDFs por página.

## Requisitos

- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) 0.12 ou superior
- Python 3.10, instalado localmente ou disponibilizado pelo `uv`

## Instalação

O `uv.lock` está incluído no repositório. Sincronize o ambiente com as versões registradas no lockfile:

```bash
uv sync --extra dev --locked
```

O `uv` cria `.venv` e instala o pacote em modo editável, LangChain e as dependências de teste. Não é necessário ativar o ambiente ou ter `ensurepip` instalado.

Por padrão, os pacotes são obtidos do PyPI. Em uma rede que utiliza outro índice PEP 503, informe-o somente pelo ambiente:

```bash
UV_DEFAULT_INDEX=https://packages.example.edu/simple uv lock
UV_DEFAULT_INDEX=https://packages.example.edu/simple uv sync --extra dev --locked
```

Substitua a URL de exemplo pelo índice autorizado. Não inclua credenciais no comando, no README ou em arquivos versionados. Ao trocar de índice, confira as origens do lockfile; alterar a variável não garante o redirecionamento de URLs já registradas. Depois de uma sincronização completa, é possível reutilizar o cache local sem acessar o índice:

```bash
uv sync --extra dev --locked --offline
```

## CLI

Exiba a ajuda ou a versão instalada:

```bash
uv run --locked python -m academic_assistant --help
uv run --locked python -m academic_assistant --version
```

## Estrutura e responsabilidades

```text
assistente-ifma/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── uv.lock
├── uv.toml
├── .python-version
├── .gitignore
├── .skill-index/              # perfil auxiliar do projeto
├── specs/                     # especificações numeradas e template
├── src/academic_assistant/
│   ├── __init__.py             # metadados e versão
│   ├── __main__.py             # entrada do pacote e reexportações da CLI
│   ├── cli.py                  # argumentos, despacho e relatório
│   ├── config.py               # Settings, sem criar pastas
│   └── ingestion.py            # extração por página e relatórios
├── tests/                     # testes offline com PDFs sintéticos temporários
└── data/
    ├── documents/
    │   ├── .gitkeep
    │   └── *.pdf              # documentos locais ignorados pelo Git
    └── index/
        └── .gitkeep           # reservado ao índice futuro
```

Os marcadores mantêm as pastas no checkout. Para cadastrar documentos, coloque os PDFs diretamente em `data/documents/` e execute `ingest` a partir da raiz. Um checkout sem PDFs retorna código 2: `.gitkeep` não é um documento. Imports e configuração não criam pastas; os caminhos padrão continuam relativos ao diretório de execução.

Documentos PDF, conteúdo das pastas de dados (inclusive subpastas), `.env` e variantes locais, ambiente virtual e caches são ignorados pelo Git. Apenas os marcadores das pastas de dados são versionáveis; um futuro `.env.example` também poderá ser versionado. Esta etapa não precisa de variáveis de ambiente da aplicação.

## Configuração

A classe `Settings` usa estes caminhos, relativos ao diretório em que o processo é executado:

- documentos: `data/documents/`
- índice: `data/index/`

Os caminhos podem ser substituídos ao construir a configuração. A construção de `Settings` não cria nem lê essas pastas; o comando de ingestão lê a pasta selecionada.

## Ingestão de PDFs

A SPEC-004 implementa a leitura com `pypdf` 6.x e retorna um `Document` LangChain por página com texto aproveitável. A extração segue a [documentação oficial de pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html). O texto extraído é preservado sem limpeza adicional. Esta etapa não envia conteúdo para serviços externos.

Coloque os PDFs em `data/documents/` ou selecione outra pasta. Apenas PDFs diretamente nela são lidos, em ordem determinística; subpastas são ignoradas. Os arquivos originais permanecem intactos.

Use a pasta padrão ou uma pasta personalizada:

```bash
uv run --locked python -m academic_assistant ingest
uv run --locked python -m academic_assistant ingest --documents-dir /caminho/para/pdfs
```

O segundo comando lê uma pasta personalizada sem copiar ou mover seus arquivos. O resumo informa arquivos completos, parciais ou rejeitados e lista páginas não aproveitadas; não imprime os textos por padrão.

Os PDFs locais `doc1.pdf` e `doc2.pdf` foram movidos para `data/documents/`, preservando nomes e hashes. A ingestão pela pasta padrão aproveitou 9 páginas em cada arquivo (18 no total), sem modificar os originais. Os identificadores continuam sendo `doc1.pdf` e `doc2.pdf`; não há deduplicação por texto.

Cada página retorna `document_id` (caminho relativo à pasta), `document_name` (nome real do arquivo), `document_hash` (SHA-256 dos bytes originais) e `page_number` (página física do PDF começando em 1). A numeração impressa não é inferida. Alterar o arquivo no mesmo caminho mantém seu identificador; renomeá-lo cria outro identificador. O hash identifica conteúdo, não vigência ou aplicabilidade.

Arquivos protegidos, inválidos, sem páginas ou sem texto são rejeitados. Páginas sem texto ou com falha de extração são reportadas; as demais páginas podem ser aproveitadas. Ausência de texto não comprova digitalização; páginas digitalizadas podem exigir OCR, que ainda não está disponível.

Código de saída 0 significa processamento completo; 1 indica rejeição ou processamento parcial; 2 indica pasta inválida, ausência de PDFs ou argumento inválido. A biblioteca pode emitir avisos técnicos de leitura de PDFs danificados.

O núcleo expõe `ingest_documents(Path(...))` em `academic_assistant.ingestion`, com `pages` e `reports` no resultado. Nenhum texto extraído é persistido nesta etapa. Mantenha documentos privados fora do versionamento; PDFs em `data/documents/` já são ignorados pelo Git.

## Testes

Execute pelo ambiente sincronizado:

```bash
uv run --extra dev --locked --offline pytest -q
```

## Estado da verificação

Bootstrap validado com uv 0.12.11, CPython 3.10.12 e pytest 8.4.2. O desenvolvedor gerou o lockfile e executou a instalação inicial com sucesso. O assistente confirmou os imports reais, os cinco testes pelo pytest, ajuda, versão e rejeição de argumento inválido na CLI.

Uma nova instalação em ambiente vazio funcionou offline usando o cache aquecido. Lockfiles ausentes ou incompatíveis foram rejeitados por `--locked`, e o lockfile original permaneceu inalterado.

As SPEC-001, SPEC-002 e SPEC-003 estão concluídas. A primeira instalação exige acesso aos pacotes; os downloads foram realizados no terminal do desenvolvedor.

A SPEC-004 também está concluída, com pypdf 6.19.0 e 16 testes aprovados por `uv run --extra dev --locked --offline pytest -q`. A ingestão dos dois PDFs reais retornou código 0; páginas físicas 1–9 e metadados foram conferidos em cada arquivo. Os hashes anteriores e posteriores confirmaram que os PDFs originais permaneceram intactos. O lockfile atualizado contém 49 pacotes e passou em `uv lock --check --offline`.

A SPEC-005 está concluída: CLI separada com compatibilidade dos imports, pastas de dados com marcadores, PDFs locais movidos com hashes preservados e exclusões do Git verificadas. Os 22 testes passaram offline; a ingestão pela pasta padrão retornou código 0 e 18 páginas. Dependências e lockfile permaneceram inalterados.

## Funcionalidades pendentes

Divisão em trechos, embeddings, persistência do índice vetorial, recuperação, geração, prompts e validação de respostas ficam para SPECs posteriores. Seus módulos ainda não existem; não há comandos de indexação ou consulta disponíveis. Provedor de modelo e armazenamento vetorial ainda não foram escolhidos. A extração não garante que o corpus contenha regulamentos acadêmicos aplicáveis: a seleção dos documentos e de seu contexto ainda deve ser feita antes das consultas.
