# Assistente de Regulamentos Acadêmicos

Aplicação em Python e LangChain para consultar documentos acadêmicos com recuperação rastreável. As entregas atuais incluem ingestão por página, divisão em trechos, índice Chroma persistente e recuperação de evidências com filtros de aplicabilidade.

Para uma visão geral não técnica da arquitetura, do funcionamento, das limitações e do valor do projeto, consulte o [Relatório geral](RELATORIO-GERAL.md).

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
├── .env.example               # nome da credencial necessária, sem segredo real
├── evaluation/                # casos sintéticos e inventários locais ignorados
├── specs/                     # especificações numeradas e template
├── src/academic_assistant/
│   ├── __init__.py             # metadados e versão
│   ├── __main__.py             # entrada do pacote e reexportações da CLI
│   ├── cli.py                  # argumentos, despacho e relatório
│   ├── chunking.py             # divisão por página e identificação dos trechos
│   ├── config.py               # Settings, sem criar pastas
│   ├── generation.py           # chamada estruturada ao LLM NVIDIA
│   ├── indexing.py             # embeddings, Chroma, manifesto e publicação
│   ├── prompts.py              # instruções e contexto tratado como dados
│   ├── query.py                # orquestração recuperação → geração
│   ├── retrieval.py            # busca filtrada, contexto vizinho e fontes
│   ├── validation.py           # contrato, fontes e bloqueio de saídas inválidas
│   └── ingestion.py            # extração por página e relatórios
├── tests/                     # testes offline com PDFs sintéticos temporários
└── data/
    ├── documents/
    │   ├── .gitkeep
    │   └── *.pdf              # documentos locais ignorados pelo Git
    └── index/
        └── .gitkeep           # índice gerado localmente permanece ignorado
```

Os marcadores mantêm as pastas no checkout. Para cadastrar documentos, coloque os PDFs diretamente em `data/documents/` e execute `ingest` a partir da raiz. Um checkout sem PDFs retorna código 2: `.gitkeep` não é um documento. Imports e configuração não criam pastas; os caminhos padrão continuam relativos ao diretório de execução.

Documentos PDF, conteúdo das pastas de dados (inclusive subpastas), `.env` e variantes locais, ambiente virtual e caches são ignorados pelo Git. Apenas os marcadores das pastas de dados e `.env.example`, que não contém uma chave real, são versionáveis.

## Configuração

A classe `Settings` usa estes caminhos, relativos ao diretório em que o processo é executado:

- documentos: `data/documents/`
- índice: `data/index/`
- inventário do corpus: `evaluation/corpus.local.json`

Também centraliza a divisão em 1.000 caracteres com 200 de sobreposição, embeddings NVIDIA `nvidia/nemotron-3-embed-1b` com 2.048 dimensões, coleção Chroma `academic-regulations` e recuperação com quatro resultados primários, uma página de contexto para cada lado e limite total de 12 trechos. A geração usa `nvidia/nemotron-3-super-120b-a12b`, `temperature=0.0`, `top_p=0.95`, até 1.024 tokens e raciocínio desativado para a saída estruturada. Os caminhos e valores podem ser substituídos ao construir a configuração; combinações inválidas são rejeitadas.

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

## Corpus inicial e avaliação

A SPEC-006 revisou os quatro PDFs locais. `doc1.pdf` e `doc2.pdf` foram excluídos do corpus inicial porque tratam da carreira técnico-administrativa e têm texto extraído idêntico. Os arquivos continuam preservados, com identidades e hashes próprios. O corpus discente inicial contém:

- `doc3.pdf`: Guia do Estudante da Graduação, 2ª edição, 2025, usado apenas como fonte complementar do Campus São Luís–Monte Castelo;
- `doc4.pdf`: Normas Gerais dos Cursos de Graduação anexas à Resolução nº 117/2013, usadas como norma geral institucional, sem presumir vigência atual ou revogação de outros documentos.

O `doc4.pdf` disponível é a versão pós-OCR que o responsável pelo corpus colocou intencionalmente na pasta de documentos após apagar a cópia digitalizada anterior. Seu hash identifica essa versão atual. Percentuais, prazos, condições e negações usados na avaliação foram comparados com as páginas renderizadas desse arquivo.

A pasta `evaluation/` contém casos sintéticos versionáveis e descreve os dois arquivos locais ignorados pelo Git: o inventário do corpus e 16 perguntas com evidências reais. Os casos cobrem resposta completa, variações de linguagem, condições, exceções, negações, continuação entre páginas, resposta parcial, ausência de evidência e contexto insuficiente. Casos fictícios adicionais cobrem conflito e instrução maliciosa.

Esses artefatos ainda não são executados por uma pipeline de recuperação ou geração. Eles definem as evidências esperadas para as próximas SPECs e não comprovam, isoladamente, a vigência das normas.

## Divisão em trechos

A SPEC-007 acrescenta `chunk_documents`, que recebe os `Document` produzidos pela ingestão e divide cada página isoladamente com o separador recursivo do LangChain. A ordem de separação favorece parágrafos e limites de artigos antes de linhas, frases, palavras e caracteres. Cada resultado preserva todos os metadados de origem e recebe um `chunk_id` SHA-256 determinístico.

Os valores padrão são `chunk_size=1000` e `chunk_overlap=200`, ambos medidos em caracteres e configuráveis ao construir `Settings`. A sobreposição deve ser não negativa e menor que o tamanho. Esses valores são iniciais e ainda deverão ser calibrados com a recuperação; qualquer mudança de parâmetros ou modelo de embeddings exigirá reconstruir o futuro índice completo.

Exemplo de uso no núcleo:

```python
from academic_assistant.chunking import chunk_documents
from academic_assistant.config import Settings
from academic_assistant.ingestion import ingest_documents

