# Avaliação do corpus

Esta pasta separa casos sintéticos versionáveis de evidências locais extraídas dos PDFs não versionados.

- `synthetic-cases.json`: cenários fictícios para desenvolver e testar resposta sustentada, resposta parcial, abstenção, conflito e resistência a instruções presentes no conteúdo.
- `corpus.local.json`: inventário local dos documentos reais, seus hashes, contexto conhecido e decisão de inclusão. É ignorado pelo Git.
- `cases.local.json`: perguntas revisadas contra os documentos reais, com página física e excerto literal. É ignorado pelo Git porque reproduz conteúdo dos PDFs locais.

Os arquivos usam `format_version` 1. Cada caso possui um identificador, categoria, pergunta, contexto aplicável e resultado esperado. Os estados previstos são:

- `answerable`: há evidência para responder integralmente;
- `partial`: somente parte da pergunta possui suporte;
- `insufficient_evidence`: os documentos não sustentam a resposta;
- `context_required`: falta informação para escolher o contexto aplicável;
- `conflict`: duas evidências aplicáveis divergem e devem ser apresentadas sem escolha silenciosa.

Em `expected.evidence`, `excerpt` deve ser literal, aceitando apenas normalização de espaços, e `page_number` é sempre a página física do PDF iniciada em 1. Os casos locais não comprovam vigência normativa; eles avaliam recuperação e sustentação usando o corpus cadastrado.

Validação estrutural simples, sem rede:

```bash
uv run --locked --offline python -m json.tool evaluation/synthetic-cases.json >/dev/null
uv run --locked --offline python -m json.tool evaluation/corpus.local.json >/dev/null
uv run --locked --offline python -m json.tool evaluation/cases.local.json >/dev/null
```
