# Relatório de progresso — Assistente de Regulamentos Acadêmicos

**Projeto:** assistente-ifma

**Data de referência:** 8 de outubro de 2026

**Versão da aplicação:** 0.1.0

**Escopo analisado:** entregas SPEC-001 a SPEC-005

**Commit de referência:** `cd99297` — `feat: implementa ingestão de PDFs e organiza estrutura do projeto`

**Finalidade:** apresentar ao professor o trabalho realizado, as decisões técnicas, a organização do código e as evidências de funcionamento.

## 1. Visão geral do trabalho realizado

O projeto pretende oferecer um assistente que responda, em português, a perguntas sobre regulamentos acadêmicos usando documentos institucionais como evidência. As respostas futuras deverão indicar documento, página física do PDF e trecho que sustenta cada afirmação. Quando os documentos não oferecerem suporte suficiente, o assistente deverá comunicar essa limitação.

Até esta entrega, foi construída e verificada a base de desenvolvimento e a primeira etapa de processamento documental: **a ingestão local de PDFs com extração de texto por página e preservação de metadados de origem**.

A aplicação já pode ser instalada como pacote Python, executada pelo terminal e utilizada para processar uma pasta de PDFs. Ela informa quais documentos foram processados integralmente, quais foram aproveitados parcialmente e quais foram rejeitados. A extração utiliza bibliotecas reais e foi testada com PDFs sintéticos e dois arquivos locais.

O resultado atual pode ser descrito como uma base funcional para o futuro RAG. Ainda não há indexação vetorial, busca por perguntas, integração com um modelo de linguagem ou geração de respostas acadêmicas. Portanto, os resultados apresentados neste relatório demonstram a qualidade da instalação, da estrutura e da ingestão, sem representar uma validação completa do assistente final.

### 1.1. Resultados principais

| Item | Resultado obtido |
| --- | --- |
| Organização das entregas | Cinco especificações concluídas, com critérios de aceite e evidências |
| Pacote da aplicação | `academic_assistant`, versão 0.1.0 |
| Ambiente reproduzível | `pyproject.toml`, `uv.lock`, `.python-version` e `uv.toml` |
| Interface disponível | CLI com ajuda, versão e comando `ingest` |
| Processamento | Extração local por página com `pypdf` |
| Integração com LangChain | Uso de `langchain_core.documents.Document` para representar cada página |
| Rastreabilidade | Identificador, nome, hash SHA-256 e página física para cada página aproveitada |
| Testes automatizados | 22 testes aprovados offline na validação da SPEC-005 |
| Verificação com arquivos locais | Dois PDFs completos, 9 páginas por arquivo, 18 páginas aproveitadas |
| Integridade dos originais | Hashes preservados antes e depois da movimentação e ingestão |
| Versionamento | Código e documentação registrados; PDFs locais excluídos do commit |

## 2. Problema e requisitos do produto

Perguntas sobre frequência mínima, segunda chamada, trancamento ou aproveitamento de disciplinas exigem atenção ao documento aplicável, às condições e às exceções. Uma resposta baseada apenas em conhecimento geral de um modelo pode atribuir ao IFMA uma regra de outra instituição ou apresentar como universal uma norma que depende de curso, modalidade ou período.

O `AGENTS.md` registra os requisitos que devem orientar o assistente:

1. Usar Python e LangChain em um RAG simples.
2. Responder perguntas em linguagem natural sobre documentos cadastrados.
3. Fundamentar afirmações sobre regras acadêmicas nas evidências recuperadas.
4. Apresentar fontes verificáveis, com documento, página e excerto.
5. Preservar condições, exceções e conflitos entre documentos.
6. Comunicar quando não houver evidências suficientes.
7. Distinguir ausência de evidência de erros técnicos.

O arquivo de instruções não define percentuais, prazos ou procedimentos acadêmicos. Esses dados deverão ser obtidos dos regulamentos selecionados. Este relatório também não atribui regras acadêmicas aos PDFs locais.

### 2.1. Relação da ingestão com o RAG

RAG significa *Retrieval-Augmented Generation*, ou geração aumentada por recuperação. No fluxo previsto, os documentos serão divididos em trechos, representados por embeddings, armazenados em um índice e recuperados conforme a pergunta. O modelo receberá as evidências e produzirá a resposta com referências.

O estágio atual e as etapas previstas podem ser visualizados assim:

```text
IMPLEMENTADO
Pasta local de PDFs
        ↓
Seleção e leitura dos arquivos
        ↓
Extração de texto por página
        ↓
Document LangChain + metadados de origem
        ↓
Relatório de processamento pela CLI

PENDENTE
Páginas extraídas
        ↓
Divisão em trechos
        ↓
Embeddings e persistência do índice
        ↓
Recuperação de evidências para uma pergunta
        ↓
Geração e validação da resposta
        ↓
Resposta com documento, página e excerto
```

A preservação da origem na ingestão é necessária para que as futuras citações possam ser montadas pela aplicação a partir de dados reais, sem depender da criação de nomes ou números de página pelo modelo.

## 3. Evolução por especificação

### 3.1. SPEC-001 — Bootstrap do projeto

A primeira entrega estabeleceu a base mínima da aplicação:

- Pacote Python no layout `src/academic_assistant/`.
- Declaração de dependências e versão em `pyproject.toml`.
- Entrada por `python -m academic_assistant`.
- Ajuda, versão e rejeição de argumentos desconhecidos.
- Configuração simples dos caminhos de documentos e índice.
- Testes iniciais e documentação de uso.

O objetivo foi obter um projeto instalável e verificável antes de implementar o processamento documental. A conclusão das verificações de instalação ocorreu durante a SPEC-003.

### 3.2. SPEC-002 — Ambiente reproduzível com uv

