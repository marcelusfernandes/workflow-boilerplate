# Workflow compartilhado

## Preparar

1. Reconcile pedido, caminho/HEAD/diff, base, branches/worktrees, dependências, donos e recursos.
   Falta de PR/ref remota não prova abandono. Tarefa local não exige issue remota.
2. Defina unidades verificáveis e independentes, um escritor por árvore. Recursos compartilhados,
   migrations/tipos, lockfile e hooks/CI são coordenados por um responsável único.
3. Despache com objetivo, caminho absoluto, branch/HEAD/base, dono, globs, dependências, aceite,
   skills, gates, recursos e autorizações. Perfis/modelos não ampliam permissões da sessão.
4. Worktree real não copia uncommitted/ignorados. Isole banco/portas, sessões/fixtures e relatórios,
   não apenas Git. Não copie segredos ou dados reais como parte deste workflow.
5. Delegue somente quando útil e suportado. O principal também trabalha em parte independente.

## Implementar e corrigir

Localize definição e consumidores antes de editar. Regra compartilhada tem uma fonte única
estabelecida pelo projeto, sem pressupor layout de monorepo. Para comportamento, escreva
regressão e confirme vermelho pelo defeito, depois verde pela implementação. Config/docs
usam prova estrutural proporcional. Hooks/permissões/executáveis não são exceção documental.

Falha compreendida recebe correção com critério objetivo. Sem progresso, mude hipótese,
reduza reprodução ou encaminhe diagnóstico. Escale decisão/autorização/recurso realmente
faltante; não pare por contagem fixa de rodadas nem repita tentativas idênticas.
Retome unidade/worktree existente ou combine transferência explícita; não duplique escritor.

## Provar e revisar

Configure gates reais de lint/tipos/testes/build/integracão segundo impacto. O runner executa
argv sem shell e captura exit codes; não interpreta automaticamente quantidade de testes.
Gates com protocolo estruturado devem reportar passed/failed/skipped/blocked/error.
Confira relatório ligado ao HEAD, conteúdo e configuração. Requisito ausente ou CI não
executado não é verde. Relatório local não substitui revisão/aceite visual/controle negativo.

Revisor independente é readonly; QA exercita HEAD/build e não corrige produto. Frontend tem
um escritor: design engineer ou implementador. Quando aceite é visual, navegue e inspecione.
Usuário simulado recebe contexto novo e tarefa sintética, sem solução interna para testar
descobribilidade. Relato não equivale a pesquisa com pessoa ou aprovação de produto.
Confirme capacidades do navegador e dono da sessão; abas não isolam cookies/banco.

Principal integra apenas se autorizado, com revisão e gates atuais. Branch publicada integra
base por merge, sem reescrever histórico. Verifique efeito de escrita remota no alvo exato.

## Encerrar

Retorno inclui HEAD/diff, aceite, comandos/resultados/skips, artefatos/origem/limites e pendências.
Memória durável guarda fonte, alcance e revalidação; handoffs guardam status temporário.
Antes de remover árvore ou parar serviço, confira dono/processos, mudanças e commits não
publicados. Não limpe volumes/recursos alheios. Ausência de branch remota não autoriza exclusão.
