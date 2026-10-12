# Integração com CI

Instalação não modifica workflows do provedor. O responsável configura checkout/HEAD real,
Python >=3.11, Git, dependências/serviços do projeto e fixtures sintéticas isoladas.
Instale/versione os arquivos do workflow no projeto antes de usar o runner em CI.

Passos de job, com a ferramenta/shell adequada ao provedor:

1. Execute setup/testes/gates exigidos pelo manifesto e política do destino.
2. Execute `python3 .workflow/workflow.py run` para gates configurados, sem mascarar exit code.
3. Publique summary e relatórios permitidos como artefatos; nunca stdout/segredos/dados reais.
4. Exija status de checks estáveis no HEAD atual no servidor e revisão independente.

Para a distribuição, use `python3 workflow.py validate` e `python3 verify.py`.

Não há Actions/copias de versões/providers hardcoded. Jobs de banco/e2e exigem adaptadores
reais para a stack; não presuma Supabase/Docker nem faça reset remoto. CI sem execução ou com
skip/blocked não é verde. Controlar branch depois do push é detecção, não prevenção.
Controle negativo deve ser implementado para o comportamento do projeto, com falha discriminante;
a suíte desta distribuição não implementa overlay automático dos testes em todo tipo de projeto.