A segunda entrega padronizou instalação e execução com `uv`, mantendo um único fluxo principal de dependências. Foram estabelecidos:

- Python 3.10 como versão selecionada em `.python-version`.
- Compatibilidade declarada com Python 3.10 ou superior.
- Cache local em `.cache/uv`.
- `uv.lock` para registrar a resolução das dependências.
- Uso de `--locked` para evitar atualização silenciosa do lockfile.
- Uso explícito de `--extra dev` nos comandos de teste.
- Possibilidade de sincronização offline após disponibilizar os pacotes no cache.

As verificações desta entrega foram concluídas com a resolução do acesso aos pacotes na SPEC-003.

### 3.3. SPEC-003 — Desbloqueio das dependências

O ambiente restrito de execução apresentou falhas de DNS ao acessar o PyPI e os arquivos dos pacotes. A falha foi registrada como uma limitação observada do ambiente, sem tratá-la automaticamente como erro do código ou incompatibilidade das dependências.

O desenvolvedor executou a geração do lockfile e a sincronização no seu terminal, onde o acesso aos pacotes estava disponível. Depois, foram verificadas no ambiente do assistente as importações reais, os testes e a CLI.

As evidências registradas incluem:

- Cinco testes iniciais aprovados.
- Imports reais de `academic_assistant`, `langchain`, `langchain_core` e `pytest`, sem uso de `PYTHONPATH=src`.
- Ajuda e versão com código 0; argumento desconhecido com código 2.
- Instalação em outro ambiente vazio usando cache aquecido e modo offline.
- Rejeição de lockfile ausente ou incompatível, em cópias temporárias do projeto.

Não foram alterados DNS, firewall ou configurações de rede para contornar o problema. Também não foram criadas dependências simuladas para substituir a instalação real.

### 3.4. SPEC-004 — Ingestão de PDFs por página

A quarta entrega implementou o primeiro processamento efetivo de documentos:

- Leitura de uma pasta local configurável.
- Seleção apenas de PDFs diretamente nessa pasta.
- Extração por página com `pypdf`.
- Um `Document` LangChain para cada página com texto aproveitável.
- Metadados de origem e SHA-256 dos bytes do PDF.
- Relatórios de páginas não aproveitadas e arquivos rejeitados.
- Subcomando `ingest` na CLI.
- Testes com PDFs reais sintéticos, além de simulações de falhas de leitura.

Na validação desta etapa, 16 testes passaram. Os dois PDFs locais foram processados com 9 páginas aproveitadas em cada arquivo. O lockfile passou a registrar 49 pacotes após a inclusão de `pypdf`.

### 3.5. SPEC-005 — Organização da estrutura

A quinta entrega separou a interface do núcleo de ingestão e organizou os dados locais:

- Parsing, despacho e apresentação transferidos para `cli.py`.
- `__main__.py` reduzido à delegação da execução.
- Imports anteriores de `main` e `build_parser` preservados por reexportação.
- Pastas `data/documents/` e `data/index/` criadas com `.gitkeep`.
- PDFs movidos da raiz para a pasta padrão, sem alteração de bytes.
- Exclusões do Git ampliadas para dados, PDFs e variantes locais de `.env`.
- README atualizado com estrutura, comandos e responsabilidades.
- Testes ampliados para a entrada real pelo pacote e a compatibilidade da reorganização.

Os 22 testes passaram offline. A ingestão pela pasta padrão retornou código 0 e aproveitou 18 páginas. Não foram alterados dependências, lockfile, configuração ou núcleo de extração nessa reorganização.

## 4. Decisões técnicas e suas implicações

As decisões abaixo estão refletidas no código, nos manifests e nas specs. As justificativas explicam sua adequação ao escopo atual.

| Decisão adotada | Justificativa e consequência |
| --- | --- |
| Python e LangChain | Atendem ao requisito do projeto; `Document` fornece uma representação comum para as etapas posteriores |
| Layout `src/` | Separa o pacote dos arquivos de documentação e dados; a verificação usa o pacote instalado |
| `uv` como fluxo principal | Centraliza sincronização, execução e controle das versões resolvidas |
| Setuptools como backend | Mantém o empacotamento declarado no projeto sem introduzir outra ferramenta de build |
| `argparse` para CLI | A biblioteca padrão cobre o fluxo atual sem dependência adicional |
| Dataclasses para configuração e relatórios | Representam contratos simples com campos explícitos e sem uma hierarquia extensa |
| `pypdf` para extração | Permite iterar páginas, extrair texto e identificar PDFs protegidos |
| `Document` por página | Preserva a associação entre o texto extraído e a página física do PDF |
| SHA-256 dos bytes originais | Identifica a versão de conteúdo processada e permite conferir integridade |
| Identificador relativo à pasta selecionada | Mantém identidade por caminho; mudar o conteúdo não muda o identificador |
| Leitura não recursiva | Torna explícito quais PDFs entram no lote e evita incluir subpastas automaticamente |
| Ordem determinística | Facilita reproduzir relatórios e comparar resultados |
| Texto sem limpeza adicional | Evita remoção própria de números, negações, condições ou referências importantes |
| Processamento local | A ingestão atual não exige chaves de API nem envia conteúdo a provedores externos |
| Testes sintéticos offline | Permitem validar o código sem depender de documentos privados, rede ou modelo pago |
| Implementação incremental | Módulos futuros serão criados quando suas funcionalidades forem implementadas |

Preservar o texto sem limpeza adicional significa manter o resultado de `extract_text()`. Isso não garante reprodução perfeita do layout visual do PDF: a qualidade da extração continua dependente do arquivo e da biblioteca.

Não foi escolhido provedor de LLM, modelo de embeddings ou armazenamento vetorial. Essas escolhas permanecem abertas para as próximas entregas.

