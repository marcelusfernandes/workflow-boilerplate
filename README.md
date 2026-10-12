# Workflow Boilerplate

Workflow reutilizável com agentes, skills, hooks e gates independentes de stack.
**Python 3.11+ e Git**, sem bibliotecas externas para instalar/validar/testar a distribuição.

## Conteúdo

- **6 papéis padrão + 3 opcionais**, em fonte canônica, renderizados para Codex e Claude.
- **7 skills**: worktrees, prova, domínio, recursos locais, revisão, issues/PRs e memória.
- Modelos herdados da sessão ou escolhidos explicitamente por papel, sem defaults Apollo.
- Instalador preview/apply, idempotente para conteúdo igual, recusando conflitos/symlinks.
- Runner por argv/cwd/timeout e evidência ligada a HEAD/conteúdo/config/tarefa/prazo.
- Guard Claude PreToolUse e Stop opcional; hook Git pre-push instalado separadamente.

Não inicializa Git, instala dependências, sobe serviços, copia segredos, commita, publica,
ou altera configurações globais. Sem dependência de Supabase, pnpm, shadcn ou gravador.

## Começar

```sh
python3 workflow.py doctor
python3 workflow.py validate
python3 -m unittest discover -s tests -v
```

No Windows, python também serve se aponta para 3.11+. Configure python_command ao executável
acessível pelo Git/Claude. Hook Git usa sh (Git Bash no Windows testado). Fonte compartilhada
em core/roles.json e core/skills/; instruções em core/AGENTS.md e core/orchestration.md.

## Instalar em outro projeto

1. Copie config.example.json para um arquivo próprio e ajuste project_name, adapters,
   roles, gates e políticas. Examples contém comandos mínimos, não descoberta de stack.
2. Use como target a raiz de um repositório Git existente. Substitua os paths nos comandos:

```sh
python3 workflow.py install --target "path/to/project" --config "project-config.json"
python3 workflow.py install --target "path/to/project" --config "project-config.json" --apply
```

Preview não escreve. Apply compara todo o plano antes de criar. Arquivos existentes diferentes,
incluindo instruções/settings, causam recusa sem sobrescrita. Reconcile conflitos manualmente;
sem --force ou bypass. Upgrades não apagam personalizações. Erro de IO na escrita pode deixar
arquivos novos parciais; compare com o plano sem restaurar/deletar trabalho preexistente.
Reserve diretório confiável e um escritor durante instalação. Paths são revalidados na escrita,
mas não há proteção atômica contra troca adversarial de ancestrais entre syscalls (TOCTOU).

Estrutura gerada no destino:

```text
AGENTS.md
CLAUDE.md                             # somente Claude
.workflow/
  workflow.py, engine.py, roles.json, config.json
  project.md, task.example.json
  docs/, memory/, .gitignore
.agents/skills/                       # Codex
.codex/agents/                        # Codex
.claude/agents/, skills/, settings.json    # Claude
```

3. Preencha .workflow/project.md com arquitetura, contratos, recursos e comandos reais.
   Papéis padrão: explorador, implementador, qa, revisor, documentador e operador.
   Principal/orquestrador é a sessão coordenadora. Opcionais: banco, design_engineer,
   usuario_simulado. Inclua-os em roles apenas se pertinentes.
4. Configure gates reais; o exemplo padrão fica vazio deliberadamente, sem declarar verde.
   No destino:

```sh
python3 .workflow/workflow.py doctor
python3 .workflow/workflow.py run
python3 .workflow/workflow.py check-evidence
```

Summary fica em .workflow/artifacts/summary.json, sem stdout/stderr bruto. Exit 0 sem
result_file prova somente o comando, não contagens/cobertura. Para exigir total>0 e zero
falhas/skips, emita o protocolo JSON em docs/configuration.md. Gates são código confiável:
revise comandos/ambiente; não há reset/instalação automático.

5. Para tarefa delimitada, copie task.example.json para .workflow/task.json, configure
   base/owner/globs e execute `python3 .workflow/workflow.py scope`. Reconcile mudanças
   preexistentes pela base correta. Com contrato, violação impede gates; sem contrato,
   scope declara skipped/não obrigatório. Dono declarado não é identidade autenticada.

## Hook Git opcional

```sh
python3 .workflow/workflow.py install-git-hook
python3 .workflow/workflow.py install-git-hook --apply
```

Recusa hook diferente ou core.hooksPath customizado. Composição com gestores é manual.
Hooks podem ser compartilhados entre worktrees; cada árvore usada precisa do runtime.
Pre-push avalia refs reais, branches protegidas e ancestralidade; não publica nada.
Hook local não substitui proteção no servidor. Guard Claude bloqueia gh pr merge por padrão;
integração autorizada ocorre fora desse guard, coordenada, nunca por bypass inline.
Stop é opt-in; não inicia testes/serviços automaticamente e evita recursão.

## Organização e documentação

- core/: fonte canônica; installer.py renderiza adaptadores sem cópias manuais concorrentes.
- engine.py: política/evidência; workflow.py: CLI; validation.py: catálogo/referências/formatos/drift.
- docs/configuration.md: config, globs, escopo, protocolo de gates e evidência.
- docs/adapters.md: formatos oficiais e capacidades solicitadas versus efetivas.
- docs/verification.md: cobertura realmente exercitada e limites.
- docs/source-map.md: levantamento anterior preservado, não política vigente do destino.
- adapters/ci/README.md: integração manual com CI, sem jobs instalados implicitamente.
- extensions/README.md: regras próprias de stack/produto fora do núcleo.

Guard Bash é parcial, não parser completo ou sandbox de rede. Evidência local não é atestado
antifraude, revisão ou CI. Arquivos ignorados não entram no fingerprint; declare dependências
ignoradas/ambientais que afetem testes. Subprocessos/serviços criados por gates precisam de
cleanup próprio. Não transportar caches, .env, gravações ou status remoto de memórias.

Exercitado no Windows; Linux/macOS e ativação nativa dos clientes são limites não comprovados.
Capacidades/modelos efetivamente carregados precisam ser verificados na sessão. Nenhuma
configuração ativa do Apollo foi alterada. A distribuição é versionada neste repositório;
a branch principal é `main`.