settings = Settings()
pages = ingest_documents(settings.documents_dir).pages
chunks = chunk_documents(pages, settings)
```

O divisor não cria nem persiste um índice e ainda não possui comando próprio na CLI. Uma página sem origem completa é tratada como erro técnico, não como falta de evidência. O texto de cada trecho permanece um excerto literal de uma única página; os PDFs não são modificados e nenhum conteúdo é enviado a serviços externos nesta etapa.

## Embeddings e índice persistente

A SPEC-008 usa uma única configuração: embeddings NVIDIA `nvidia/nemotron-3-embed-1b` com 2.048 dimensões e Chroma local persistente. O modelo e a dimensão são registrados no manifesto e devem ser os mesmos na futura consulta. O Chroma é carregado pela integração dedicada `langchain-chroma`; não há pickle nem desserialização insegura.

Crie a credencial em [NVIDIA Build — API Keys](https://build.nvidia.com/settings/api-keys): entre ou crie uma conta NVIDIA, aceite os termos do Developer Program quando solicitado, selecione **Generate API Key** e copie imediatamente o valor `nvapi-...`. Essa chave de endpoints é diferente de uma chave NGC usada para baixar contêineres privados.

Não envie a chave em conversas nem a grave em arquivos versionados. Para mantê-la somente na sessão atual do terminal:

```bash
export NVIDIA_API_KEY="nvapi-sua-chave-real"
```

Para usar um arquivo local ignorado pelo Git:

```bash
cp .env.example .env
chmod 600 .env
# Edite .env e substitua apenas o valor fictício pela chave nvapi-...
set -a
source .env
set +a
```

O projeto não carrega `.env` automaticamente; o comando `source .env` deve ser repetido em cada novo terminal. Confira se a variável está carregada sem imprimir o segredo:

```bash
test -n "$NVIDIA_API_KEY" && echo "NVIDIA_API_KEY configurada"
```

Valide a credencial e o acesso ao catálogo sem enviar os PDFs:

```bash
uv run --locked python -c 'from academic_assistant.config import Settings; from academic_assistant.indexing import create_embeddings; model = create_embeddings(Settings()); print("Acesso NVIDIA confirmado:", model.model)'
```

Essa verificação consulta o catálogo hospedado da NVIDIA, mas não chama `embed_documents` nem envia o corpus.

Depois execute:

```bash
uv run --locked python -m academic_assistant index
```

O comando lê `evaluation/corpus.local.json`, processa apenas os documentos selecionados, exige extração completa e confere os hashes revisados antes de enviar dados ao provedor. **Os textos dos trechos de `doc3.pdf` e `doc4.pdf` serão enviados ao endpoint hospedado da NVIDIA.** Não execute o comando com documentos privados sem autorização institucional e análise das regras de tratamento de dados aplicáveis.

É possível substituir os caminhos sem copiar os arquivos:

```bash
uv run --locked python -m academic_assistant index \
  --documents-dir /caminho/para/pdfs \
  --corpus-file /caminho/para/corpus.local.json \
  --index-dir /caminho/para/indice
