# Bootcamp de Automação — Cisco Catalyst SD-WAN

Quatro horas para quem **já domina SD-WAN e está aprendendo automação**.

Aqui não se ensina o que é TLOC, OMP ou config group — presume-se que você
sabe. Ensina-se automação usando esses objetos como vocabulário. A frase que
resume o dia:

> Você já sabe o que é um config group. Hoje você aprende como ele é em JSON
> na rede — e por que isso muda o que dá para fazer com ele.

## O arco

Você não faz cinco exercícios soltos. Você constrói **uma ferramenta**, camada
por camada, e sai com ela funcionando.

| Módulo | Tempo | Automação | SD-WAN |
|---|---|---|---|
| [01 — Conectando ao Manager](01-conectando-ao-manager/) | 45 min | Sessões HTTP, segredo fora do código | Handshake `j_security_check` + `X-XSRF-TOKEN` |
| [02 — Estado como dado](02-estado-operacional/) | 50 min | Modelagem, snapshot, diff | Control connections, BFD, OMP, app-route |
| [03 — Config Groups](03-config-groups/) | 50 min | Idempotência, tarefa assíncrona, dry-run | Feature profiles, parcels, deploy |
| [04 — Terraform](04-terraform/) | 45 min | Declarativo, state, drift | Config group como código |
| [05 — Pipeline](05-pipeline/) | 30 min | CI/CD, verificação, rollback | Precheck/postcheck do fabric |

Sobram 20 minutos para abertura, intervalo e o fechamento. É de propósito.

## Antes de começar

```bash
git clone https://github.com/autonetops/sdwan_automation.git
cd sdwan_automation

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# A suíte offline tem que passar ANTES de você tocar no lab.
python -m pytest -q
```

### Credenciais

Elas vivem no **HashiCorp Vault** (`https://vault.autonetops.com`), nunca no
repositório. Você recebe um token de leitura no início do bootcamp.

```bash
export VAULT_ADDR=https://vault.autonetops.com
export VAULT_TOKEN=hvs.xxxxxxxx      # entregue pelo instrutor
export WS_ALUNO=07                   # o seu número — vira prefixo dos objetos

source scripts/vault-env.sh          # exporta VMANAGE_* e TF_VAR_*
```

O segredo fica em `secret/sdwan/manager` com as chaves `url`, `username` e
`password`. Todo o código lê por uma função só: `sdwan_toolkit.vault.load_credentials()`.

> **Por que Vault e não um `.env`?** Porque o `.env` de hoje é o commit
> acidental de amanhã. E porque revogar um token é instantâneo; trocar uma
> senha que dezoito pessoas copiaram, não.

## O lab é compartilhado

Um Manager para a turma inteira. Duas regras que não são burocracia:

1. **Tudo que você criar leva o prefixo `ws<NN>-`** (o seu `WS_ALUNO`). Sem
   isso vocês sobrescrevem o trabalho uns dos outros.
2. **Não tire o rate limit do cliente.** Endpoints `/device/*` são real-time:
   o Manager consulta o equipamento pelo plano de controle. Vinte pessoas em
   laço fechado transformam a aula num incidente. O `RateLimiter` em
   `sdwan_toolkit/client.py` existe por isso.

## Como estudar depois

Cada módulo tem `exercicio.py` com TODOs e uma pasta `solution/` com a versão
pronta e comentada. Compare — mas só depois de tentar.

A suíte de testes roda **sem lab nenhum**, contra um Manager de mentira em
`tests/conftest.py`. É assim que você continua praticando na semana seguinte,
no avião, sem VPN.

```bash
python -m pytest -q                        # tudo
python -m pytest tests/test_diff.py -q     # só o juiz da mudança
```

## O toolkit

```
sdwan_toolkit/
├── vault.py        credenciais (módulo 1)
├── client.py       sessão autenticada + rate limit (módulo 1)
├── inventory.py    quem é quem no fabric (módulo 1)
├── state.py        retrato operacional (módulo 2)
├── diff.py         o juiz da mudança (módulo 2)
├── tasks.py        polling de tarefa assíncrona (módulo 3)
└── configgroup.py  mudança declarativa (módulo 3)
```

## O que ficou de fora

Consciente, por causa das quatro horas: automação orientada a eventos
(webhooks de alarme), a query DSL de estatísticas agregadas, onboarding
ZTP/PnP e vManage multi-tenant. Todos valem — nenhum cabe. Ficam como o
próximo passo.

---

Feito por [AutoNetOps](https://autonetops.com). Para a versão de
**configuração** (não automação) de SD-WAN, veja o workbook prático na
plataforma.