## 5. Ambiente e dependências

### 5.1. Declaração das dependências

Trecho de `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "academic-assistant"
version = "0.1.0"
description = "Assistente de consulta a regulamentos acadêmicos"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "langchain>=1.0,<2.0",
    "langchain-core>=1.0,<2.0",
    "pypdf>=6,<7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8,<9",
]
```

O manifesto define as faixas compatíveis; o lockfile registra as versões resolvidas, incluindo dependências transitivas. Não existe um segundo fluxo principal baseado em `requirements.txt`.

| Componente | Versão registrada no lockfile atual |
| --- | --- |
| LangChain | 1.4.3 |
| LangChain Core | 1.6.7 |
| pypdf | 6.19.0 |
| pytest | 8.4.2 |

O ambiente registrado nas verificações anteriores utiliza uv 0.12.11 e CPython 3.10.12. O projeto exige uv 0.12.0 ou superior em `uv.toml`.

```toml
cache-dir = ".cache/uv"
required-version = ">=0.12.0"
```

`--locked` exige consistência com o lockfile. `--offline` exige que os artefatos necessários já estejam disponíveis localmente; a primeira instalação em uma máquina sem cache ainda depende de acesso aos pacotes.

## 6. Estrutura atual do projeto

A árvore abaixo apresenta a estrutura de código e documentação do commit de referência, além dos PDFs presentes localmente:

```text
assistente-ifma/
├── AGENTS.md
├── README.md
├── .gitignore
├── .python-version
├── .skill-index/
│   └── project-profile.json
├── pyproject.toml
├── uv.lock
├── uv.toml
├── specs/
│   ├── SPEC-TEMPLATE.md
│   ├── 001-bootstrap.md
│   ├── 002-ambiente-reproduzivel-com-uv.md
│   ├── 003-desbloqueio-dependencias.md
│   ├── 004-ingestao-pdfs-por-pagina.md
│   └── 005-organizacao-da-estrutura-do-projeto.md
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
    │   ├── doc1.pdf                  # local e ignorado
    │   └── doc2.pdf                  # local e ignorado
    └── index/
        └── .gitkeep                  # ainda sem índice implementado
```

O presente relatório é um artefato adicional de documentação, gerado após o commit de referência. `.venv/`, caches e arquivos gerados também podem existir localmente, mas permanecem ignorados.

### 6.1. Responsabilidades dos arquivos

| Caminho | Responsabilidade |
| --- | --- |
| `AGENTS.md` | Requisitos do assistente e convenções de desenvolvimento |
| `README.md` | Instalação, configuração, uso, verificações e limitações |
| `pyproject.toml` | Metadados do pacote, dependências, build e configuração do pytest |
| `uv.lock` | Resolução das versões e origens dos pacotes |
| `uv.toml` | Cache e versão mínima de uv |
| `.python-version` | Seleção local do Python 3.10 |
| `.gitignore` | Exclusão de dados locais, segredos e artefatos |
| `specs/` | Escopo, contratos, critérios de aceite e evidências das entregas |
| `__init__.py` | Metadados e versão do pacote |
| `__main__.py` | Entrada pelo pacote e compatibilidade dos imports da CLI |
| `cli.py` | Argumentos, despacho do comando e apresentação do relatório |
| `config.py` | Caminhos padrão e substituição por caminhos personalizados |
| `ingestion.py` | Leitura, extração por página, metadados e relatórios |
| `tests/` | Verificações automatizadas com dados temporários |
| `data/documents/` | PDFs originais locais |
| `data/index/` | Local reservado para uma implementação futura de índice |
| `.skill-index/` | Perfil auxiliar de desenvolvimento, sem participação no fluxo de ingestão |

## 7. Trechos importantes do código

Os trechos desta seção foram extraídos dos arquivos do projeto. Quando um fragmento é apresentado, sua localização e seu propósito são indicados no texto.

### 7.1. Configuração sem efeitos no sistema de arquivos

Arquivo: `src/academic_assistant/config.py`.

```python
"""Configuração local do assistente."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Caminhos usados pelo assistente, sem efeitos no sistema de arquivos."""

    documents_dir: Path = Path("data/documents")
    index_dir: Path = Path("data/index")
```

`Settings` centraliza os caminhos padrão. `frozen=True` impede atribuições comuns aos campos depois da construção, e `slots=True` restringe os atributos da instância aos campos declarados.

Construir a configuração não cria nem lê diretórios. Os caminhos são relativos ao diretório de execução. Essa decisão permite usar uma pasta temporária nos testes ou executar a aplicação em outro local sem procurar automaticamente a raiz do repositório.

O caminho `index_dir` é apenas uma configuração reservada: não implica que exista persistência de índice nesta versão.

### 7.2. Ponto de entrada mínimo e compatibilidade

Arquivo: `src/academic_assistant/__main__.py`.

```python
"""Entrada do pacote e compatibilidade dos imports da CLI."""

from academic_assistant.cli import build_parser, main

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
```

A execução `python -m academic_assistant` chama `main()` e propaga seu código de saída. A reexportação mantém os imports anteriores funcionando, mesmo depois de a implementação da CLI ter sido transferida para `cli.py`.

Não há duplicação de parsing ou de processamento no ponto de entrada.

### 7.3. Construção da interface de terminal

Arquivo: `src/academic_assistant/cli.py`, função `build_parser()`.

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m academic_assistant",
        description="Assistente de consulta a regulamentos acadêmicos.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command")
    ingest = commands.add_parser("ingest", help="Extrair PDFs locais por página.")
    ingest.add_argument(
        "--documents-dir", type=Path, default=Settings().documents_dir,
        help="Pasta de PDFs (padrão: data/documents).",
    )
    return parser
