# SPEC-001 — Bootstrap do projeto

## 1. Metadados

- **Estado:** Planejada
- **Dependências:** Nenhuma
- **Entrega:** Projeto Python instalável, com CLI básica, configuração de caminhos e testes locais.

## 2. Objetivo

Preparar a base mínima para desenvolver o assistente em Python com LangChain, com instalação e execução reproduzíveis.

## 3. Contexto

O projeto ainda não possui código ou configuração de dependências. Os requisitos do produto estão em [AGENTS.md](../AGENTS.md). Esta spec prepara o ambiente de desenvolvimento; o fluxo RAG será implementado em entregas posteriores.

## 4. Pré-condições

- Python e ferramenta de instalação disponíveis no ambiente de desenvolvimento.
- Leitura das instruções do `AGENTS.md` antes da implementação.

Não são necessários PDFs, credenciais ou acesso a um provedor de modelos.

## 5. Escopo

- Criar o pacote Python e declarar dependências.
- Implementar ajuda e versão na CLI.
- Centralizar os caminhos de documentos e índice.
- Configurar testes básicos, exclusões do versionamento e README.

## 6. Fora do escopo

Extração de PDFs, divisão em trechos, embeddings, índice vetorial, recuperação, geração de respostas, interface web e integração com provedores externos. Não criar módulos vazios para essas funcionalidades.

## 7. Requisitos funcionais

- **RF-01:** `python -m academic_assistant --help` deve exibir a ajuda e terminar com sucesso.
- **RF-02:** `python -m academic_assistant --version` deve exibir a versão da aplicação e terminar com sucesso.
- **RF-03:** A configuração deve fornecer os caminhos padrão `data/documents/` e `data/index/`, permitindo substituí-los na sua construção.
- **RF-04:** A CLI deve iniciar sem credenciais, chamadas de rede ou existência prévia das pastas de dados.

## 8. Requisitos técnicos

- **RT-01:** Usar Python, com versão suportada declarada, e pacote em `src/academic_assistant/`.
- **RT-02:** Declarar LangChain e dependências de teste em `pyproject.toml`, com versões compatíveis e um único fluxo de instalação documentado.
- **RT-03:** Usar `pytest` para testes locais sem rede e sem chaves reais.
- **RT-04:** Preferir biblioteca padrão para CLI e configuração; usar nomes de código em inglês e mensagens em português.
- **RT-05:** Excluir do versionamento ambientes virtuais, credenciais, caches, documentos locais e índices gerados.

## 9. Modelo e contratos

- **Configuração:** objeto simples com `documents_dir` e `index_dir`, representados por `pathlib.Path`. Caminhos relativos são resolvidos a partir do diretório de execução. Sua construção não cria nem lê pastas.
- **CLI:** ponto de entrada `python -m academic_assistant`, responsável apenas por ajuda e versão nesta etapa.
- **Versão:** o valor exibido deve corresponder à versão declarada do pacote.

## 10. Tratamento de erros

Argumentos desconhecidos na CLI devem produzir mensagem de uso e código de saída diferente de zero. A ausência das pastas de dados não é erro nesta etapa. Não capturar exceções genericamente para ocultar falhas.

## 11. Arquivos afetados

- `pyproject.toml`
- `README.md`
- `.gitignore`
- `src/academic_assistant/__init__.py`
- `src/academic_assistant/__main__.py`
- `src/academic_assistant/config.py`
- `tests/test_bootstrap.py`

Arquivo de lock poderá ser criado se exigido pelo mecanismo de instalação escolhido. Mudanças fora desta lista devem ter justificativa dentro do escopo desta spec.

## 12. Estratégia de testes

Verificar ajuda e versão por execução da CLI, incluindo rejeição de argumento desconhecido. Verificar os caminhos padrão e sua substituição, executando sem pastas de dados e sem credenciais. Confirmar instalação e importação de LangChain no ambiente preparado.

## 13. Critérios de aceite

- **CA-01:** Instalação em ambiente virtual seguindo o README concluída, com pacote e LangChain importáveis.
- **CA-02:** Ajuda e versão executadas com sucesso, sem rede, credenciais ou pastas de dados.
- **CA-03:** Configuração permite caminhos padrão e personalizados sem operações no sistema de arquivos.
- **CA-04:** Argumento desconhecido resulta em mensagem de uso e status de falha.
- **CA-05:** Testes passam com `pytest` e README registra comandos verificados e funcionalidades pendentes.

## 14. Definition of Done

- [ ] Requisitos funcionais atendidos
- [ ] Requisitos técnicos atendidos
- [ ] Testes relevantes implementados e aprovados
- [ ] Instalação do pacote e execução da CLI verificadas em ambiente virtual
- [ ] Nenhum item fora do escopo implementado
- [ ] Documentação afetada atualizada

O item de build Maven do template foi adaptado à verificação de instalação do projeto Python.

## 15. Critério de parada

Encerrar quando instalação, configuração, ajuda, versão e testes estiverem verificados e documentados. Ingestão de PDFs e demais etapas do RAG ficam para specs futuras; este bootstrap não constitui validação do MVP.
