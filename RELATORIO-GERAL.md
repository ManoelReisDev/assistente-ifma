# Relatório geral — Assistente de Regulamentos Acadêmicos

## 1. Resumo executivo

O projeto implementa um assistente capaz de responder perguntas sobre regulamentos acadêmicos a partir de documentos institucionais em PDF. A proposta não é apenas conversar com um modelo de inteligência artificial, mas construir respostas verificáveis: cada afirmação deve estar associada ao documento, à página e ao trecho que serviram de base.

O sistema segue uma abordagem de **RAG** (*Retrieval-Augmented Generation*, ou geração aumentada por recuperação). Em termos simples, antes de responder, a aplicação procura trechos relevantes nos documentos cadastrados. O modelo de linguagem recebe somente esses trechos e redige a resposta. A aplicação então valida as fontes e monta as referências que serão exibidas ao usuário.

O resultado é um MVP com valor acadêmico e prático:

- reduz a necessidade de procurar manualmente em documentos extensos;
- preserva a origem das informações;
- evita responder com regras inventadas quando não há evidência;
- considera instituição, nível do curso, campus e modalidade;
- trata documentos conflitantes como conflito, em vez de escolher uma versão silenciosamente;
- possui testes automatizados offline e uma interface de terminal reproduzível.

## 2. Problema que o projeto resolve

Regulamentos acadêmicos normalmente estão espalhados em PDFs longos, guias, resoluções e documentos complementares. A dificuldade não é apenas encontrar uma palavra, mas saber se o trecho encontrado realmente se aplica à pergunta:

- o documento é da instituição correta?
- trata do nível de curso correto?
- vale para o campus ou modalidade informados?
- o texto apresenta uma regra completa, incluindo exceções?
- existem documentos com prazos diferentes?
- a informação está atualizada ou é apenas uma referência histórica?

O projeto foi desenhado para não transformar uma busca aproximada em uma certeza. Quando o material cadastrado não sustenta uma conclusão, a resposta esperada é:

> Não encontrei evidências suficientes nos documentos cadastrados para responder a essa pergunta.

Essa postura é importante porque, em assuntos acadêmicos, uma resposta convincente mas sem fonte pode induzir o estudante a perder prazos ou seguir um procedimento incorreto.

## 3. Como o sistema funciona

O fluxo completo possui cinco etapas principais.

### 3.1. Cadastro e leitura dos PDFs

Os PDFs são colocados em `data/documents/`. A aplicação lê cada arquivo diretamente, sem modificar o original, e extrai o texto página por página.

Para cada página aproveitada, são mantidos:

- identificação do documento;
- nome do arquivo;
- hash SHA-256 do conteúdo;
- número físico da página;
- texto extraído.

Arquivos inválidos, protegidos, vazios ou páginas sem texto aproveitável são informados ao usuário. O sistema não trata silenciosamente uma ingestão incompleta como se fosse completa.

### 3.2. Divisão em trechos

Uma página pode ser maior que o tamanho ideal para busca e geração. Por isso, o texto é dividido em trechos de tamanho configurável, com sobreposição entre trechos próximos.

O projeto mantém cada trecho dentro de uma única página. Essa decisão facilita a citação: quando uma fonte é apresentada, o usuário consegue verificar exatamente a página física do PDF.

Cada trecho recebe um identificador estável calculado a partir do documento, do hash, da página, da posição e da configuração de divisão.

### 3.3. Indexação persistente

Os trechos são transformados em vetores por um modelo de embeddings e armazenados em um índice Chroma local. O índice é versionado e possui um manifesto com:

- modelo de embeddings utilizado;
- tamanho e sobreposição dos trechos;
- documentos e hashes incluídos;
- quantidade de páginas e trechos;
- identificador da versão ativa.

A construção ocorre em uma versão separada. Somente depois que a nova versão é validada ela passa a ser a versão ativa. Assim, uma falha durante uma reconstrução não substitui automaticamente o último índice utilizável.

### 3.4. Recuperação contextual

Ao receber uma pergunta, a aplicação primeiro verifica o contexto informado, como instituição e nível do curso. Depois, procura os trechos mais semelhantes no índice, mas somente dentro dos documentos aplicáveis.

Além dos trechos principais, pode recuperar páginas vizinhas. Isso ajuda quando uma regra começa em uma página e continua na seguinte.

A recuperação não decide sozinha se uma regra é verdadeira. Ela apenas reúne evidências candidatas e seus metadados para a etapa seguinte.

### 3.5. Geração e validação da resposta

O modelo de linguagem recebe:

- a pergunta;
- o contexto informado;
- as limitações conhecidas do corpus;
- os trechos recuperados com identificadores de fonte.

O prompt instrui o modelo a usar somente esse material, preservar condições e exceções e tratar qualquer instrução encontrada dentro de um documento como conteúdo, não como comando.