```

A CLI oferece `--version`, o subcomando `ingest` e a opção `--documents-dir`. A ajuda é fornecida pelo `argparse`, que também rejeita argumentos inválidos.

Sem subcomando, a implementação atual retorna 0 e não realiza processamento. O valor padrão de `--documents-dir` vem de `Settings`, evitando manter duas definições independentes do caminho.

### 7.4. Contrato do resultado de ingestão

Arquivo: `src/academic_assistant/ingestion.py`, estruturas de relatório.

```python
@dataclass
class PageIssue:
    page_number: int
    reason: str


@dataclass
class FileReport:
    document_name: str
    status: Literal["complete", "partial", "rejected"] = "rejected"
    total_pages: int | None = None
    processed_pages: list[int] = field(default_factory=list)
    skipped_pages: list[PageIssue] = field(default_factory=list)
    problem: str | None = None


@dataclass
class IngestionResult:
    pages: list[Document]
    reports: list[FileReport]
```

A função de ingestão retorna duas coleções distintas:

- `pages`: evidências textuais extraídas e seus metadados.
- `reports`: resultado do processamento de cada arquivo, inclusive daqueles que não produziram texto aproveitável.

`PageIssue` registra página e motivo. `FileReport` distingue processamento completo, parcial e rejeitado, mantendo o total de páginas quando conhecido. `field(default_factory=list)` cria listas independentes para cada instância.

A separação permite que a CLI apresente os problemas sem imprimir o texto dos documentos e que etapas futuras consumam as páginas diretamente.

### 7.5. Seleção determinística dos PDFs

Arquivo: `src/academic_assistant/ingestion.py`, função pública `ingest_documents()`.

```python
def ingest_documents(documents_dir: Path) -> IngestionResult:
    """Lê PDFs diretamente da pasta e retorna páginas e relatório de cada arquivo."""
    root = Path(documents_dir)
    try:
        if not root.is_dir():
            raise IngestionError("A pasta de documentos não existe ou não é um diretório.")
        paths = sorted(
            (path for path in root.iterdir() if path.suffix.lower() == ".pdf" and path.is_file()),
            key=lambda path: (path.name.casefold(), path.name),
        )
    except OSError as error:
        raise IngestionError("Não foi possível acessar a pasta de documentos.") from error
    if not paths:
        raise IngestionError("Não encontrei arquivos PDF diretamente na pasta de documentos.")

    result = IngestionResult(pages=[], reports=[])
    for path in paths:
        pages, report = _extract_file(path, root)
        result.pages.extend(pages)
        result.reports.append(report)
    return result
```

A função verifica se a entrada é uma pasta e seleciona apenas arquivos com extensão `.pdf`, sem diferenciar maiúsculas de minúsculas. Como utiliza `iterdir()`, não percorre subpastas. A ordenação combina o nome normalizado por `casefold()` com o nome original, produzindo uma ordem determinística.

Uma pasta ausente, inacessível ou sem PDFs provoca `IngestionError`. Arquivos com extensão PDF são posteriormente examinados pelo leitor; a extensão, sozinha, não comprova que seu conteúdo seja válido.

O marcador `.gitkeep` é ignorado pela seleção. Por isso, um checkout sem PDFs mantém as pastas, mas a tentativa de ingestão informa ausência de documentos.

### 7.6. Identidade do documento e página física

Fragmento de `_extract_file()`, em `ingestion.py`:

```python
metadata = {
    "document_id": path.relative_to(root).as_posix(),
    "document_name": path.name,
    "document_hash": sha256(content).hexdigest(),
}
for page_index in range(report.total_pages):
    page_number = page_index + 1
```

`document_id` é o caminho relativo à pasta selecionada, normalizado com barras. `document_name` é o nome real do arquivo. O hash é calculado sobre os bytes originais, e não sobre o texto extraído.

A página da biblioteca é acessada por índice iniciado em zero; a aplicação faz a conversão para página física iniciada em um apenas na ingestão. Assim, os consumidores posteriores recebem uma convenção única.

| Campo | Interpretação | Limite da informação |
| --- | --- | --- |
| `document_id` | Identidade pelo caminho relativo | Renomear o arquivo altera o identificador |
| `document_name` | Nome do arquivo exibido ao usuário | Não é um título institucional inferido |
| `document_hash` | Identificação da versão dos bytes | Não informa vigência ou aplicabilidade da norma |
| `page_number` | Posição física no PDF, começando em 1 | Pode diferir do número impresso na página |
| `page_content` | Texto retornado pela extração | Não reproduz necessariamente todo o layout visual |

Alterar o conteúdo mantendo o caminho preserva `document_id`, mas muda o hash. Renomear sem modificar bytes altera o identificador e preserva o hash. Não existe deduplicação por igualdade de texto.

### 7.7. Aproveitamento parcial sem renumerar páginas

Fragmento do laço de extração em `ingestion.py`:

```python
try:
    text = reader.pages[page_index].extract_text()
except (PyPdfError, OSError, ValueError, UnicodeError):
    report.skipped_pages.append(
        PageIssue(page_number, "Falha de leitura ou extração da página.")
    )
    continue
if not text or not text.strip():
    report.skipped_pages.append(
        PageIssue(page_number, "Página sem texto extraível; pode exigir OCR.")
    )
    continue
