# Extensões de projeto

O núcleo não inclui schema/RLS, frameworks de UI, provedores de LLM ou protocolos de produto.
Acrescente procedimentos pertinentes nas skills do projeto, preserve licenças de referências
reutilizadas e defina a descoberta conforme o runtime. Não copie infraestrutura/data/segredos.

1. Registre stack, contratos, mapa de código, invariantes e recursos em .workflow/project.md.
2. Crie skill com nome/description claros, procedimento, armadilhas e verificação por evidência.
3. Configure comandos reais em config.json, ownership de paths e responsável único por recursos.
4. Mantenha a semântica compartilhada numa fonte; derive/checke cópias entre runtimes.
5. Prove contrato e efeito real separadamente: dublê, interface e plataforma nativa não são iguais.

Papéis banco/design_engineer/usuario_simulado já existem no catálogo, mas são opt-in.
Especialista em contrato de um produto deve ser criado no destino, não transformado em default.
Provas comportamentais precisam de controle negativo; docs/config têm validação proporcional.
