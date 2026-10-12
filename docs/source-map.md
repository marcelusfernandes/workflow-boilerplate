<!-- Archived source inspection; current usage is in README.md. -->

# Extração do workflow de desenvolvimento

**Estado: levantamento concluído; boilerplate executável ainda não entregue.** A gravação de
novos templates de instruções de agentes não recebeu confirmação do editor. Este documento
registra o desenho e os critérios para continuar, sem alterar a configuração ativa do Apollo.
Não é um instalador e não declara que os hooks estejam ativos ou os gates verdes.

## Fonte e limites

Base inspecionada: `20df50c740ce379019e2bfb2e6b3cc89221b7227`, na árvore principal já com
alterações locais. Perfis/skills/hooks foram inspecionados em leitura, sem serviços, acesso remoto,
segredos ou dados de produção. Os dez TOMLs Codex foram novamente parseados com `tomllib`.
O perfil Codex `companion.toml` estava untracked: sua presença local não garante transporte por Git.

Fontes principais: `AGENTS.md`, `.docs/workflow/orquestracao.md`,
`.docs/workflow/orquestracao-codex.md`, `.docs/workflow/validacao-interface.md`,
`.docs/agentes/README.md`, `.codex/agents/`, `.claude/agents/`, `.codex/skills/`,
`.claude/settings.json`, `.claude/hooks/`, `tools/ci/`, `scripts/prova.mjs`,
`lefthook.yml` e `.github/workflows/`.

## Arquitetura proposta

Separar quatro camadas, com uma única fonte canônica para o conteúdo compartilhado:

1. **Núcleo:** contratos de despacho/retorno, ownership, worktrees, evidência, revisão e memória.
2. **Adaptadores de runtime:** instruções, perfis, sandbox/tools e hooks efetivamente suportados
   pelo cliente. Codex e Claude não são formatos intercambiáveis.
3. **Configuração do projeto:** comandos, caminhos, fronteiras, branches, globs, recursos e gates.
4. **Extensões de stack/produto:** banco, UI, testes de navegador, provedores e contratos externos.

Estrutura de distribuição proposta, não criada nem validada como pacote:

```text
workflow-boilerplate/
  README.md
  source-map.md
  installer/                 # preview por padrão, apply explícito
  core/
    orchestration.md
    dispatch.schema.json
    evidence.schema.json
    project.example.json
    roles/
    skills/
  adapters/
    codex/
    claude/
    git/
    ci/
  extensions/
    README.md                # interface para plugins, sem infraestrutura Apollo
  tests/                     # fixtures sintéticas; sem segredos ou acesso remoto
```

Instalar em projeto existente deve reconciliar arquivos, não substituir suas instruções.
`AGENTS.md`, `CLAUDE.md`, settings e hooks existentes exigem comparação e aprovação de conflito.
Nada modifica configuração global, publica, commita ou instala hooks Git implicitamente.
Um hook Git pode ser compartilhado entre worktrees; respeitar `core.hooksPath` e gestores de hooks.

## Papéis

Há **10 perfis Codex e 8 perfis Claude** no checkout consultado. Modelos escolhidos no Apollo
permanecem intocados; o boilerplate deve permitir seleção explícita/herança, sem fixá-los como
defaults universais ou substituí-los silenciosamente.

| Papel                  | Núcleo/ extensão         | Contrato                                                                              |
| ---------------------- | ------------------------ | ------------------------------------------------------------------------------------- |
| Principal/orquestrador | Núcleo; sessão principal | Coordena donos/dependências, executa trabalho independente, integra quando autorizado |
| Explorador             | Núcleo                   | Levantamento readonly com fontes e limites                                            |
| Implementador          | Núcleo                   | Um escritor/unidade/árvore, prova e entrega revisável                                 |
| QA                     | Núcleo                   | Exercita HEAD/build entregue; não corrige produto para obter verde                    |
| Revisor                | Núcleo                   | Independente do autor, readonly, parecer vinculado ao HEAD                            |
| Documentador           | Núcleo                   | Documenta implementação confirmada, separando plano e resultado                       |
| Operador               | Núcleo                   | Confirma alvo/autorização; verifica efeito após operação                              |
| Banco                  | Extensão                 | Responsável único por migrations/tipos e gates específicos da stack                   |
| Design engineer        | Extensão                 | Escritor da unidade de UI, implementa e navega no resultado                           |
| Usuário simulado       | Extensão                 | Contexto novo e cenário sintético; não concede aprovação humana                       |
| Companion              | Produto Apollo           | Não exportar gravador ou seus contratos como default                                  |