```

Cada reconstrução cria `data/index/versions/<index_id>/`, contendo `manifest.json` e o banco Chroma. Depois de validar IDs, dimensão e totais, a aplicação substitui atomicamente `data/index/active.json`. Falhas anteriores à publicação preservam a versão ativa. Versões antigas permanecem separadas para não exigir a remoção ou renomeação de um banco aberto; somente a versão apontada por `active.json` é carregada.

O manifesto registra formato, modelo, dimensão, parâmetros de divisão, documentos, hashes e contagens. Na carga, mudanças no modelo, chunking, seleção ou conteúdo dos PDFs são rejeitadas com orientação para executar `index` novamente. A reconstrução é completa: a nova versão ativa não mistura trechos removidos ou alterados.

Os testes usam embeddings determinísticos locais e não enviam dados. O suporte a Python 3.10 exige temporariamente `onnxruntime>=1.14.1,<1.24`, pois a versão 1.24.3 selecionada inicialmente não possui wheel para esse runtime.

## Recuperação de evidências

A SPEC-009 acrescenta uma busca independente da geração. Ela exige instituição e nível do curso, restringe o Chroma aos documentos aplicáveis e atribui `source_id` somente a trechos reais. Fontes específicas de campus só entram quando o campus corresponde; fontes institucionais compatíveis continuam disponíveis. Limitações de aplicabilidade registradas no corpus acompanham o resultado.

Por padrão são recuperados quatro trechos primários, sem limiar arbitrário. A aplicação também inclui trechos da mesma página e das páginas físicas imediatamente anterior e posterior, deduplicados até o limite total de 12. A distância do Chroma é mantida apenas para diagnóstico dos resultados primários: valor menor indica maior proximidade, não probabilidade de resposta correta.

Diagnóstico pelo núcleo, sem LLM:

```python
from academic_assistant.config import Settings
from academic_assistant.indexing import create_embeddings
from academic_assistant.retrieval import RetrievalContext, retrieve_from_active_index

settings = Settings()
result = retrieve_from_active_index(
    "Como funciona o aproveitamento de estudos?",
    settings,
    create_embeddings(settings),
    RetrievalContext(institution="IFMA", course_level="graduação"),
)
for evidence in result.evidences:
    print(evidence.source_id, evidence.document_name, evidence.page_number)
```

Na recuperação isolada do exemplo, somente a pergunta é enviada ao endpoint NVIDIA para gerar o embedding; os trechos recuperados permanecem locais. O código imprime apenas identificação e página. Quando a geração abaixo é executada, pergunta e evidências também são enviadas ao LLM.

## Geração e validação

A SPEC-010 usa `nvidia/nemotron-3-super-120b-a12b`, disponível no endpoint gratuito da NVIDIA e confirmado pelo catálogo como modelo de chat com saída estruturada. O modelo recebe a pergunta, o contexto, as limitações e os trechos recuperados. Portanto, a geração real envia esse conteúdo ao provedor externo; não a execute com dados privados sem autorização institucional e análise das regras aplicáveis.

O prompt delimita pergunta e evidências em JSON e declara o conteúdo recuperado como dado não confiável. O modelo escolhe somente o estado, o texto, `source_ids` e, em respostas parciais, `unsupported_parts`. A aplicação valida os IDs, acrescenta as referências `[source_id]`, explicita deterministicamente as partes sem suporte e monta documento, página, `chunk_id` e excerto a partir do mapa da recuperação. Campos adicionais, fontes inexistentes, referências escritas pelo próprio modelo e conflitos com menos de duas fontes são rejeitados.

Quando não há evidências, o modelo não é chamado e a aplicação retorna exatamente: **“Não encontrei evidências suficientes nos documentos cadastrados para responder a essa pergunta.”** Se resultados semelhantes não sustentarem a pergunta, o modelo pode selecionar `insufficient_evidence`, que produz a mesma saída sem fontes. Falhas da NVIDIA e saídas inválidas seguem erros técnicos próprios; não são apresentadas como falta de evidência.

A geração realiza uma chamada e permite no máximo uma segunda tentativa quando a primeira saída viola o contrato ou se abstém apesar de haver evidências recuperadas. Uma revisão inválida não substitui uma primeira abstenção válida. Respostas sustentadas usam referências `[source_id]`, e as limitações registradas no corpus são acrescentadas deterministicamente. A validação garante a integridade estrutural e das fontes; a SPEC-012 registrou separadamente os limites semânticos observados com o modelo real.

## Consulta pela CLI

Com a chave carregada e o índice ativo, consulte pelo terminal:

```bash
uv run --locked python -m academic_assistant ask \
  "Como funciona o aproveitamento de estudos?" \
  --institution IFMA \
  --course-level graduação
