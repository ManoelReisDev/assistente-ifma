# SPEC-003 — Desbloqueio das dependências e conclusão do bootstrap

## 1. Metadados

- **Estado:** Concluída
- **Dependências:** Implementações existentes das SPEC-001 e SPEC-002; sua conclusão não é pré-condição.
- **Entrega:** Dependências reais instaladas, `uv.lock` gerado e validações pendentes das duas SPECs concluídas.

## 2. Objetivo

Viabilizar o acesso à fonte de pacotes e concluir a instalação e os testes do bootstrap usando o fluxo `uv` já implementado.

## 3. Contexto

A criação de `.venv` com Python 3.10 e o cache gravável já funcionam. A tentativa de gerar o lockfile falhou na resolução de DNS de `pypi.org`; o cache inspecionado não contém pytest. Ainda não foi determinado se a falha ocorre apenas no ambiente restrito de execução ou também no terminal do desenvolvedor.

Criar uma nova configuração de dependências não resolve, por si só, esse bloqueio. Esta entrega deve obter uma execução com acesso autorizado aos pacotes e registrar resultados reais.

## 4. Pré-condições

- Código e configuração das SPEC-001 e SPEC-002 disponíveis.
- `uv` e Python 3.10 disponíveis.
- Para concluir a instalação, um ambiente autorizado com acesso ao índice e aos arquivos dos pacotes deve estar disponível. Esse acesso será verificado no início da execução.

## 5. Escopo

- Verificar se o bloqueio está no ambiente restrito ou na rede do desenvolvedor.
- Usar o PyPI ou um índice institucional já autorizado e acessível.
- Se o ambiente restrito não permitir downloads, documentar a execução necessária no terminal do desenvolvedor e solicitar seus resultados.
- Gerar o lockfile, instalar as dependências e concluir as verificações previstas na SPEC-002.
- Corrigir os comandos do README para distinguir a geração inicial do lockfile da instalação a partir dele.

## 6. Fora do escopo

Alterar DNS, firewall, proxy ou permissões do sistema; contornar restrições do ambiente; criar espelho de pacotes, Docker, CI ou scripts de diagnóstico permanentes; adicionar funcionalidades do RAG. Não substituir dependências reais por implementações simuladas para aprovar esta entrega.

## 7. Requisitos funcionais

- **RF-01:** Identificar onde a instalação pode ocorrer e registrar a causa observada quando houver falha, sem atribuí-la automaticamente ao projeto.
- **RF-02:** Gerar `uv.lock` pelo próprio `uv` a partir das dependências existentes e disponibilizá-lo para versionamento.
- **RF-03:** Instalar o projeto e o extra `dev` em um ambiente novo, usando o lockfile.
- **RF-04:** Executar pytest, imports e CLI no ambiente instalado, sem `PYTHONPATH=src` nem substituição pelo unittest como comprovação final.
- **RF-05:** Atualizar os estados das SPECs anteriores somente após verificar seus critérios pendentes.

## 8. Requisitos técnicos

- **RT-01:** Reutilizar `.python-version`, `uv.toml`, `pyproject.toml` e os testes existentes.
- **RT-02:** Separar a operação inicial `uv lock` dos comandos de instalação e execução com `--locked`.
- **RT-03:** Incluir explicitamente `--extra dev` na execução dos testes para garantir a seleção das dependências de desenvolvimento.
- **RT-04:** Manter credenciais fora do repositório e não editar manualmente o lockfile. Inspecionar as origens registradas nele antes da entrega, sem divulgar endereços privados.
- **RT-05:** Um índice alternativo deve fornecer os pacotes e artefatos necessários. Não presumir que mudar uma variável redireciona URLs já registradas no lockfile; validar a origem utilizada.

## 9. Modelo e contratos

Fluxo a executar e verificar na raiz do projeto:

```bash
uv lock
uv sync --extra dev --locked
uv run --extra dev --locked python -c "import academic_assistant, langchain, langchain_core, pytest"
uv run --extra dev --locked pytest
uv run --locked python -m academic_assistant --help
uv run --locked python -m academic_assistant --version
```

Esses comandos são alvos de validação, ainda não comprovados em conjunto. Registrar ambiente, versões de Python e uv, comandos, códigos de saída e resultados resumidos. Quando executados pelo desenvolvedor, identificar essa origem da evidência.

## 10. Tratamento de erros

Falhas de DNS, conexão, autenticação e indisponibilidade de artefatos devem ser diferenciadas de incompatibilidade de dependências. Preservar a causa técnica e ocultar segredos nos registros.