`design_engineer` e `usuario_simulado` não têm equivalente Claude neste checkout.
`isolation: worktree` não é sandbox. Arquivo de perfil não inicia agente, serviço ou navegador.
Modelo/esforço/sandbox solicitado deve ser distinguido da capacidade efetivamente aplicada.

## Skills: extrair procedimentos, não copiar a pasta

As **11 skills Codex** têm bindings Apollo; nenhuma deve ser copiada integralmente como universal.

| Skill atual         | Tratamento                                                                    |
| ------------------- | ----------------------------------------------------------------------------- |
| worktree-segura     | Extrair preservação, dono, retomada e cleanup; remover stack/limites locais   |
| prova               | Extrair regressão, controle negativo, origem da evidência e skips explícitos  |
| issue-e-pr          | Adaptador de provedor; parametrizar repo, labels, template e autorizações     |
| dominio             | Princípios de pureza/fonte única/paridade; regras de produto ficam no destino |
| design-de-interface | Extensão de UI; separar acessibilidade/estados dos tokens Apollo              |
| playwright-e2e      | Extensão Playwright; separar fixture/auth/backend do procedimento             |
| migration           | Extensão de banco; não universalizar RLS/tenant/ledgers/gerador de tipos      |
| supabase-local      | Plugin Supabase, não dependência do núcleo                                    |
| frontend-shadcn     | Plugin da stack frontend, não arquitetura obrigatória                         |
| contrato-gravador   | Produto Apollo; fora do núcleo                                                |
| anthropic-analise   | Produto/provedor; fora do núcleo                                              |

Referências de terceiros só viajam quando a extensão as reutilizar, preservando licenças.
Memória versionada deve começar vazia com seu contrato; não transportar caches, status histórico,
worktrees, dados, gravações, `.env` ou estado pessoal do cliente.

## Hooks e gates

| Camada/fonte                                         | Extração e limite                                                     |
| ---------------------------------------------------- | --------------------------------------------------------------------- |
| `.claude/settings.json:17-60`                        | Adaptador de PreToolUse/PostToolUse/Stop específico do runtime        |
| `.claude/hooks/protege-main.sh:40-114`               | Política de branches/merge; separar avaliação e consulta remota       |
| `.claude/hooks/git-pre-push:15-45`                   | Refs reais e ancestralidade; parametrizar branches protegidas         |
| `.claude/hooks/protege-escrita.sh:108-200`           | Caminhos/ownership parametrizados; papel não é identidade autenticada |
| `.claude/hooks/protege-comandos.sh:60-189`           | Políticas gerais + plugins de provedores; regex não é sandbox de rede |
| `.claude/hooks/formata.sh:38-66`                     | Conveniência opcional, não gate de qualidade                          |
| `.claude/hooks/stop-gate.sh:110-248`                 | Runner configurável, timeout, controle de recursão e requisitos       |
| `tools/ci/scope-check.mjs`, `tools/ci/lib/globs.mjs` | Escopo por globs com sintaxe definida e concessões verificáveis       |
| `tools/ci/lib/contracts.mjs`                         | Motor reaproveitável; regras Hono/Supabase/domain são perfil Apollo   |
| `tools/ci/negative-control.mjs`, `scripts/prova.mjs` | Evidência/controle negativo com runners substituíveis                 |
| `.github/workflows/guarda-main.yml`                  | Detecção posterior, não proteção de servidor                          |

