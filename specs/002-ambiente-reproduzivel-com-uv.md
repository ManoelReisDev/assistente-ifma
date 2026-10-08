# SPEC-002 — Ambiente reproduzível com uv

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** SPEC-001 — implementação existente; esta spec conclui sua validação pendente.
- **Entrega:** Ambiente Python criado pelo `uv`, dependências travadas e instalação, CLI e testes executados de forma reproduzível.

## 2. Objetivo

Eliminar a dependência de `ensurepip` no fluxo de desenvolvimento e concluir a validação do bootstrap com as dependências reais instaladas. O resultado deve ser um único procedimento para preparar o ambiente, executar a CLI e rodar o pytest.

## 3. Contexto

A SPEC-001 implementou o pacote, a CLI e os testes, mas o ambiente disponível não possuía `ensurepip` e não conseguia resolver o endereço do PyPI. O `uv` cria e gerencia o ambiente virtual sem depender de `python -m venv`, porém ainda precisa acessar uma fonte de pacotes na primeira instalação ou encontrar os artefatos em cache.

Esta spec trata a preparação reproduzível do projeto. Disponibilidade de rede, DNS ou de um espelho de pacotes permanece uma condição externa.

As decisões seguem a documentação oficial do `uv` sobre [lock e sincronização](https://docs.astral.sh/uv/concepts/projects/sync/), [versões de Python](https://docs.astral.sh/uv/concepts/python-versions/) e [índices de pacotes](https://docs.astral.sh/uv/concepts/indexes/).

## 4. Pré-condições

- `uv` instalado e disponível no `PATH`.
- Python 3.10 compatível disponível localmente ou acessível para instalação pelo `uv`.
- Acesso ao PyPI, a um índice compatível configurado pelo ambiente ou a um cache completo do `uv`.

Nenhuma credencial de provedor de LLM é necessária.

## 5. Escopo

- Adotar `uv` como fluxo principal de instalação e execução do projeto.
- Fixar a versão menor do Python utilizada no desenvolvimento.
- Gerar e versionar o lockfile das dependências.
- Usar um diretório de cache gravável e ignorado pelo Git.
- Permitir a configuração de um índice de pacotes pelo ambiente.
- Executar com dependências reais os testes, a CLI e as importações de LangChain.
- Atualizar o README e concluir os itens pendentes da SPEC-001 após a validação.

## 6. Fora do escopo

- Corrigir DNS, proxy, firewall ou indisponibilidade de índices externos.
- Versionar wheels, credenciais, caches ou o ambiente virtual.
- Garantir uma primeira instalação totalmente offline.
- Adicionar provedor de modelo, leitor de PDF, vector store, CI ou funcionalidades do RAG.
- Atualizar dependências além do necessário para produzir o primeiro lockfile compatível.

## 7. Requisitos funcionais

- **RF-01:** Um único comando documentado deve criar ou sincronizar `.venv` com as dependências da aplicação e de desenvolvimento, sem usar `ensurepip`.
- **RF-02:** Com o ambiente sincronizado, comandos do `uv` devem executar ajuda, versão e pytest sem ativação manual do ambiente virtual.
- **RF-03:** A instalação deve respeitar o lockfile versionado e falhar quando ele estiver ausente ou incompatível com o `pyproject.toml`.
- **RF-04:** O desenvolvedor deve poder selecionar um índice compatível por variável de ambiente, sem registrar URL privada ou credencial no repositório.
- **RF-05:** Depois de uma sincronização completa, o cache deve permitir nova sincronização offline quando todos os artefatos necessários estiverem disponíveis.

## 8. Requisitos técnicos

- **RT-01:** Manter `pyproject.toml` como declaração única das dependências diretas e `uv.lock` como resolução exata gerenciada pelo `uv`.
- **RT-02:** Declarar Python 3.10 em `.python-version`, compatível com `requires-python = ">=3.10"`.
- **RT-03:** Configurar o `uv` para usar cache dentro do projeto ou outro caminho gravável, excluído do versionamento.
- **RT-04:** Exigir uma versão mínima do `uv` compatível com as opções adotadas.
- **RT-05:** Usar `--locked` nos comandos reproduzíveis de sincronização e execução. Atualizações do lockfile devem ocorrer somente por comando explícito.
- **RT-06:** Manter `langchain>=1.0,<2.0` e `langchain-core>=1.0,<2.0` como dependências diretas. Não adicionar integrações ainda sem uso.
- **RT-07:** Usar `UV_DEFAULT_INDEX` quando for necessário substituir o PyPI. Segredos de autenticação devem permanecer em variáveis de ambiente.

## 9. Modelo e contratos

- **`.python-version`:** contém `3.10` e orienta a seleção do interpretador pelo `uv`.
- **`uv.lock`:** contém a resolução exata e deve ser versionado; não pode ser editado manualmente.
- **Configuração do `uv`:** define a versão mínima da ferramenta e um cache gravável ignorado pelo Git.
- **Fluxo normal:** `uv sync --extra dev --locked`, seguido de `uv run --locked <comando>`.
- **Índice alternativo:** o ambiente pode definir `UV_DEFAULT_INDEX` com uma URL PEP 503. O valor não faz parte dos arquivos versionados.

## 10. Tratamento de erros

- Ausência ou versão incompatível do `uv` deve gerar orientação objetiva de instalação ou atualização.
- Python incompatível ou indisponível deve ser distinguido de falha na resolução de dependências.
- Falha de DNS, índice inacessível ou pacote ausente deve preservar a mensagem original do `uv`; não apresentar o projeto como instalado.
- Lockfile desatualizado deve causar falha nos comandos com `--locked`, sem atualização silenciosa.
- Cache não gravável deve ser informado como erro de configuração, sem recorrer automaticamente a diretórios fora do projeto.
- Credenciais e URLs privadas não devem aparecer em logs, README ou arquivos versionados.

## 11. Arquivos afetados

- `pyproject.toml`
- `uv.lock`
- `.python-version`
- `uv.toml` ou configuração equivalente no `pyproject.toml`
- `.gitignore`
- `README.md`
- `specs/001-bootstrap.md`
- `specs/002-ambiente-reproduzivel-com-uv.md`

Mudanças fora desta lista exigem justificativa dentro do escopo da spec.

## 12. Estratégia de testes

Em um ambiente com fonte de pacotes acessível, gerar o lockfile e sincronizar um `.venv` novo. Confirmar as importações de `langchain`, `langchain_core`, `pytest` e `academic_assistant`. Executar o pytest, a ajuda, a versão e um argumento inválido pela interface `uv run --locked`.

Depois de aquecer o cache, recriar somente o ambiente virtual e confirmar a sincronização com modo offline e lockfile. Alterar temporariamente a declaração de uma dependência para comprovar que `--locked` rejeita um lockfile incompatível, sem versionar essa alteração.

## 13. Critérios de aceite

- **CA-01:** `uv sync --extra dev --locked` cria `.venv` e instala o projeto sem depender de `ensurepip`.
- **CA-02:** `uv run --extra dev --locked pytest` executa todos os testes com sucesso.
- **CA-03:** LangChain, LangChain Core e o pacote da aplicação são importados no ambiente sincronizado.
- **CA-04:** Ajuda e versão funcionam por `uv run --locked python -m academic_assistant`.
- **CA-05:** `uv.lock` está versionado, consistente com o `pyproject.toml` e não é alterado pelos comandos de validação.
- **CA-06:** Um cache aquecido permite sincronização offline sem acessar o índice.
- **CA-07:** O README apresenta apenas o fluxo principal com `uv`, documenta o índice alternativo e não contém credenciais.
- **CA-08:** Os itens pendentes da Definition of Done da SPEC-001 são marcados como concluídos somente após CA-01 a CA-05 passarem.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Lockfile criado e validado
- [x] Testes aprovados com `uv run --extra dev --locked pytest`
- [x] CLI e importações verificadas no ambiente sincronizado
- [x] SPEC-001 concluída sem pendências de validação
- [x] Nenhum item fora do escopo implementado
- [x] Documentação afetada atualizada

O item de build Maven do template foi adaptado à sincronização e validação do projeto Python com `uv`.

Validação concluída durante a SPEC-003: instalação real informada pelo desenvolvedor, imports e cinco testes confirmados pelo assistente, nova instalação offline aprovada com cache aquecido e lockfile inalterado. O extra `dev` foi explicitado no comando de testes para manter pytest selecionado.

CA-05 concluído: o desenvolvedor adicionou `uv.lock` ao Git; o assistente confirmou seu registro com `git ls-files --error-unmatch uv.lock`. O arquivo está preparado para commit.

## 15. Critério de parada

Encerrar quando um ambiente novo puder ser criado pelo `uv`, os comandos travados pelo lockfile passarem e a SPEC-001 estiver concluída. Interromper antes de adicionar qualquer componente do RAG. Indisponibilidade persistente de uma fonte de pacotes deve ser registrada como bloqueio externo, sem ampliar esta spec para infraestrutura de rede ou distribuição de artefatos.
