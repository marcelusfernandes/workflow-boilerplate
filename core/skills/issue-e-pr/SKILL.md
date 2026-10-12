---
name: issue-e-pr
description: "Prepare issues e PRs com escopo e autorização."
---

# issue-e-pr

## Quando usar

Entrega por provedor Git solicitada; tarefa local não exige issue remota.

## Procedimento

1. Revalide issue/PR, base/HEAD/donos antes de reivindicar. Branch não é lock autenticado.
2. Defina objetivo, globs, dependências, aceite/gates. Labels e naming são política do destino.
3. Prepare corpo com resumo, referências, escopo/HEAD, prova negativa, comandos/resultados/
   skips/riscos/pendências. Closes somente para aceite realmente atendido.
4. Publique/comente só dentro da autorização; leia de volta o alvo exato após escrita remota.
5. Revisor independente avalia HEAD atual. Principal integra somente com autorização/gates.

## Armadilhas

Label antigo não valida novo HEAD. CI ausente não é verde. Hook local não substitui proteção
no servidor. Não transformar preparação local em commit/PR/publicação por convenção.

## Verificação

Se publicado, entregue URL/ID/HEAD confirmado; caso contrário, entregue o artefato local.
