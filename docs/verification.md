# Verificação da distribuição

O estado final legível por máquina é produzido por `python3 verify.py` em
`artifacts/verification.json`. O script registra resultado real da suíte, totais/falhas/erros/
skips, plataforma/interpreter, timestamps e fingerprint do código da distribuição.
Não contém fixture real, credencial ou saída bruta de serviços.

Comandos:

```sh
python3 workflow.py validate
python3 workflow.py doctor
python3 verify.py
python verify.py --report verification-py314.json
```

## Cobertura

Os testes usam repositórios/contas/arquivos sintéticos em TemporaryDirectory; no ambiente Hermes,
configure TMPDIR ao scratch do agente. Nunca usam o checkout de origem como alvo de instalação.

- Preview/apply/idempotência; conflitos existentes sem sobrescrita.
- Catálogo canonical e modelos selecionados versus herança; TOML e frontmatter gerados.
- Gates passando/falhando, zero gates, executável ausente, timeout e mutação da árvore durante gate.
- Protocolo estruturado: zero testes/skips/relatórios ausentes recusados; relatório antigo removido.
- Evidência invalidada por conteúdo/HEAD/index/tarefa/base resolvida/prazo; lock preserva dono existente.
- Scope em staged/unstaged/untracked, Unicode/espaços, deletes e caminhos antigo/novo de rename.
- Guard Claude Write/Bash, input inválido, ownership, alvo externo e recursão Stop.
- Junction real no Windows (symlink no ramo POSIX do teste), recusada antes de escrita externa.
- Junction criada pelo gate no result_file recusada; troca injetada após mkdir detectada pelo apply.
- Index-only com working file restaurado e base nomeada movida durante gate não produzem verde.
- Summary malformado causa decision:block no Stop, sem traceback/protocolo aberto.
- Instalação explícita do Git hook, hook existente/custom hooksPath e linked worktree comum.
- **Git push local real** a remoto bare sintético: feature permitida, main recusada e ausência
  da ref main lida de volta. Update não-fast-forward recusado por ancestralidade.

## Controle negativo

Os fluxos principais foram exercitados primeiro sem comandos implementados (instalação,
runner/evidência, scope/Claude e Git hook), depois passaram com a implementação. Inputs inválidos
com owner objeto e configuração desconhecida tiveram regressões vermelhas antes da correção.
Esses controles provam o pacote, não dispensam negativos das futuras mudanças de produto.

A revisão independente reproduziu lacunas no snapshot inicial. As regressões index-only,
base movida durante gate e troca de ancestral após mkdir foram executadas vermelhas antes da
correção. O caso de troca de ancestral precisou de Python 3.14 para reproduzir: Python 3.11
recusava a abertura por um erro distinto. A revisão de fechamento é restrita às regiões/gates,
sem declarar ativação do cliente ou ausência universal de riscos.

## Limites

A execução registrada neste host é Windows com Git Bash e Python. Linux/macOS não foram
exercitados aqui. Junction de diretório não comprova todos os tipos de reparse point/symlink
final de arquivo. Formatos/client docs foram consultados, mas ativação/spawn real no Codex/Claude,
modelos disponíveis, sandbox efetivo, navegador, CI e proteção no servidor não foram comprovados.

Hooks são locais e removíveis. Shell guard é parcial. Ownership/task/relatório podem ser editados
por quem tem escrita: coordenação, não autenticação/atestado. Subprocessos/serviços de gates têm
cleanup próprio; timeout da ferramenta principal não comprova fim de todos os descendentes.
Arquivos ignorados/ambiente não entram automaticamente na evidência. Exit 0 só vira contagem de
provas com result_file; comandos sem protocolo não comprovam coleta >0/ausência de skips.

Resolve/check/open não fornece atomicidade contra escritor adversarial concorrente. A instalação
exige diretório confiável e um escritor; a troca injetada testada é uma fase específica, não prova
de todas as janelas de TOCTOU. Gates testam working tree, não blobs staged divergentes por si só.

A distribuição é versionada neste repositório, com `main` como branch principal. O SHA no
source-map é a fonte Apollo inspecionada, não um HEAD desta pasta. Use o fingerprint do
relatório para identificar este artefato.
