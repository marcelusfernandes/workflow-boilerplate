# Exemplos mínimos

Overrides de config.example.json; ajuste a stack/comandos reais antes de instalar.
python.json demonstra unittest; node.json o runner do Node. São exemplos de argv, não prova
que testes existem ou foram coletados. Sem result_file, o runner só registra exit code.
Ferramentas/scripts do destino precisam falhar quando houver defeito; zero testes/skip com
exit 0 exige adaptador de protocolo estruturado para não virar verde indevido.

Defina lint/tipos/build/e2e conforme manifestos. No Windows, escolha executáveis reais ou
scripts compatíveis: shims .cmd não são presumidos portáveis com subprocess sem shell.
Para modelos, use models.codex/models.claude por nome de papel e reasoning_efforts Codex;
nenhum ID do projeto de origem é imposto. Inclua roles opcionais apenas quando pertinentes.