pages.append(
    Document(page_content=text, metadata={**metadata, "page_number": page_number})
)
report.processed_pages.append(page_number)
```

Se uma página não tiver texto aproveitável ou ocorrer uma falha recuperável de extração, o motivo é registrado e o processamento segue para a próxima página. Quando há texto, ele é associado aos metadados do arquivo e à página física correspondente.

A verificação `text.strip()` identifica conteúdo vazio ou composto apenas por espaços; o texto armazenado continua sendo `text`, sem aplicar essa limpeza ao conteúdo retornado.

Em um PDF de três páginas cuja segunda página não tem texto, as páginas retornadas continuam numeradas como 1 e 3. A aplicação não as renumera como 1 e 2, o que evitará referências incorretas no futuro.

### 7.8. Leitura dos originais e rejeição de PDFs protegidos

Fragmento inicial de `_extract_file()`:

```python
content = path.read_bytes()
reader = PdfReader(BytesIO(content))
if reader.is_encrypted:
    report.problem = "PDF protegido; descriptografia não está disponível."
    return [], report
report.total_pages = len(reader.pages)
if not report.total_pages:
    report.problem = "PDF sem páginas."
    return [], report
```

O arquivo é lido em bytes e entregue ao leitor por `BytesIO`; o código de ingestão não grava no PDF original. PDFs identificados como criptografados são rejeitados, pois esta versão não oferece descriptografia. PDFs sem páginas também recebem um problema explícito.

Falhas de arquivo, como leitura interrompida ou PDF inválido, seguem um tratamento próprio. Se o documento não pode ser processado com segurança até o fim, ele pode ser rejeitado mesmo que páginas anteriores tenham sido extraídas; nesse caso, suas páginas não são retornadas como um resultado válido.

### 7.9. Despacho, resumo e código de saída

Arquivo: `src/academic_assistant/cli.py`, função `main()`.

```python
def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ingest":
        from academic_assistant.ingestion import IngestionError, ingest_documents

        try:
            result = ingest_documents(args.documents_dir)
        except IngestionError as error:
            print(f"Erro de ingestão: {error}", file=sys.stderr)
            return 2
        labels = {"complete": "completo", "partial": "parcial", "rejected": "rejeitado"}
        print(f"Arquivos: {len(result.reports)} | Páginas aproveitadas: {len(result.pages)}")
        for report in result.reports:
            total = report.total_pages if report.total_pages is not None else "desconhecido"
            print(
                f"{report.document_name}: {labels[report.status]} | "
                f"Páginas: {len(report.processed_pages)}/{total}"
            )
            if report.problem:
                print(f"  Problema: {report.problem}")
            for issue in report.skipped_pages:
                print(f"  Página do PDF {issue.page_number}: {issue.reason}")
        return int(any(report.status != "complete" for report in result.reports))
    return 0
```

A CLI converte problemas de pasta em mensagem de erro enviada a `stderr`, com código 2. Para um lote iniciado, imprime o total de arquivos, as páginas aproveitadas, o estado de cada arquivo e as ocorrências por página.

O código final depende dos relatórios: um único arquivo parcial ou rejeitado faz o lote retornar 1. Desse modo, um lote misto não é apresentado como processamento completo.

## 8. Tratamento de erros e limites operacionais

| Situação | Comportamento atual | Código da CLI |
| --- | --- | --- |
| Todos os PDFs processados integralmente | Resumo de sucesso por arquivo | 0 |
| PDF com páginas aproveitáveis e páginas sem texto | Arquivo parcial; páginas ausentes e motivos listados | 1 |
| PDF inválido ou ilegível | Arquivo rejeitado com problema registrado | 1 |
| PDF protegido | Arquivo rejeitado; descriptografia indisponível | 1 |
| PDF sem páginas ou sem texto aproveitável | Arquivo rejeitado com explicação | 1 |
| Lote com arquivos válidos e rejeitados | Resultados individuais preservados; lote incompleto | 1 |
| Pasta ausente, inacessível ou caminho de arquivo | Erro de ingestão, sem processamento do lote | 2 |
| Pasta sem PDFs, inclusive apenas com `.gitkeep` | Mensagem de ausência de PDFs | 2 |
| Argumento desconhecido | Mensagem de uso do `argparse` | 2 |

Ausência de texto não prova que uma página seja digitalizada. A mensagem informa que ela **pode exigir OCR**. A aplicação não implementa OCR nem recupera automaticamente informações existentes apenas como imagem.

A ingestão retorna os textos em memória. Não há persistência das páginas extraídas nesta etapa, e executar novamente `ingest` repete a leitura e a extração.

## 9. Testes e evidências de validação

### 9.1. Estratégia de testes

A suíte é executada por `pytest` e combina testes com `unittest.TestCase` e funções de teste do pytest. Os PDFs sintéticos são criados em diretórios temporários com `PdfWriter`; seus textos são explicitamente identificados como fictícios.

Os testes comuns não exigem rede, chaves de API, LLM ou os PDFs do usuário. A extração principal utiliza PDFs válidos gerados para o teste, enquanto falhas difíceis de reproduzir são complementadas por simulações locais com `monkeypatch`.

### 9.2. Cobertura implementada

| Grupo | Verificações existentes |
| --- | --- |
| Configuração | Caminhos padrão, caminhos personalizados e ausência de criação automática de diretórios |
| CLI básica | Ajuda, versão e rejeição de argumento desconhecido |
| Entrada real pelo pacote | Execução em subprocesso, sem subcomando, ajuda, versão e argumento inválido |
| Compatibilidade | Reexportações de `main` e `build_parser` apontam para a implementação de `cli.py` |
| Texto e origem | Uma página por `Document`, texto preservado, metadados e numeração física |
| Identidade e integridade | Mudança de conteúdo, renomeação e preservação dos bytes originais |
| PDFs sem conteúdo | Arquivos sem páginas e páginas sem texto |
| Lote misto | Arquivos válidos, inválidos e protegidos no mesmo processamento |
| Seleção | Extensão com maiúsculas, ordem determinística e exclusão de subpastas |
| Processamento parcial | Páginas ausentes sem perda da numeração física |
| Falhas simuladas | Erro de extração por página, erro de leitura por arquivo e acesso negado à pasta |
| Ingestão pela CLI | Pasta padrão, pasta personalizada, resumo e códigos 0, 1 e 2 |
| Marcadores | Pasta apenas com `.gitkeep` produz ausência de PDFs |
| Dados personalizados | Arquivos permanecem na pasta informada sem cópia para a pasta padrão |
| Saída de texto | Conteúdo integral das páginas não é impresso pelo resumo da CLI |

Não foi calculado um percentual de cobertura de código. Os 22 casos aprovados comprovam os comportamentos exercitados; não equivalem a uma garantia de funcionamento com todo PDF possível.

### 9.3. Exemplo de teste da numeração física

Arquivo: `tests/test_ingestion.py`.

```python
def test_partial_pdf_keeps_physical_page_numbers(tmp_path: Path) -> None:
    write_pdf(tmp_path / "parcial.pdf", ["Regra ficticia A.", None, "Regra ficticia B."])
    result = ingest_documents(tmp_path)
    report = result.reports[0]
    assert report.status == "partial"
    assert report.total_pages == 3
    assert [page.metadata["page_number"] for page in result.pages] == [1, 3]
    assert report.skipped_pages[0].page_number == 2
    assert "sem texto" in report.skipped_pages[0].reason
