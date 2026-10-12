---
name: revisao-independente
description: "Revise aceite, riscos e provas sem editar produto."
---

# revisao-independente

## Quando usar

Revisão independente de implementação; não autoparecer do autor.

## Procedimento

1. Confirme base/HEAD/diff exatos, aceite e escopo. Trace definições e consumidores.
2. Avalie regressão, segurança, dados, concorrência, erros/cleanup e contratos afetados.
3. Confira negativo, requisitos/skips e origem das evidências. Não presuma capacidades.
4. Achado tem severidade, arquivo:linha, reprodução, esperado/observado e critério de correção.
5. Entregue parecer restrito ao HEAD visto, aprovado/rejeitado/bloqueado, com razões/limites.
   Não editar produto ou publicar review/label sem autorização.

## Armadilhas

Readonly não pode rodar testes que escrevem dados. Screenshot não prova persistência; verde
não cobre todo aceite. Nova mudança exige revalidar o parecer na parte afetada.

## Verificação

Cada critério tem evidência ou pendência explícita. Sem independência, declarar revisão pendente.