```

Informe `--campus "São Luís–Monte Castelo"` quando desejar incluir o guia específico desse campus. `--modality` também está disponível quando a modalidade for conhecida. O comando aceita os mesmos caminhos configuráveis da indexação:

### Exemplos para graduação no Campus São Luís–Monte Castelo

Os exemplos abaixo passam o campus explicitamente. Assim, a recuperação pode combinar o Guia do Estudante específico de Monte Castelo (`doc3.pdf`) com as Normas Gerais de Graduação do IFMA (`doc4.pdf`), que têm escopo institucional. As respostas continuam limitadas ao conteúdo recuperado e podem indicar que falta evidência.

Consultar o significado e as competências da Diretoria de Ensino Superior (DESU), conforme o guia do campus:

```bash
uv run --locked python -m academic_assistant ask \
  "O que é DESU e quais são suas competências?" \
  --institution IFMA \
  --course-level graduação \
  --campus "São Luís–Monte Castelo"
```

Perguntar sobre os passos de aproveitamento de estudos no campus e o prazo mencionado nos documentos (não alinhado):

```bash
uv run --locked python -m academic_assistant ask \
  "Como peço aproveitamento de estudos no Campus Monte Castelo e qual é a data final informada?" \
  --institution IFMA \
  --course-level graduação \
  --campus "São Luís–Monte Castelo"
```

Consultar o conceito, os documentos necessários e os critérios de equivalência para aproveitamento (alinhado):

```bash
uv run --locked python -m academic_assistant ask \
  "O que significa aproveitamento de estudos, quais documentos devo apresentar e como é avaliada a equivalência?" \
  --institution IFMA \
  --course-level graduação \
  --campus "São Luís–Monte Castelo"
```

Consultar condições de aprovação e avaliação final previstas nas Normas Gerais de Graduação (alinhado):

```bash
uv run --locked python -m academic_assistant ask \
  "Quem pode fazer avaliação final e qual média precisa alcançar?" \
  --institution IFMA \
  --course-level graduação \
  --campus "São Luís–Monte Castelo"
```

Verificar se há regra cadastrada para segunda chamada, sem presumir prazo quando os documentos não o sustentarem (não alinhado):

```bash
uv run --locked python -m academic_assistant ask \
  "Qual é o prazo para solicitar segunda chamada de uma prova?" \
  --institution IFMA \
  --course-level graduação \
  --campus "São Luís–Monte Castelo"
```

O campus limita a aplicabilidade de fontes específicas; ele não garante que todo assunto tenha resposta no corpus. Quando faltar suporte, a CLI deve informar que não encontrou evidências suficientes. A data atual de um semestre, por exemplo, não deve ser inferida de um guia de 2025.

Exemplos com outros contextos ou caminhos:

```bash
uv run --locked python -m academic_assistant ask \
  "Pergunta" \
  --institution IFMA \
  --course-level graduação \
  --documents-dir /caminho/para/pdfs \
  --corpus-file /caminho/para/corpus.local.json \
  --index-dir /caminho/para/indice
```

A consulta envia a pergunta ao modelo de embeddings NVIDIA e, quando houver evidências recuperadas, envia pergunta, contexto, limitações e trechos ao modelo de geração NVIDIA. A saída apresenta `Resposta:` e um bloco por fonte com documento, página física do PDF e excerto literal. Não execute com conteúdo privado sem autorização adequada.

Código 0 indica consulta concluída, inclusive quando a resposta é a mensagem de evidência insuficiente. Código 1 indica erro técnico de índice, recuperação, provedor ou validação. Código 2 indica pergunta/contexto inválido ou não coberto. Erros são escritos em `stderr`; uma falha técnica nunca é exibida como abstenção.

## Avaliação do MVP

A avaliação real é executada separadamente do `pytest`. Ela usa uma tentativa por caso, um limite total de chamadas e grava perguntas, respostas e excertos somente em arquivos `*.local.json` ignorados pelo Git:

```bash
set -a
source .env
set +a

uv run --locked python -m academic_assistant evaluate \
  --max-provider-calls 50