```

Esse teste produz três páginas, sendo a segunda sem texto. Ele confirma que a resposta contém as páginas 1 e 3 e que a ocorrência aponta para a página 2. O caso valida a rastreabilidade necessária às futuras citações.

### 9.4. Exemplo de teste de identidade e hash

Arquivo: `tests/test_ingestion.py`.

```python
def test_identity_and_hash_after_change_and_rename(tmp_path: Path) -> None:
    path = tmp_path / "regra.pdf"
    write_pdf(path, ["Documento ficticio: primeira versao."])
    previous = ingest_documents(tmp_path).pages[0].metadata
    write_pdf(path, ["Documento ficticio: segunda versao."])
    current = ingest_documents(tmp_path).pages[0].metadata
    assert previous["document_id"] == current["document_id"]
    assert previous["document_hash"] != current["document_hash"]
    path.rename(tmp_path / "renomeado.pdf")
    renamed = ingest_documents(tmp_path).pages[0].metadata
    assert renamed["document_id"] != current["document_id"]
    assert renamed["document_hash"] == current["document_hash"]
```

Esse teste distingue identidade por caminho e identidade de conteúdo. Ele evita confundir alteração de versão com criação de um novo documento e comprova que uma renomeação não é tratada como mudança dos bytes.

### 9.5. Resultados registrados

Na validação da SPEC-005, foi executado:

```bash
uv run --extra dev --locked --offline pytest -q
```

Resultado registrado:

```text
22 passed in 1.08s
```

Também foi executada a ingestão real pela pasta padrão:

```bash
uv run --extra dev --locked --offline python -m academic_assistant ingest
```

Saída observada, com código 0:

```text
Arquivos: 2 | Páginas aproveitadas: 18
doc1.pdf: completo | Páginas: 9/9
doc2.pdf: completo | Páginas: 9/9
```

Foram conferidos identificadores, nomes, hashes e páginas físicas 1–9 em cada documento. As specs registram também que os textos extraídos dos dois arquivos são idênticos, embora os hashes sejam diferentes. Ambos são mantidos como entradas distintas, conforme a política de identidade por caminho.

Os resultados acima são evidências da execução registrada durante a implementação, no estado correspondente ao commit de referência. A preparação deste relatório não envolveu uma nova instalação em máquina vazia ou uma nova avaliação de modelo.

### 9.6. Integridade dos PDFs locais

| Arquivo | Páginas aproveitadas | SHA-256 preservado |
| --- | --- | --- |
| `doc1.pdf` | 9 | `9e90b9119bb5025ae3360ce93f30e9c48b61bf619dc74fded53a6f13bd020f40` |
| `doc2.pdf` | 9 | `00aad6a9e7e6bcb7d1bee66040c6d51742528dee7147582d8a6f08686ca8259c` |

Os hashes foram comparados antes e depois da movimentação e após a ingestão. Essa verificação confirma a preservação dos arquivos nesta operação; não comprova autenticidade institucional, vigência ou adequação acadêmica do conteúdo.

## 10. Segurança dos dados e versionamento

A ingestão atual é local. Não há provedor externo configurado, envio de documentos para embeddings ou transmissão de perguntas para geração de respostas.

O `.gitignore` exclui ambientes virtuais, caches, artefatos de build, PDFs, dados de índice e variantes locais de `.env`. As pastas de dados mantêm somente seus marcadores versionáveis.

Trecho das regras implementadas:

```gitignore
.env
.env.*
!.env.example

