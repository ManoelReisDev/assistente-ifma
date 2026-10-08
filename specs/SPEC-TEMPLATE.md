# SPEC-XXX — Título

## 1. Metadados

- **Estado:** Planejada
- **Dependências:** Informar specs que devem estar concluídas ou “Nenhuma”
- **Entrega:** Resumir o incremento observável

## 2. Objetivo

Descrever o problema tratado e o resultado esperado desta spec.

## 3. Contexto

Registrar somente o contexto necessário para compreender as decisões e os limites do incremento.

## 4. Pré-condições

Listar as condições que devem existir antes da implementação.

## 5. Escopo

Listar, de forma objetiva, tudo que esta spec autoriza implementar ou alterar.

## 6. Fora do escopo

Listar funcionalidades relacionadas que permanecem proibidas nesta etapa.

## 7. Requisitos funcionais

Definir comportamentos observáveis e regras de negócio. Identificar os requisitos como `RF-01`, `RF-02` e assim por diante.

## 8. Requisitos técnicos

Definir restrições de implementação, arquitetura, linguagem e dependências. Identificar os requisitos como `RT-01`, `RT-02` e assim por diante.

## 9. Modelo e contratos

Descrever tipos, responsabilidades, dados, operações, invariantes e relações necessários. Evitar prescrever detalhes internos que não afetem o contrato.

## 10. Tratamento de erros

Definir falhas esperadas, exceções e condições inválidas. Não usar exceptions como fluxo normal.

## 11. Arquivos afetados

Indicar os packages e arquivos que poderão ser criados ou alterados. Mudanças fora desta lista exigem justificativa dentro do escopo da spec.

## 12. Estratégia de testes

Descrever os testes necessários, incluindo casos válidos, limites e falhas relevantes. Não criar testes que apenas repitam a implementação.

## 13. Critérios de aceite

Listar resultados verificáveis como `CA-01`, `CA-02` e assim por diante.

## 14. Definition of Done

- [ ] Requisitos funcionais atendidos
- [ ] Requisitos técnicos atendidos
- [ ] Testes relevantes implementados e aprovados
- [ ] Build aprovado com `./mvnw clean package`
- [ ] Nenhum item fora do escopo implementado
- [ ] Documentação afetada atualizada

## 15. Critério de parada

Declarar explicitamente em que ponto a implementação deve terminar e quais evoluções ficam para specs futuras.