```

O relatório fica em `evaluation/results.local.json`. A revisão humana fica em `evaluation/reviews.local.json` e é aplicada sem novas chamadas externas:

```bash
uv run --locked python -m academic_assistant evaluate-review
```

Para repetir somente um caso afetado e consolidá-lo no relatório completo:

```bash
uv run --locked python -m academic_assistant evaluate \
  --report evaluation/retry.local.json \
  --max-provider-calls 3 \
  --only-case IFMA-012

uv run --locked python -m academic_assistant evaluate-merge \
  --retry evaluation/retry.local.json
```

A execução final da SPEC-012 concluiu os 21 casos, incluindo um rerun focalizado após falha transitória do provedor, sem erros técnicos restantes. Foram registradas 38 chamadas: 16 de embeddings e 22 de geração; a integração não informou custo monetário. Resultados finais:

| Métrica | Resultado |
| --- | ---: |
| Recuperação das evidências esperadas | 100% |
| Cobertura das citações esperadas | 95,00% |
| Precisão semântica das citações revisadas | 91,67% (22/24) |
| Estado da resposta | 95,24% |
| Abstenção | 100% |
| Tratamento de contexto ausente | 100% |
| Suporte semântico revisado | 90,48% |
| Preservação dos requisitos revisados | 90,48% |

O MVP ainda não deve ser declarado semanticamente validado a 100%. Na regressão final, IFMA-002 se absteve apesar de recuperar a evidência; IFMA-013 fez uma generalização mais forte que a fonte antes de explicitar a lacuna; IFMA-001 omitiu um requisito cumulativo; e IFMA-011 anexou duas fontes apenas relacionadas. A recuperação, a integridade estrutural das fontes, a abstenção fora do corpus, o conflito sintético e a resistência à instrução maliciosa foram aprovados.

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

A SPEC-006 está concluída: os quatro PDFs foram classificados, duplicatas textuais e documentos fora do domínio foram excluídos da seleção sem remoção, o contexto de `doc3.pdf` e `doc4.pdf` foi registrado e os casos de avaliação foram revisados por página. A vigência da Resolução nº 117/2013 permanece uma limitação explícita; `doc4.pdf` está registrado como a versão pós-OCR deliberadamente selecionada para o corpus. A validação final aprovou os três arquivos JSON, todos os excertos locais e os 23 testes offline.

A SPEC-007 está concluída: a divisão recursiva em caracteres mantém cada trecho dentro de uma única página, preserva os metadados da ingestão e acrescenta um identificador determinístico sensível à versão e à configuração. Os padrões são 1.000 caracteres com 200 de sobreposição; ainda não representam calibração final.

A SPEC-008 está concluída: além dos testes offline, a indexação real com `nvidia/nemotron-3-embed-1b` publicou a versão `20261013T144645Z-1304d1326486`, com 2 documentos, 67 páginas e 169 trechos. A integração 1.4.3 emite um aviso de catálogo por ainda não classificar estaticamente esse modelo, mas a chamada real retornou vetores com as 2.048 dimensões esperadas.

A SPEC-009 está concluída: a recuperação filtra o corpus por contexto, busca sem limiar arbitrário, agrega contexto de páginas vizinhas sob limite configurado e produz um mapa de fontes verificáveis sem chamar LLM. Os testes usam corpus e embeddings fictícios offline.

A SPEC-010 está concluída: a geração estruturada usa um modelo NVIDIA, trata evidências como dados não confiáveis e permite que o modelo selecione apenas IDs fornecidos. A aplicação valida as citações, monta fontes reais, bloqueia saídas inválidas e mantém abstenção e falhas técnicas em caminhos distintos.

A SPEC-011 está concluída: o comando `ask` coordena o índice persistido, a recuperação e a geração, imprime fontes verificáveis e usa códigos de saída distintos para sucesso, contexto inválido e falha técnica. O fluxo integrado possui testes offline com índice, embeddings e modelo fictícios.

A SPEC-012 está concluída com limitações registradas: o executor real, o limite de chamadas, a revisão humana e a consolidação de reruns foram implementados. Os 21 casos foram concluídos e revisados, mas os resultados acima impedem declarar o MVP integralmente validado no aspecto semântico.

## Funcionalidades pendentes

A próxima evolução deve reduzir abstenção indevida, omissões de condições e sobrecitação observadas na SPEC-012 e repetir os casos afetados. Não há limiar de relevância calibrado. A seleção atual não comprova vigência normativa; essa limitação acompanha as respostas sustentadas.
