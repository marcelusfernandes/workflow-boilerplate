---
name: recursos-locais
description: "Isole serviços, fixtures e artefatos de teste."
---

# recursos-locais

## Quando usar

Banco, integração/e2e, portas, containers, contas ou sessão de navegador.

## Procedimento

1. Confirme ambiente/alvo/responsável por fonte verificável antes do acesso. Incerto ou produção
   não é alvo autorizado. Não descobrir ambiente lendo dados de produção.
2. Reserve recursos próprios ou serialize os compartilhados. Confirme capacidade efetiva.
3. Use fixtures sintéticas, nunca dados reais/gravações pessoais ou segredos em relatórios.
4. Reset/cleanup exigem alvo e dono confirmados; use adaptador da stack do destino.
5. Exercite serviço real quando o aceite exigir, leia estado resultante e limpe só o criado.

## Armadilhas

Uma aba não isola cookies/localStorage; worktree não isola banco/volume/porta. Dublê de protocolo
não comprova efeito nativo. Não fabrique metadados de stack ou preparação do sucesso por API.

## Verificação

Relate alvo sem segredos, fixtures, comandos/efeitos/cleanup, recursos em uso e limites da camada.
