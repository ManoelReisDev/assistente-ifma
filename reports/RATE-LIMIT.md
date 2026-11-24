# Proteção de consultas web — 24/11/2026

## Escopo e garantias

Limitar consultas caras antes de chamar o núcleo RAG, sem autenticação nova,
serviço externo de contadores, novas dependências ou mudanças nos prompts.
Implementação em `rate_limit.py`, integração em `web.py` e configuração
opcional no ambiente/launcher.

- Padrão por IP: cinco consultas por minuto e 20 por dia.
- Padrão global do mesmo banco: dez consultas por minuto e 100 por dia.
- Janelas fixas por minuto e dia UTC.
- Respostas 429 com `Retry-After`, mensagem em português e nenhum resultado
  acadêmico inventado; banco indisponível retorna 503, sem chamar o RAG.
- Tentativas admitidas contam mesmo quando a consulta falha.
- SQLite persistente e transação de leitura/incremento indivisível.
- IPs são normalizados, incluindo IPv4 mapeado em IPv6; somente identificadores
  derivados por hash são persistidos, sem textos das consultas.
- O aplicativo não lê cabeçalhos de encaminhamento do cliente, e o launcher
  desabilita a interpretação automática desses cabeçalhos pelo Uvicorn.
- O launcher lê apenas chave NVIDIA e configurações de limite permitidas do
  `.env`, como dados, preservando a precedência das variáveis de ambiente.

## Jornadas e evidência RED/GREEN

| Jornada | RED observado | GREEN |
| --- | --- | --- |
| A sexta consulta do mesmo IP não chega ao provedor | A API retornava 200, não 429 | Teste verifica cinco chamadas ao substituto e bloqueio da sexta |
| Falhas do provedor não permitem repetições ilimitadas | A sexta tentativa ainda retornava erro do provedor 502 | Depois de cinco falhas, 429 sem nova chamada |
| Configuração dos limites pode vir do `.env` | Launcher não carregava a variável permitida | Testes de leitura e precedência passaram |
| Cabeçalhos não confiáveis não mudam a identidade do visitante | Launcher não desabilitava o processamento automático | Testes exigem `proxy_headers=False` e headers diferentes não burlam a franquia |

Antes de editar a lógica de limitação, os dois testes HTTP reproduziram a falta
de proteção. Demais cenários cobertos:

- Limites por IP e globais, por minuto e dia, incluindo desbloqueio nas fronteiras.
- Consultas negadas não gastam outros contadores.
- Preservação dos limites ao criar outra instância da aplicação.
- Vinte consumidores concorrentes de diferentes instâncias do limitador:
  exatamente três admitidos quando o limite foi configurado como três.
- Teto global aplicado a diferentes endereços de cliente.
- Limpeza de registros expirados e ausência do IP em texto puro no dump do banco.
- Falha de armazenamento bloqueia o núcleo sem expor caminhos internos.
- Configurações inválidas impedem a inicialização.
- Página e contexto continuam acessíveis quando consultas estão bloqueadas.

Comandos executados:

```bash
PYTHONDONTWRITEBYTECODE=1 ANONYMIZED_TELEMETRY=False \
  /tmp/opencode/assistente-ifma-tests/bin/python -m pytest -q -p no:cacheprovider
node --test tests/frontend.test.cjs
bash -n scripts/run-web.sh
git diff --check
```

Resultado final: **224 testes Python e três testes Node aprovados**, sintaxe
do launcher e diff sem erros. Cobertura Python com branches: **86% global**,
**100% em `rate_limit.py`**. Medição por `coverage run --branch`, com arquivo
de dados em `/tmp/opencode/rate-limit.coverage`, seguida de
`coverage report --fail-under=80`. Build offline e conferência do lockfile
passaram; o wheel contém o novo módulo, sem banco de limites ou dados privados.
Nenhuma chamada real à NVIDIA foi feita para implementar ou testar estes
limites. Não houve commit ou push nesta tarefa.

## Limitações e operação

IP é uma aproximação de usuário, não identidade autenticada. O limite global
mitiga rotação de IP, mas se aplica somente ao mesmo arquivo SQLite.
O disco precisa ser preservado; planos com armazenamento efêmero podem zerar
a franquia nos reinícios. Réplicas independentes precisam de contador central.

Atrás de proxy, configurar confiança em cabeçalhos apenas no servidor ASGI e
somente para proxies controlados que removam valores vindos do visitante.
Sem essa configuração, o IP compartilhado do proxy é limitado conservadoramente.

Os contadores são de consultas, não de chamadas internas do SDK, tokens ou custo.
Uma consulta pode invocar geração duas vezes. Os padrões não foram calibrados
com o saldo da conta NVIDIA e não garantem que a quota de toda a conta nunca
seja esgotada, sobretudo por CLI, indexação, avaliações e outras aplicações.
Não foram simulados proxies reais de hospedagem, falha física de disco ou
múltiplas réplicas distribuídas. A UI usa o tratamento de erro existente para
mostrar a espera; não foi acrescentado um contador regressivo visual.