O modelo não pode inventar nome de documento, página ou trecho. Ele escolhe apenas identificadores de fontes fornecidos pela aplicação. A aplicação monta os dados completos da citação a partir do índice e rejeita respostas inválidas.

## 4. Arquitetura do projeto

O projeto é uma aplicação de linha de comando em Python, organizada em módulos com responsabilidades bem separadas:

| Módulo | Responsabilidade |
| --- | --- |
| `cli.py` | Recebe comandos e argumentos, mostra resultados e mensagens de erro |
| `config.py` | Centraliza caminhos, modelos e parâmetros do sistema |
| `ingestion.py` | Lê PDFs e produz documentos por página |
| `chunking.py` | Divide páginas em trechos rastreáveis |
| `indexing.py` | Gera embeddings, cria o índice, valida versões e publica o índice ativo |
| `retrieval.py` | Filtra documentos aplicáveis e recupera evidências |
| `prompts.py` | Define as instruções enviadas ao modelo |
| `generation.py` | Inicializa o modelo e solicita uma resposta estruturada |
| `validation.py` | Valida a saída, as fontes e os estados da resposta |
| `query.py` | Coordena recuperação, geração e validação |

Essa separação facilita a evolução do projeto. Por exemplo, é possível trocar a interface de terminal por uma interface web sem reescrever as regras centrais de recuperação e validação.

### Pontos de entrada

O uso principal ocorre pelo comando:

```bash
uv run --locked python -m academic_assistant
```

Os comandos disponíveis são:

```bash
uv run --locked python -m academic_assistant ingest
uv run --locked python -m academic_assistant index
uv run --locked python -m academic_assistant ask "Qual é a frequência mínima?"
```

- `ingest` verifica os PDFs e apresenta um relatório de processamento;
- `index` reconstrói o índice persistente com os documentos selecionados;
- `ask` consulta o índice ativo e apresenta resposta e fontes.

## 5. Decisões de projeto que agregam valor

### Respostas fundamentadas

O sistema não exibe apenas texto gerado. Ele exibe fontes com documento, página e excerto. Isso permite que um professor ou estudante confira a origem da resposta.

### Aplicabilidade explícita

O corpus possui um inventário separado, com contexto institucional e decisão de inclusão. A aplicação não usa somente a semelhança textual para decidir que um documento serve para qualquer pergunta.

### Abstenção responsável

Quando não há suporte suficiente, a aplicação se abstém. Essa é uma característica de confiabilidade, não uma falha de usabilidade: é preferível reconhecer uma lacuna do corpus a inventar uma regra acadêmica.

### Preservação de exceções e conflitos

Os prompts e os casos de avaliação exigem que condições, negações, exceções e conflitos sejam preservados. Se dois documentos aplicáveis apresentarem prazos diferentes, o comportamento esperado é mostrar o conflito e não escolher uma regra sem justificativa.

### Proteção contra instruções presentes nos documentos

Documentos são tratados como dados. Mesmo que um trecho contenha uma frase como “ignore as fontes” ou “execute um comando”, essa frase não altera as regras da aplicação.

### Índice confiável e atualizável

Hashes e manifestos permitem detectar quando o PDF mudou ou quando o índice foi produzido com outra configuração. A reconstrução completa evita manter trechos antigos misturados com trechos novos.

### Testes substituíveis e sem dependência de rede

O núcleo permite injetar embeddings e modelos fictícios nos testes. Dessa forma, a maior parte da aplicação pode ser verificada sem chave real, sem custo de API e sem depender da disponibilidade de um provedor externo.

## 6. Estado atual e evidências

O repositório contém:

- código da aplicação em `src/academic_assistant/`;
- testes automatizados em `tests/`;
- especificações de evolução em `specs/`;
- casos sintéticos para avaliação em `evaluation/synthetic-cases.json`;
- documentação de instalação, uso, limites e decisões em `README.md`;
- dependências fixadas por `uv.lock`.

Na verificação realizada para este relatório:

- **70 testes automatizados passaram**;
- a execução foi feita offline;
- a compilação dos arquivos Python foi concluída sem erros;
- a verificação de whitespace do Git não apontou problemas.

Os testes cobrem, entre outros pontos:

- configuração e argumentos da CLI;
- leitura de PDFs por página;
- documentos inválidos, vazios ou parcialmente processados;
- divisão de trechos e estabilidade dos identificadores;
- criação, carga e reconstrução do índice;
- detecção de índice incompatível ou desatualizado;
- filtros de instituição, curso, campus e modalidade;
- recuperação de páginas vizinhas;
- resposta sem evidência;
- resposta parcial e conflito;
- fontes inexistentes, repetidas ou inventadas;
- conteúdo documental com instruções maliciosas.

## 7. Limitações atuais

As limitações são importantes para apresentar o projeto com honestidade.

### Corpus ainda limitado

A qualidade da resposta depende dos documentos cadastrados. O sistema não consulta automaticamente todos os regulamentos da instituição e não pesquisa a internet durante uma pergunta.

