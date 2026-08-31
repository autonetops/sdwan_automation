# Módulo 5 — Pipeline de mudança validada (30 min)

O capstone. Tudo que você construiu, junto.

```
retrato ANTES  →  aplica a mudança  →  retrato DEPOIS  →  compara
                                                            │
                                            regrediu?  →  ROLLBACK
```

## A tese do bootcamp

> Mudança sem verificação automática não é automação. É digitação mais rápida.

Um script que empurra config mais rápido que você só fez você errar mais
rápido. O que muda o jogo é o fabric conseguir **reprovar a própria mudança**.

## Mãos à obra

```bash
cd 05-pipeline
python pipeline.py --dry-run    # só os retratos, não muda nada
python pipeline.py              # o ciclo completo
```

Código de saída `0` = fabric íntegro. `1` = regrediu (e já fez rollback). É
esse código que o GitHub Actions usa para reprovar o merge.

## As três decisões que o exercício cobra

Os TODOs não têm resposta única. Eles têm **justificativa**:

1. **Precheck deve abortar se algum device já está fora?**
   Num lab compartilhado, abortar sempre é inviável. Mas o `compare()` só olha
   a diferença — um device que já estava fora antes e depois não gera achado
   nenhum. Você precisa pelo menos *registrar*.

2. **Quanto esperar antes do postcheck?**
   BFD e OMP não reconvergem instantaneamente. Verificar cedo demais acusa
   regressão que não existe. E um pipeline que grita lobo é um pipeline que as
   pessoas desligam.

3. **Rollback via `apply` com valor antigo, ou `destroy`?**
   Destruir o config group inteiro é mais violento que a mudança que você está
   desfazendo. **Rollback que causa mais impacto que o problema original não é
   rollback — é um segundo incidente.**

## O workflow

`.github/workflows/change-validation.yml` roda isto de verdade. Repare no
desenho:

- **PR** → testes offline + `terraform plan`. Seguro, roda em qualquer PR.
- **push para main** → `apply` com verificação e rollback, atrás de um
  *environment* com approval.
- **Segredos** → o único segredo no GitHub é o token do Vault. Tudo o mais
  vem do Vault em runtime, e os retratos ficam anexados ao run como evidência.

Automação boa não é a que aplica mais rápido. É a que erra em direção ao lado
seguro.

## Onde continuar

- Trocar o rollback caseiro pelo **config-rollback timer** nativo do Manager.
- Alarmes do Manager via webhook → automação orientada a eventos.
- `terraform plan` comentado automaticamente no PR.
- Estender o `compare()` com SLA de app-route, não só contagem de sessões.
