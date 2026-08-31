# Cisco Catalyst SD-WAN — Automation Bootcamp

Four hours for engineers who **already know SD-WAN and are learning automation**.

Nobody here will explain what a TLOC, OMP or config group is — you know that
already. What you'll learn is automation, using those objects as the
vocabulary. The sentence that sums up the day:

> You already know what a config group is. Today you learn what it looks like
> as JSON on the wire — and why that changes what you can do with it.

## The arc

You don't do five disconnected exercises. You build **one tool**, layer by
layer, and you leave with it working.

| Module | Time | Automation | SD-WAN |
|---|---|---|---|
| [01 — Connecting to the Manager](01-connecting-to-manager/) | 45 min | HTTP sessions, secrets out of code | `j_security_check` + `X-XSRF-TOKEN` handshake |
| [02 — State as data](02-operational-state/) | 50 min | Modelling, snapshots, diffing | Control connections, BFD, OMP, app-route |
| [03 — Config Groups](03-config-groups/) | 50 min | Idempotency, async tasks, dry-run | Feature profiles, parcels, deploy |
| [04 — Terraform](04-terraform/) | 45 min | Declarative, state, drift | Config group as code |
| [05 — Pipeline](05-pipeline/) | 30 min | CI/CD, verification, rollback | Fabric pre/post checks |

The remaining 20 minutes are for the opening, a break and the wrap-up. That's
deliberate.

## Before you start

```bash
git clone https://gitlab.autonetops.com/workshop/sdwan_automation.git
cd sdwan_automation

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# The offline suite must pass BEFORE you touch the lab.
python -m pytest -q
```

### Credentials

They live in **HashiCorp Vault** (`https://vault.autonetops.com`), never in the
repository. You get a read-only token at the start of the bootcamp.

```bash
export VAULT_ADDR=https://vault.autonetops.com
export VAULT_TOKEN=hvs.xxxxxxxx     # handed out by the instructor
export WS_STUDENT=07                # your number — prefixes everything you create

source scripts/vault-env.sh         # exports VMANAGE_* and TF_VAR_*
```

The secret lives at `secret/sdwan/manager` with the keys `url`, `username` and
`password`. All the code reads it through one function:
`sdwan_toolkit.vault.load_credentials()`.

> **Why Vault and not a `.env`?** Because today's `.env` is tomorrow's
> accidental commit. And because revoking a token is instant, while changing a
> password that eighteen people copied is not.

## The lab is shared

One Manager for the whole class. Two rules that aren't bureaucracy:

1. **Everything you create carries the `ws<NN>-` prefix** (your `WS_STUDENT`).
   Without it you overwrite each other's work.
2. **Don't remove the client's rate limiter.** `/device/*` endpoints are
   real-time: the Manager queries the device across the control plane. Twenty
   people in a tight loop turn the class into an incident. The `RateLimiter`
   in `sdwan_toolkit/client.py` exists for that reason.

## Studying afterwards

Every module has an `exercise.py` with TODOs and a `solution/` folder with the
finished, annotated version. Compare them — but only after you've tried.

The test suite runs **with no lab at all**, against a fake Manager in
`tests/conftest.py`. That's how you keep practising the following week, on a
plane, with no VPN.

```bash
python -m pytest -q                      # everything
python -m pytest tests/test_diff.py -q   # just the judge of the change
```

## The toolkit

```
sdwan_toolkit/
├── vault.py        credentials (module 1)
├── client.py       authenticated session + rate limiting (module 1)
├── inventory.py    who is who in the fabric (module 1)
├── state.py        operational snapshot (module 2)
├── diff.py         the judge of the change (module 2)
├── tasks.py        asynchronous task polling (module 3)
└── configgroup.py  declarative change (module 3)
```

## CI/CD

The repo ships both pipelines, so it works on whichever forge you import it
into:

- `.gitlab-ci.yml` — three stages (test → plan → apply). MRs get the offline
  tests and a `terraform plan`; the apply is default-branch-only and **manual**.
  Requires one masked, protected CI/CD variable: `VAULT_TOKEN`.
- `.github/workflows/change-validation.yml` — the same shape with GitHub
  Actions, gated by a `fabric-lab` environment.

## What was left out

Deliberately, because of the four hours: event-driven automation (alarm
webhooks), the aggregated statistics query DSL, ZTP/PnP onboarding and
multi-tenant vManage. All worthwhile — none of them fit. They're the next step.

---

Built by [AutoNetOps](https://autonetops.com). For the **configuration** (not
automation) side of SD-WAN, see the practical workbook on the platform.
