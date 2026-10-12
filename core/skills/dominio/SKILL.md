---
name: dominio
description: "Centralize regras puras e contratos compartilhados."
---

# dominio

## Quando usar

Regra de negócio, schema, contrato externo ou paridade entre consumidores.

## Procedimento

1. Descubra fontes/fonte única no projeto e trace consumidores; não presuma layout de pacotes.
2. Extraia regra pura da infraestrutura, sem rede/estado global ou duplicação entre UI/API/export.
3. Schemas e contratos validam fronteiras; não importe internals cruzando pacote sem export público.
4. Especifique entradas/saídas/erros e prove invariantes com oráculo independente; teste consumidores
   para concordância real. Mudança externa respeita versionamento/compatibilidade do destino.

## Armadilhas

Tipos não validam runtime. Regra copiada pode divergir mesmo com testes verdes de cada cópia.
Não transportar vocabulário/regras de outro produto para criar dependência do núcleo.

## Verificação

Regra tem fonte única, consumidores rastreados e prova de limites/paridade pertinente.