# Dados locais e artefatos gerados
data/documents/**
!data/documents/.gitkeep
data/index/**
!data/index/.gitkeep

# PDFs locais, inclusive fora da pasta padrão
*.[pP][dD][fF]
```

As exceções dos marcadores foram verificadas com `git check-ignore`. Um futuro `.env.example` poderá ser versionado, mas não foi criado porque ainda não há variáveis de ambiente da aplicação a documentar.

Os PDFs estavam preparados no staging antes da organização. Após serem movidos, apenas esses dois caminhos foram retirados do staging, preservando os originais em `data/documents/`. Eles não foram incluídos no commit.

A regra de exclusão não remove automaticamente arquivos já rastreados pelo Git. Por isso, a conferência do staging foi parte da entrega. O commit `cd99297` contém 21 arquivos alterados, incluindo as entregas anteriores já preparadas e a SPEC-005. A árvore de trabalho estava limpa após o commit, antes da criação deste relatório.

A inspeção de whitespace identificou duas linhas em branco extras no fim de `__init__.py` e `config.py`, já presentes no staging anterior. Elas foram preservadas para manter o escopo da reorganização. Não foram registradas falhas funcionais associadas a essas linhas, e a suíte passou.

## 11. Roteiro para demonstração ao professor

### 11.1. Preparar o ambiente

Na raiz do projeto, com uv e Python disponíveis:

```bash
uv sync --extra dev --locked
```

Esse comando usa o lockfile versionado para instalar o projeto e as dependências de desenvolvimento. Uma primeira instalação sem cache exige acesso aos pacotes. Após o cache estar disponível, a sincronização pode usar `--offline`.

### 11.2. Apresentar a CLI

```bash
uv run --locked python -m academic_assistant --help
uv run --locked python -m academic_assistant --version
```

A ajuda apresenta as opções implementadas, e a versão identifica a aplicação como 0.1.0.

### 11.3. Processar os documentos locais

Os PDFs devem estar diretamente em `data/documents/`. Então:

```bash
uv run --locked python -m academic_assistant ingest
```

No ambiente verificado, esse fluxo processou os dois PDFs locais e apresentou o resumo de 18 páginas. Em outro checkout, esses arquivos não estarão disponíveis automaticamente, pois não são versionados.

Para selecionar outra pasta:

```bash
uv run --locked python -m academic_assistant ingest --documents-dir /caminho/para/pdfs
```

O caminho deve ser substituído por uma pasta existente. O comando não copia nem move os documentos dessa pasta.

### 11.4. Executar os testes

Com o ambiente e o cache preparados:

```bash
uv run --extra dev --locked --offline pytest -q
```

A demonstração pode destacar que os testes não dependem dos dois PDFs locais: eles geram seus próprios documentos temporários e verificam também casos de erro.

### 11.5. Mostrar o contrato interno

O núcleo pode ser usado diretamente por Python:

```python
from pathlib import Path
from academic_assistant.ingestion import ingest_documents

result = ingest_documents(Path("data/documents"))

for page in result.pages:
    print(page.metadata)

for report in result.reports:
    print(report.document_name, report.status, report.processed_pages)
```

Esse exemplo demonstra o consumo da interface pública; não é uma funcionalidade de consulta acadêmica. A saída pode mostrar os metadados sem divulgar o texto integral dos documentos.

## 12. Limitações atuais

| Limitação | Consequência prática |
| --- | --- |
| Não há divisão em trechos | O conteúdo ainda está organizado apenas por página |
| Não há embeddings | Não existe representação vetorial para busca semântica |
| Não há persistência do índice | A pasta `data/index/` contém apenas um marcador |
| Não há recuperação por pergunta | A aplicação não seleciona evidências para uma consulta |
| Não há LLM configurado | A aplicação não gera respostas em linguagem natural |
| Não há validação de citações de respostas | O contrato final ainda não foi implementado |
| Não há OCR | Informações existentes apenas como imagem podem não ser aproveitadas |
| Não há descriptografia | PDFs identificados como protegidos são rejeitados |
| Leitura não recursiva | PDFs em subpastas não entram automaticamente no lote |
| Textos não são persistidos | Uma nova ingestão refaz a extração |
| Aplicabilidade do corpus não foi validada | Extrair texto não comprova que o documento seja a norma adequada |
| Interface exclusivamente de terminal | Ainda não há interface web |
| Sem avaliação com LLM real | Os testes atuais não demonstram qualidade de respostas ou resistência a instruções maliciosas |

Não foram implementados agentes autônomos, pesquisa web durante respostas, fine-tuning, autenticação, CI ou infraestrutura distribuída. Esses recursos não eram necessários para as entregas concluídas.

## 13. Próximas etapas previstas

A sequência abaixo expressa as responsabilidades que ainda precisam ser implementadas; não representa funcionalidades disponíveis nem novas specs já aprovadas.

| Etapa | Trabalho necessário | Verificação esperada |
| --- | --- | --- |
| Seleção do corpus | Identificar documentos institucionais e contextos aplicáveis | Conferir instituição, curso, modalidade e versão quando relevantes |
| Divisão em trechos | Dividir páginas com tamanho e sobreposição configuráveis | Manter origem, condições e identificação dos trechos |
| Embeddings | Escolher modelo e integração compatíveis | Usar a mesma configuração na indexação e consulta |
| Índice persistente | Armazenar vetores e metadados | Reutilizar índice e substituir versões sem resíduos ou perda do último índice válido |
| Recuperação | Buscar evidências relevantes para a pergunta | Avaliar se a evidência sustenta a resposta, além da semelhança temática |
| Geração | Enviar pergunta e evidências ao modelo | Preservar condições, citar fontes e se abster quando necessário |
| Validação | Conferir estrutura e identificadores de fonte | Rejeitar fontes inexistentes e excertos que não correspondam ao contexto |
| Avaliação ponta a ponta | Executar perguntas revisadas com o modelo escolhido | Avaliar recuperação, suporte semântico, citações e abstenção separadamente |

O retorno final deverá separar `answer` de `sources`. Os identificadores de fonte deverão ser atribuídos pela aplicação, vinculados aos trechos recuperados. O modelo poderá selecionar esses identificadores, mas a aplicação deverá montar documento, página e excerto a partir dos dados recuperados.

A mensagem exigida para falta de suporte é:

> Não encontrei evidências suficientes nos documentos cadastrados para responder a essa pergunta.

Esse comportamento ainda será implementado na etapa de consulta. Uma falha técnica não deverá ser convertida automaticamente nessa mensagem.

Antes de utilizar um provedor externo, será necessário documentar quais textos serão enviados para embeddings e geração. A escolha deverá considerar o ambiente, a configuração e o custo de avaliação, mantendo os testes comuns independentes de chamadas reais.

## 14. Situação em relação ao MVP

| Critério final do MVP | Situação no estágio atual |
| --- | --- |
| Receber um PDF com texto | Atendido pela pasta local e ingestão |
| Indexar o PDF | Pendente |
| Reutilizar um índice sem recalcular embeddings a cada consulta | Pendente |
| Responder pergunta coberta pelos documentos | Pendente |
| Apresentar documento, página e excerto literal na resposta | Metadados de documento e página preparados; resposta e fontes ainda pendentes |
| Abster-se quando faltar suporte | Requisito definido, implementação pendente |
| Distinguir erro técnico de ausência de evidência | Erros de ingestão tratados; distinção no fluxo de consulta ainda pendente |
| Testes e README reproduzíveis | Atendidos para instalação, CLI e ingestão; serão ampliados nas próximas etapas |

O progresso obtido estabelece um ponto de partida verificável para o restante do sistema: documentos podem ser lidos sem alterar os originais, suas páginas mantêm origem identificável e problemas de processamento são apresentados explicitamente. O próximo avanço deverá conectar essa base à divisão de trechos, ao índice e à consulta fundamentada.

## 15. Referências internas para conferência

- [Requisitos e convenções — AGENTS.md](AGENTS.md)
- [Instalação e uso — README.md](README.md)
- [Dependências e configuração — pyproject.toml](pyproject.toml)
- [Configuração do uv — uv.toml](uv.toml)
- [SPEC-001 — Bootstrap](specs/001-bootstrap.md)
- [SPEC-002 — Ambiente com uv](specs/002-ambiente-reproduzivel-com-uv.md)
- [SPEC-003 — Dependências](specs/003-desbloqueio-dependencias.md)
- [SPEC-004 — Ingestão](specs/004-ingestao-pdfs-por-pagina.md)
- [SPEC-005 — Estrutura](specs/005-organizacao-da-estrutura-do-projeto.md)
- [Interface de terminal — cli.py](src/academic_assistant/cli.py)
- [Configuração — config.py](src/academic_assistant/config.py)
- [Extração e relatórios — ingestion.py](src/academic_assistant/ingestion.py)
- [Testes de bootstrap e CLI](tests/test_bootstrap.py)
- [Testes de ingestão](tests/test_ingestion.py)

Este relatório foi elaborado a partir do código, das especificações, do README e das evidências registradas na implementação. Não reproduz o conteúdo dos PDFs locais nem certifica a validade acadêmica de seus textos.

## 16. Atualização de 13 de outubro de 2026 — SPEC-006 a SPEC-012

Esta seção preserva o relatório histórico acima e registra a evolução posterior. O fluxo completo do RAG foi implementado: seleção do corpus, divisão por página, embeddings NVIDIA, índice Chroma persistente, recuperação filtrada por contexto, geração estruturada, validação determinística, consulta pela CLI e avaliação real separada dos testes.

O corpus inicial de regras discentes contém `doc3.pdf`, específico do Campus São Luís–Monte Castelo, e `doc4.pdf`, com normas gerais de graduação e vigência atual não comprovada. `doc1.pdf` e `doc2.pdf` continuam preservados, mas foram excluídos da seleção por tratarem da carreira técnico-administrativa. A ingestão atual processa quatro PDFs e 85 páginas; o índice ativo contém dois documentos, 67 páginas e 169 trechos.

Os modelos escolhidos foram `nvidia/nemotron-3-embed-1b`, com 2.048 dimensões, e `nvidia/nemotron-3-super-120b-a12b`. O índice é versionado e publicado atomicamente. A consulta exige instituição e nível do curso e inclui fontes específicas de campus somente quando o campus correspondente é informado.

A SPEC-012 executou 16 casos locais e cinco sintéticos. O relatório local registra hashes do código, prompt, corpus e casos, manifesto do índice, modelos, parâmetros e chamadas. Uma falha transitória em IFMA-012 foi repetida isoladamente e consolidada após verificação de compatibilidade. No total consolidado foram contabilizadas 38 chamadas, 16 de embeddings e 22 de geração; a integração não informou custo monetário.

| Métrica da avaliação real | Resultado |
| --- | ---: |
| Casos concluídos | 21/21 |
| Erros técnicos após consolidação | 0 |
| Recuperação das evidências esperadas | 100% |
| Cobertura das citações esperadas | 95,00% |
| Precisão semântica das citações | 91,67% |
| Estado da resposta | 95,24% |
| Abstenção | 100% |
| Contexto ausente | 100% |
| Suporte semântico revisado | 90,48% |
| Preservação dos requisitos | 90,48% |

Conflito, resposta parcial, exceção, negação e instrução maliciosa foram aprovados nos casos sintéticos. A avaliação também encontrou limites que impedem declarar validação semântica integral: IFMA-002 se absteve apesar da evidência recuperada; IFMA-013 generalizou além do trecho antes de explicitar a lacuna; IFMA-001 omitiu uma condição cumulativa; e IFMA-011 anexou duas fontes apenas relacionadas. Esses resultados são falhas observadas do modelo e da seleção de citações, não falhas de ingestão ou recuperação.

O MVP funciona de ponta a ponta pelo terminal, reutiliza o índice e apresenta fontes verificáveis. Sua infraestrutura e seus contratos estão validados; a qualidade semântica permanece aprovada parcialmente e requer uma próxima iteração focada nos quatro casos registrados.

A verificação final da implementação aprovou 80 testes offline, compilação de `src` e `tests`, consistência do lockfile, validação dos JSONs e whitespace. Os relatórios locais, revisões, PDFs e índice permaneceram ignorados pelo Git.
