# {{PROJECT_NAME}}

## Condução

- Leve o pedido até o resultado verificável. Resolva escolhas rotineiras no escopo; escale
  somente autorização, decisão de produto, recurso ou saída segura realmente ausentes.
- Confirme caminho, branch/HEAD, alterações, donos e recursos antes de agir. Preserve trabalho
  existente: sem stash, reset --hard, clean, restauração destrutiva ou push forçado.
- Commit, publicação, mensagens, merge e deploy exigem autorização da tarefa. Não são implícitos.
- Nunca leia segredos, dados pessoais ou produção. Use fixtures sintéticas e confirme o alvo
  antes de operações externas. Ambiente incerto não é alvo autorizado.
- Leia `.workflow/project.md` para arquitetura, comandos e contratos locais. Não invente
  símbolos, dependências, serviços ou infraestrutura. Trace definições e consumidores.
- Conversa e interface em português; código, commits e GitHub em inglês, salvo pedido diferente.

## Coordenação

Leia `.workflow/docs/orchestration.md`, `.workflow/memory/MEMORY.md` e somente as notas/skills
pertinentes. Skills estão em `.agents/skills` no Codex e `.claude/skills` no Claude.
Perfis descrevem papéis; não iniciam agentes, worktrees ou serviços por si só.

Delegue unidades independentes quando houver ganho e suporte efetivo. Um escritor por árvore,
um responsável por recurso compartilhado. O principal também executa trabalho independente.
Despacho inclui objetivo, caminho/HEAD/base/branch, dono, globs, dependências, aceite, skills,
gates e autorizações. Modelos/esforços são escolhas do usuário, nunca substituídos silenciosamente.
Configuração não concede navegador, sandbox ou permissões ausentes no runtime.

Migrations/tipos gerados, lockfile, hooks/CI e recursos compartilhados têm responsáveis únicos.
Configure os caminhos reais no projeto. Branch publicada integra base por merge, não force/rebase.
Falha compreendida volta ao dono com critério objetivo; sem progresso, mude hipótese/reprodução.
Não bloqueie por contagem fixa de rodadas nem repita tentativas sem informação nova.

## Prova e revisão

Mudança comportamental exige regressão e controle negativo pelo defeito correto. Docs/config
usam validação estrutural proporcional; hooks e código executável não são exceção documental.
Configure comandos reais em `.workflow/config.json` e execute os gates declarados com
`python3 .workflow/workflow.py run`. Não confunda sucesso do comando com cobertura/aceite.
Para escopo, copie `.workflow/task.example.json` para `.workflow/task.json` e ajuste a base/globs.

O revisor é independente do autor e não edita produto. QA exercita o HEAD/build entregue.
Aceite visual exige navegação/inspeção quando possível; teste DOM não prova aparência.
CI indisponível não é verde, evidência antiga não valida árvore nova e relato simulado não é
aprovação humana. Merge pertence ao principal, somente com autorização e gates aplicáveis.
Depois do verde, repetir checks exige mudança, falha ou dúvida concreta ainda aberta.

## Encerramento

Entregue HEAD/diff, comandos, resultados/skips, origem/limites da evidência e pendências.
Registre aprendizado confirmado com fonte, alcance e condição de revalidação. Skills guardam
procedimentos, ADRs decisões, handoffs progresso; memória não guarda segredos ou status volátil.
Antes de remover worktree/recursos, confirme dono/processos e preserve alterações/commits.
Hooks locais são defesa em camadas, não sandbox ou proteção de servidor. Não contorne guards.
