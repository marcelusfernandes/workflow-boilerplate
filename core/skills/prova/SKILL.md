---
name: prova
description: "Valide mudanças com regressão e evidência do HEAD."
---

# prova

## Quando usar

Mudança de comportamento, configuração/hook ou preparação de entrega.

## Procedimento

1. Leia aceite/manifestos; defina testes observáveis e oráculo independente. Não prove só o dublê.
2. Para comportamento, execute regressão contra o defeito/ausência/stub compilável e confirme
   vermelho pela causa correta. Instalação quebrada ou erro de import não bastam por si só.
3. Implemente e execute testes afetados + gates obrigatórios. Preserve negativo já comprovado.
   Docs/config têm verificação estrutural proporcional; hooks não são exceção documental.
4. Configure argv/cwd/timeout em .workflow/config.json e execute o runner com a ferramenta de
   terminal do cliente: `python3 .workflow/workflow.py run`. Gates são código confiável:
   revise comandos/ambiente; o runner não faz reset de banco ou instalação automaticamente.
5. Se precisar contar testes/skips, configure result_file e emita o protocolo JSON documentado.
   Sem protocolo, exit 0 prova execução do comando, não zero skips nem número de testes.

## Armadilhas

Gates vazios/requisito ausente não são verde. Evidência velha perde validade com HEAD/conteúdo/
configuração. CI/revisão/UI/negativo não ficam verdes pelo runner local. Rode sequencialmente.
Lock protege apenas esta bancada; serviços externos exigem coordenação própria.

## Verificação

Use check-evidence e relate HEAD, comandos/resultados/skips/origem/limites. Depois do verde,
repetir exige mudança/falha/dúvida concreta. Não fabrique resultados nem cobertura.
