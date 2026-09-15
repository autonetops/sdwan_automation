# Cisco Catalyst SD-WAN — Automation Bootcamp

Four hours for engineers who **already know SD-WAN and are learning automation**.

Nobody here will explain what a TLOC, OMP or config group is — you know that
already. What you'll learn is automation, using those objects as the
vocabulary. The sentence that sums up the day:

> You already know what a config group is. Today you learn what it looks like
> as JSON on the wire — and why that changes what you can do with it.

## The arc

You don't do six disconnected exercises. You build **one tool**, layer by
layer, and you leave with it working.

| Module | Time | Automation | SD-WAN |
|---|---|---|---|
| [01 — Credentials out of the code](01-vault-credentials/) | 30 min | Secrets management, validation at the boundary | Vault userpass, the KV v2 double envelope |
| [02 — Connecting to the Manager](02-connecting-to-manager/) | 30 min | HTTP sessions and cookie jars | `j_security_check` + `X-XSRF-TOKEN` handshake |
| [03 — From functions to a client](03-building-the-client/) | 35 min | Encapsulation, context managers, one choke point | Rate limiting a shared Manager, the `data` envelope |
| [04 — Change the fabric, and prove it](04-change-and-verify/) | 50 min | Snapshots, async tasks, an opinionated diff | Config groups, preview, deploy, BFD/OMP/control |
| [05 — Terraform](05-terraform/) | 45 min + 30 | Declarative, state, drift, secrets Terraform fetches itself, state in GitLab | Config group as code |
| [06 — Pipeline](06-pipeline/) | 30 min | CI/CD, verification, rollback | Fabric pre/post checks |

The remaining 20 minutes are for the opening, a break and the wrap-up. That's
deliberate.

**Modules 1 to 3 are the toolkit you build.** Module 1 produces
`sdwan_toolkit/vault.py`, module 2 produces working handshake code, and module
3 refactors it into `sdwan_toolkit/client.py`. Everything after that is
written *on top of* what you wrote — which is why `state.py`, `tasks.py` and
`configgroup.py` are each under 170 lines.

Module 5 carries a `+ 30`: PART A is the 45-minute core, and PARTS B and C —
credentials fetched from Vault, state moved to GitLab — are ~15 minutes each.
Run them in the room if the day is going quickly, hand them over as the
take-home if it isn't. They're the two steps between "it worked on my laptop"
and "it runs without me", so they're worth the overrun when there's room.

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
repository. You get a personal, read-only **userpass** login at the start of
the bootcamp.

```bash
export VAULT_ADDR=https://vault.autonetops.com
export VAULT_USERNAME=ws07          # handed out by the instructor
export VAULT_PASSWORD=...
export WS_STUDENT=07                # your number — prefixes everything you create
```

The secret lives at `workshop/sdwan` with the keys `url`, `username` and
`password`. All the Python reads it through one function:
`sdwan_toolkit.vault.load_credentials()` — which is module 1's deliverable.

Terraform can't call that function, so PART A of module 5 uses
`source scripts/vault-env.sh` to export `TF_VAR_vmanage_*`. From module 5
PART B onward Terraform fetches the secret itself, and those variables
disappear again.

> **Why Vault and not a `.env`?** Because today's `.env` is tomorrow's
> accidental commit. And because revoking a login is instant, while changing a
> password that eighteen people copied is not.
>
> There is deliberately **no `VMANAGE_URL` fallback**. A fallback is a door,
> and a door that exists "only for CI" is a door someone eventually uses on a
> laptop. Module 1 makes the argument properly.

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
python -m pytest tests/test_vault.py -q  # module 1
python -m pytest tests/test_client.py -q # module 3 — this suite is the spec
python -m pytest tests/test_diff.py -q   # just the judge of the change
```

## The toolkit

```
sdwan_toolkit/
├── vault.py        credentials                          ← YOU BUILD THIS (module 1)
├── client.py       authenticated session + rate limiting ← YOU BUILD THIS (module 3)
├── inventory.py    who is who in the fabric             (module 3)
├── state.py        operational snapshot                 (module 4)
├── diff.py         the judge of the change              (module 4)
├── tasks.py        asynchronous task polling            (module 4)
└── configgroup.py  declarative change                   (module 4)
```

The two marked files are the ones you write. The rest are given, and they are
short because those two exist — which is the argument for building them by
hand rather than importing someone else's SDK on slide one.

## CI/CD

The repo ships both pipelines, so it works on whichever forge you import it
into:

- `.gitlab-ci.yml` — three stages (test → plan → apply). MRs get the offline
  tests and a `terraform plan`; the apply is default-branch-only and **manual**.
  Terraform state is served by GitLab (Operate → Terraform states), so `plan`
  and `apply` — separate jobs, separate containers — share one locked state.
  Requires two protected CI/CD variables — `VAULT_USERNAME` and a masked
  `VAULT_PASSWORD` — for a CI service account. The job exchanges them for a
  short-lived Vault token that Terraform can speak; the Python side does its
  own userpass login. The state backend authenticates with the job's own
  `CI_JOB_TOKEN`, so there's nothing else to store.
- `.github/workflows/change-validation.yml` — the same shape with GitHub
  Actions, gated by a `fabric-lab` environment. It runs without the GitLab
  state backend (that runner has no credentials for it), which is precisely
  why the GitLab pipeline is the supported one: state that lives for the
  length of a container is state nobody can review or lock.

## What was left out

Deliberately, because of the four hours: event-driven automation (alarm
webhooks), the aggregated statistics query DSL, ZTP/PnP onboarding and
multi-tenant vManage. All worthwhile — none of them fit. They're the next step.

---

Built by [AutoNetOps](https://autonetops.com). For the **configuration** (not
automation) side of SD-WAN, see the practical workbook on the platform.
