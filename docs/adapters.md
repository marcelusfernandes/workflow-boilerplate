# Adaptadores e limites

## Codex

Perfis standalone TOML em `.codex/agents/`; skills em `.agents/skills`. Modelo e esforço são
omitidos para herdar a sessão, salvo escolhas explícitas. Sandbox é solicitado pelo perfil,
mas capacidades/permissões efetivas dependem do runtime. Não habilitamos experimental flags
ou escrevemos `.codex/config.toml`/configuração global por rotina. Reabra/recarregue o cliente
conforme necessário. Arquivos válidos não comprovam carregamento, spawn ou modelo aplicado.

## Claude Code

Perfis Markdown com frontmatter em `.claude/agents`, `model: inherit` por padrão; skills em
`.claude/skills`. Settings registram PreToolUse para Bash/Edit/Write/MultiEdit e Stop opcional.
Guard recebe JSON stdin e nega com exit 2; onFailure=block evita falha aberta em clientes que
suportam o campo. Clientes antigos podem ignorar campos: confira versão/configuração ativa.
Não há PostToolUse que reescreva arquivos automaticamente. Stop só verifica evidência quando
ativado e evita recursão; não inicia testes/serviços ou impede uma interrupção pelo usuário.

Readonly solicita restrição de ferramentas/sandbox, não uma identidade autenticada. Bash pode
escrever, o parser de comandos é deliberadamente parcial, e uma ferramenta não coberta pode
escapar do guard. Use permissões reais do cliente/OS; não trate hook como sandbox de rede.

## Git

`install-git-hook` é separado da instalação de arquivos e exige --apply. Recusa hooks existentes
conflitantes e core.hooksPath customizado; não compõe gestores automaticamente. Localiza o
hooks dir do Git, inclusive comum entre worktrees, e informa esse escopo. Pre-push avalia refs
reais, branches protegidas e ancestralidade; não depende da branch corrente. Não publica nada.
Hooks são locais/removíveis; servidor exige proteção própria. Sem válvulas de bypass em env.

## Fontes oficiais consultadas

- Codex custom agents: https://developers.openai.com/codex/subagents
- Codex skills: https://developers.openai.com/codex/skills
- Claude subagents: https://code.claude.com/docs/en/sub-agents
- Claude hooks: https://code.claude.com/docs/en/hooks

Formatos conferidos na documentação; os testes offline exercitam scripts/payloads e geração,
não a ativação dentro dos clientes. Não alegar navegação, CI, sandbox efetivo ou desempenho
comparativo de modelos a partir desses testes. A inspeção de origem está em source-map.md
na distribuição; não é política de produto ou evidência runtime do destino.
