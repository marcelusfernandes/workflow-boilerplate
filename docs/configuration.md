# Configuração e contratos

A distribuição usa Python 3.11+ e Git. Sem bibliotecas externas, runtime de aplicativo ou rede
para instalar/testar. Comandos configurados podem acessar rede/dados: revise-os antes de run.

## Projeto

Copie config.example.json para arquivo local fora da distribuição, ajuste project_name, adapters
(codex/claude), roles e gates. Papéis opcionais: banco, design_engineer, usuario_simulado.
Models usa mapas por runtime/papel; reasoning_efforts é mapa por papel Codex. Não há defaults
fixos de modelo. python_command é o executável nos hooks Claude/Git (normalmente python3).

protected_branches lista nomes exatos, protected_paths globs de arquivos proibidos; owned_paths
usa objetos com glob e owners (papéis do catálogo). Ownership é coordenação declarativa,
não autenticação. evidence_max_age_minutes limita frescor. claude_stop_gate é opt-in.

## Gates

Cada gate: name único, argv lista não-vazia de strings, cwd relativo (default .), timeout_seconds
(default 300), e result_file opcional relativo à raiz. Nunca uma string de shell. Para executar
pipelines, crie script específico do projeto e trate-o como código confiável. No Windows,
shims .cmd/.bat de ferramentas precisam de argv compatível com o OS; prefira executável real.

Sem result_file, passed significa exit 0 do comando, não quantidade de testes/cobertura/skips.
Com result_file, o runner remove relatório antigo antes da execução e exige JSON novo:

```json
{ "status": "passed", "total": 3, "failed": 0, "skipped": 0, "reason": "" }
```

status aceita passed/failed/skipped/blocked/error; contagens são inteiros não-negativos e
failed+skipped <= total. passed exige total>0, failed=0 e skipped=0. Skip nunca vira verde.
Comando não-zero, timeout ou executável ausente não contam como passed. Artefatos de runner
não devem conter segredos/saída bruta; summary guarda metadados, não stdout/stderr do comando.

## Tarefa/escopo

Copie task.example.json para task.json e configure id, owner, base_ref existente e allowed_globs.
`scope` compara base com árvore corrente (committed/staged/unstaged/untracked), incluindo
caminho antigo/novo de renames. base_ref deve reconciliar mudanças pré-existentes.
Sem task.json, o gate scope declara skipped; ele é obrigatório quando um contrato foi criado.
Campos extras acceptance/dependencies/resources/authorized_remote_actions documentam despacho,
mas não concedem permissões automaticamente. Branch/owner autodeclarados não autenticam papel.

Globs POSIX: * não atravessa /; ** atravessa diretórios; **/ também casa zero diretórios;
? casa um caractere, [] e brace expansion não são suportados. Paths/globs são relativos,
sem .., backslash ou absoluto. .env.example é protegido pelos defaults de .env.*: libere somente
se a política do projeto permitir explicitamente. Nunca ler conteúdo de arquivos protegidos.

## Evidência

Summary em .workflow/artifacts/summary.json identifica HEAD, conteúdo de arquivos + untracked
não ignorados, index Git (mode/OID/stage), config, contrato task, OID resolvido da base,
timestamps, run_id e resultados. Alteração somente staged também invalida a evidência.
Scope une diferenças working-tree e cached contra a base; index com conflito é recusado.
Gates executam a working tree: registrar o index não prova que blobs staged divergentes foram
testados. Reconcile staged/working tree antes de usar o relatório para preparar commit.
Artefatos/lock/bytecode são
excluídos. Arquivos ignorados não entram: se configuração/fixtures ignoradas afetarem testes,
registre essa limitação e promova metadados não sensíveis a um arquivo incluído na evidência.
Symlink/junction para fora é recusado antes de ler; arquivo protegido é recusado sem conteúdo.

`check-evidence` verifica SHA/conteúdo/config/task e prazo. Não verifica aprovação independente,
CI, aceite visual ou controle negativo por si só. Os comandos/protocolo continuam confiáveis;
agente que pode alterar scripts/config/relatório pode também mentir. Não é selo de segurança.
Lock serializa apenas este runner; remoção manual de lock exige confirmar que processo acabou.

## Exclusividade e concorrência do filesystem

Instale somente em diretório confiável, reservado a um escritor. O instalador valida paths no
preflight, antes/depois de mkdir e após open antes de escrever bytes; o runner revalida result_file
depois do gate. Isso detecta trocas entre fases, mas resolve/check/open não é operação atômica
resistente a um adversário que possa trocar ancestrais entre syscalls. Nenhuma garantia de sandbox
ou no-follow por handles é implementada. Em interrupção, o instalador informa criações concluídas;
falha no arquivo corrente pode deixar criação parcial. Não remova recursos externos por rotina.