Se um documento não estiver no corpus, a aplicação não tem como garantir uma resposta sobre ele.

### Atualidade normativa não é inferida

O hash identifica a versão do arquivo, mas não prova que uma norma continua vigente. Um guia recente e uma resolução antiga podem coexistir. A aplicação registra limitações e pode apresentar conflito, mas a confirmação de vigência depende da curadoria institucional.

### OCR ainda não é integrado

Páginas digitalizadas ou PDFs protegidos podem não fornecer texto extraível. O sistema informa essa situação, mas não executa OCR automaticamente.

### Dependência de um provedor externo

O MVP utiliza NVIDIA para embeddings e geração. É necessária uma chave `NVIDIA_API_KEY` para indexação e consulta reais. O código prevê um único provedor, conforme o escopo inicial.

### Interface ainda é de terminal

A CLI é adequada para demonstrar e validar o núcleo, mas ainda não oferece uma interface web ou integração direta com portal acadêmico, WhatsApp ou aplicativo institucional.

### Avaliação sem modelo real ainda é limitada

Os testes automatizados usam modelos fictícios para validar contratos e segurança do código. A avaliação semântica completa com o modelo real e perguntas revisadas por especialistas deve ser feita separadamente.

### Sem autenticação e controle de perfis

O MVP não diferencia estudante, professor, coordenação ou administrador. Também não possui autenticação, autorização ou histórico persistente de perguntas.

## 8. Riscos e cuidados para uso institucional

Antes de usar o sistema como fonte oficial, seria necessário:

1. definir quem mantém o corpus;
2. registrar vigência, revogação e versão dos documentos;
3. revisar respostas de avaliação com pessoas que conheçam os regulamentos;
4. estabelecer política para envio de textos a serviços externos;
5. proteger documentos que possam conter informações privadas;
6. monitorar falhas de ingestão, índice e provedor;
7. manter uma forma de encaminhar o estudante para o setor responsável quando houver dúvida normativa.

O assistente deve ser apresentado como ferramenta de apoio à consulta, não como substituto da secretaria, da coordenação ou do texto oficial.

## 9. Evoluções recomendadas

### Curto prazo

- concluir uma bateria de avaliação com perguntas reais e respostas revisadas;
- adicionar uma etapa clara de revisão de vigência dos documentos;
- integrar OCR opcional para PDFs digitalizados;
- melhorar o comando de diagnóstico do corpus;
- adicionar logs técnicos sem registrar chaves ou conteúdos sensíveis.

### Médio prazo

- criar uma interface web simples;
- permitir filtros por curso, campus, modalidade e período;
- mostrar as fontes de forma clicável;
- incluir atualização controlada do corpus;
- oferecer métricas de recuperação e de abstenção;
- adicionar testes de integração com um ambiente configurado para o provedor real.

### Longo prazo

- integrar autenticação institucional;
- criar fluxo de aprovação para novos documentos;
- acompanhar vigência e revogação de normas;
- permitir múltiplos provedores ou modelos compatíveis;
- incorporar observabilidade e histórico de auditoria;
- disponibilizar integração com sistemas acadêmicos, mantendo o texto oficial como referência final.

## 10. Roteiro de demonstração para apresentação

Uma demonstração curta pode seguir esta ordem:

1. Mostrar a estrutura do projeto e explicar que a aplicação é organizada por etapas.
2. Executar `ingest` e mostrar que os PDFs são lidos por página, sem alteração dos originais.
3. Executar `index` e mostrar a criação do índice persistente.
4. Fazer uma pergunta respondível e destacar documento, página e trecho.
5. Fazer uma pergunta fora do corpus e mostrar a abstenção.
6. Fazer uma pergunta sem instituição ou nível de curso e mostrar que o sistema pede contexto.
7. Mostrar um caso de conflito ou uma instrução maliciosa dentro de documento sintético.
8. Encerrar destacando os 70 testes aprovados e as limitações conhecidas.

## 11. Conclusão

O principal valor do projeto está em combinar linguagem natural com rastreabilidade. Ele não tenta apenas “adivinhar uma resposta”; constrói um caminho verificável entre a pergunta, o trecho recuperado e a resposta exibida.

Como MVP, o sistema já demonstra uma arquitetura coerente para um assistente acadêmico confiável. O próximo salto de valor não depende somente de um modelo maior, mas de corpus bem mantido, avaliação com especialistas, controle de vigência e uma interface adequada ao público da instituição.

Arquivos centrais para consulta:

- [README.md](README.md) — instalação, uso e decisões do MVP;
- [AGENTS.md](AGENTS.md) — requisitos de comportamento e confiabilidade;
- [src/academic_assistant/](src/academic_assistant/) — implementação;
- [tests/](tests/) — testes automatizados;
- [evaluation/README.md](evaluation/README.md) — casos e critérios de avaliação.