Se o ambiente impedir downloads e não houver alternativa autorizada disponível, registrar o bloqueio e indicar a ação externa necessária. Não repetir indefinidamente tentativas idênticas, fabricar lockfile ou marcar validações como aprovadas.

## 11. Arquivos afetados

- `uv.lock`
- `README.md`
- `specs/001-bootstrap.md`
- `specs/002-ambiente-reproduzivel-com-uv.md`
- `specs/003-desbloqueio-dependencias.md`

Ajustes em `pyproject.toml` ou `uv.toml` são permitidos somente se uma falha concreta da resolução ou instalação exigir correção, com justificativa registrada.

## 12. Estratégia de testes

Executar o fluxo da seção 9 em ambiente novo, preservando o anterior. Verificar também argumento inválido na CLI, versão exibida correspondente ao pacote instalado e ausência de mudanças no lockfile durante os comandos com `--locked`.

Com o cache aquecido, instalar em outro ambiente vazio com `uv sync --extra dev --locked --offline`. Em uma cópia temporária do projeto, comprovar que lockfile ausente ou incompatível é rejeitado por `--locked`. Reaproveitar os testes existentes; não criar testes de rede na suíte comum.

## 13. Critérios de aceite

- **CA-01:** Fonte de pacotes acessível no ambiente escolhido e instalação completa bem-sucedida.
- **CA-02:** Lockfile gerado pelo uv, consistente com as dependências e pronto para versionamento.
- **CA-03:** Imports reais, pytest e CLI aprovados no ambiente instalado.
- **CA-04:** Sincronização offline com cache aquecido aprovada; lockfile ausente ou incompatível rejeitado sem alteração silenciosa.
- **CA-05:** README reproduz o fluxo verificado e as SPEC-001 e SPEC-002 têm suas pendências encerradas com evidências.

## 14. Definition of Done

- [x] Requisitos funcionais atendidos
- [x] Requisitos técnicos atendidos
- [x] Testes existentes aprovados pelo pytest
- [x] Instalação real, CLI e lockfile verificados
- [x] Nenhum item fora do escopo implementado
- [x] README e estados das SPECs atualizados

O item de build Maven do template foi adaptado à instalação e validação do pacote Python.

Registro da execução no ambiente restrito do assistente:

- uv 0.12.11, CPython 3.10.12 e cache `.cache/uv` disponíveis.
- `uv lock`: código de saída 2 após falha de DNS em `https://pypi.org/simple/langchain-core/`.
- O desenvolvedor executou `uv lock` e informou `Resolved 48 packages in 1.30s`; o arquivo gerado está disponível no projeto.
- `uv lock --check --offline` executado pelo assistente: código 0, 48 pacotes. Origens inspecionadas: PyPI e pacote local editável. CA-02 atendido; lockfile pronto para versionamento.
- `uv sync --extra dev --locked` executado pelo assistente: código 1 por falha de DNS ao baixar `truststore==0.10.4` de `files.pythonhosted.org`.
- O desenvolvedor executou a sincronização e informou construção do pacote e instalação de 46 pacotes com sucesso. Isso disponibilizou os artefatos para as verificações locais.
- Imports de `academic_assistant`, `langchain`, `langchain_core` e `pytest` confirmados pelo assistente, sem `PYTHONPATH`. Versão exibida correspondente aos metadados do pacote instalado.
- `uv run --extra dev --locked pytest`: código 0, cinco testes aprovados em CPython 3.10.12 e pytest 8.4.2.
- CLI: ajuda e versão com código 0; argumento desconhecido com código 2.
- Ambiente novo em diretório temporário: sincronização com `--extra dev --locked --offline` e imports reais aprovados, preservando o ambiente principal.
- Em cópia temporária do projeto, lockfile incompatível rejeitado com código 1 e lockfile ausente rejeitado com código 2. Nenhuma alteração feita no manifesto original.
- Hash SHA-256 do lockfile preservado: `a0cbed231d62de3911fc951725eace28218b8d831e37a818d524ca52e1b9fcef`.
- O desenvolvedor adicionou `uv.lock` ao Git; o assistente confirmou o arquivo registrado e preparado para commit com `git ls-files` e `git status`.
- CA-01 a CA-05 atendidos; SPEC-001 e SPEC-002 concluídas. O acesso externo para a instalação inicial foi realizado pelo desenvolvedor; a restrição de DNS do ambiente do assistente não foi alterada.

## 15. Critério de parada

Concluir quando os cinco critérios de aceite passarem. Se faltar acesso autorizado aos pacotes, manter a SPEC bloqueada e solicitar a execução externa necessária. A continuidade deve ocorrer nesta mesma SPEC após o acesso ser disponibilizado, sem criar outra SPEC para repetir a tentativa de instalação.