Não usar variáveis de bypass inline, nome de branch como prova de papel ou diretório operacional
como consentimento. Inputs inválidos em guardas de segurança devem falhar fechados.
Gate de escopo detecta violação; não autentica dono nem isola o processo. Hooks locais não
substituem permissões/sandbox do cliente ou proteção no servidor Git.

## Divergências a resolver antes de exportar

- QA Claude manda reset direto, suíte completa e três repetições; QA Codex exige alvo derivado,
  gates/impacto e hipótese concreta. Fontes: `.claude/agents/qa.md:11-19` e
  `.codex/agents/qa.toml:14-26`.
- Implementador Claude pressupõe issue/PR; fluxo Codex admite tarefa local autorizada.
- Revisor Claude prescreve publicação de comentário/labels; fluxo vigente exige autorização.
- Há cópias de skills com evolução diferente. Gerar adaptadores da fonte canônica e verificar drift.
- Instalador Git atual compara bytes, mas copia sobre hook diferente sem composição/backup:
  `.claude/hooks/instalar-git-hooks.sh:20-26`. Boilerplate deve recusar conflito por padrão.
- Ownership de escrita cobre Edit/Write/MultiEdit, não toda escrita por shell. A identidade pode
  vir da branch: `.claude/hooks/protege-escrita.sh:121-126`. Não prometer segurança além disso.

Não corrigir a configuração ativa do Apollo como efeito colateral desta extração.

## Configuração mínima do destino

Nome e mapa do projeto; runtime(s) escolhidos; modelos por papel ou herança; branches protegidas;
comandos por executável/argv/cwd/timeout; paths protegidos e responsáveis; globs da tarefa;
ambientes permitidos; isolamento de recursos; gates obrigatórios; política de skips e revisão.
Configuração declarativa validada, não importação de código para descobrir comandos.

Evidência deve distinguir `passed`, `failed`, `skipped`, `blocked` e `error`, vinculando run ID,
HEAD/base, conteúdo testado, comandos, artefatos, requisitos e motivos. Exit 0 não demonstra
quantidade de testes nem ausência de skips: runners precisam declarar e validar seus resultados.
Revisão, CI e aceite visual não se tornam verdes pelo sucesso do runner local.

## Critérios para considerar o boilerplate entregue

- [ ] Núcleo sem nomes, infraestrutura, paths pessoais ou regras do produto Apollo.
- [ ] Conteúdo canônico e adaptadores gerados/checados sem divergência silenciosa.
- [ ] Instalação preview/apply idempotente, preservando instruções/hooks existentes.
- [ ] Zero instalação de hooks, commits, publicação ou alteração global implícita.
- [ ] Inputs inválidos, paths externos/symlinks, branches protegidas e escopo fora do contrato recusados.
- [ ] Nenhum sucesso com gates vazios, requisito ausente ou evidência de HEAD/árvore antiga.
- [ ] Regressões reais com controle negativo; falha de infraestrutura não conta como prova do defeito.
- [ ] Testes offline em repos sintéticos, espaços/Unicode, staged/unstaged/untracked/deletes/renames.
- [ ] Composição/conflito de hooks, core.hooksPath e worktrees comuns testados.
- [ ] Compatibilidade de formato verificada; ativação/capacidades testadas em runtimes disponíveis.
- [ ] Windows/Linux/macOS: declarar cada plataforma realmente exercitada, sem presumir suporte.
- [ ] Documentação de instalação/adaptação e relatório com HEAD/comandos/resultados/skips/limites.

## Próxima etapa e autorização pendente

É necessário autorizar a criação dos novos templates de instruções dentro desta distribuição.
Isso não autoriza alterar `AGENTS.md`, `CLAUDE.md`, perfis ou hooks ativos do Apollo, nem instalar
em outro projeto ainda não indicado. Depois da autorização, implementar e exercer o pacote
em fixtures sintéticas antes de declarar conclusão. A análise acima não substitui essa prova.
