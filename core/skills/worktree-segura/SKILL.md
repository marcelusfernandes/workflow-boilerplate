---
name: worktree-segura
description: "Prepare e encerre worktrees sem perder trabalho."
---

# worktree-segura

## Quando usar

Preparação, retomada, paralelismo ou encerramento de árvore Git.

## Procedimento

1. Confira caminho, git status/HEAD, git worktree list, dono e processos. Falta de ref remota
   não autoriza limpeza; preserve alterações/commits e reconcilie dependências.
2. Uma unidade/branch e um escritor por árvore. git worktree add não copia uncommitted,
   ignorados ou segredos. Prepare somente ambiente local explicitamente necessário/autorizado.
3. Reserve serviços, portas, contas, fixtures e artefatos. Worktree não isola banco/cookies.
4. Branch publicada integra base por merge, sem reescrever histórico ou forçar push.
5. Antes de remover árvore, confira dono/processos, mudanças e commits não publicados;
   pare somente recursos próprios. Não usar stash/reset --hard/clean por convenção.

## Armadilhas

Pasta copiada não é worktree registrado; pausa de agente não libera banco. Hooks Git podem
ser compartilhados. Instalação de dependências pode rodar prepare/hooks: verifique antes.

## Verificação

Entregue caminho/HEAD, diff, recursos ocupados/liberados e pendências confirmados por ferramentas.
