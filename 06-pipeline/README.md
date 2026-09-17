# Module 6 — The pipeline (30 min + extensions)

The capstone. Everything you built, wired to a `git push`.

Until now you have been the pipeline: you ran the script, you read the
output, you decided whether it looked right. This module takes you out of the
loop — and the interesting part is not the automation, it is **what has to be
true before anyone is willing to let that happen.**

```
                     ┌─ you edit ONE file ─┐
                     │  data/fabric.yaml   │
                     └──────────┬──────────┘
                                │  git push
   ┌──────────┬──────────┬──────┴───┬──────────┬──────────┐
   │ validate │   plan   │  deploy  │   test   │  notify  │
   └──────────┴──────────┴──────────┴──────────┴──────────┘
     schema +   what will   precheck   is it      who
     semantics  it do?      apply      settled?   finds out
                            postcheck
                            rollback?
```

## The thesis

> A change without automatic verification is not automation. It's faster
> typing.

A script that pushes config faster than you only made you wrong faster. What
changes the game is the fabric being able to **fail its own change** — and a
process where the thing that gets reviewed is a diff a human can read.

---

## The five stages

| Stage | Job(s) | Asks | Needs the fabric? |
|---|---|---|---|
| **validate** | `data-model-validate`, `offline-tests`, `terraform-fmt` | Is this change even coherent? | **No** |
| **plan** | `plan` | What exactly will it do? | Yes (read-only) |
| **deploy** | `deploy` | Do it — and prove the fabric survived. | Yes (writes) |
| **test** | `test-idempotency` | Does it *stay* done? | Yes (read-only) |
| **notify** | `notify-success`, `notify-failure` | Who finds out? | No |

`validate` needing nothing is the most important row in that table. It is the
job that still works when the lab is down, on a plane, at 2am — and a gate
that needs the thing it is gating is not a gate.

## What runs where

|  | validate | plan | deploy | test | notify |
|---|:---:|:---:|:---:|:---:|:---:|
| **Feature branch** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Merge request** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Default branch** | ✅ | ✅ | ✅ *manual* | ✅ | ✅ |

The asymmetry is the design, not a limitation. **Anyone** may propose a change
and watch it be checked. Only the default branch may touch the fabric, only
after review, and only when a human presses the button.

---

## The change is a YAML file

This is the part that is new in module 6. In module 5 the change lived in
`terraform.tfvars` — HCL, read by one tool, reviewable by whoever knows that
tool. Here it lives one level up:

```
data/fabric.yaml  ──render.py──▶  generated.auto.tfvars.json  ──▶  terraform
```

```yaml
sdwan:
  student: "07"
  system:
    banner:
      motd: "Managed by the AutoNetOps pipeline"
      login: "Authorized access only"
  config_group:
    name: config-group
    description: "Config group deployed by the module 6 pipeline"
  targets:
    edges:
      - Site1-Edge1
```

Three things follow, and they are the whole lesson:

1. **The change gets a schema.** `bannner:` is an error, not a change that
   passes every check and quietly does nothing. (`extra="forbid"` on every
   model in `sdwan_toolkit/datamodel.py` — that is what buys you this.)
2. **The change gets rules.** A schema says *`motd` is a string*. A semantic
   rule says *a string containing "CHANGEME" must not reach a router*. Both
   run in `validate`, and they fail differently on purpose.
3. **The data model outlives the tool.** `targets.edges` is never rendered to
   Terraform — the Python pipeline reads it. A data model describes the
   change, not one tool's inputs.

`generated.auto.tfvars.json` is generated, gitignored and never edited by
hand. If you want to change it, the thing you actually want is a field in the
YAML and a line in `render_tfvars()`.

> **On Cisco's Network as Code.** This module is deliberately shaped like the
> [Net-as-Code pipeline lab](https://netascode.cisco.com/docs/labs/sdwan/understanding-pipelines/),
> which is worth reading. It is **not** built on NaC: no `nac-validate`, no
> `iac-test`, no `terraform-nac-sdwan` module. Everything here is ~200 lines
> you can read in one sitting, because the point of the bootcamp is to
> understand the machinery before adopting somebody's packaged version of it.
>
> | Net-as-Code | Here |
> |---|---|
> | `data/*.nac.yaml` | `data/fabric.yaml` |
> | `nac-validate` (schema + semantics) | `validate.py` + `sdwan_toolkit/datamodel.py` |
> | `terraform-nac-sdwan` module | `render.py` → module 5's Terraform |
> | `iac-test` integration tests | `pipeline.py` — snapshot, compare, roll back |
> | `test-idempotency` | `terraform plan -detailed-exitcode` |
> | Webex notification | `notify.py` → Slack |

---

## Get to work

### 1. Watch the gate refuse you

The shipped data model fails on purpose. Run the validator before you change
anything:

```bash
cd 06-pipeline
python validate.py
```

```
── VALIDATE data/fabric.yaml ──
  ✓ schema      ws00-config-group · banner motd 71 chars · 1 target edge(s)
  ✗ semantic    1 problem(s)
                • sdwan.system.banner.login: contains the placeholder 'CHANGEME'.
                  A banner is read by everyone who logs in, every day.
```

Exit code 1. That is stage 1 of the pipeline doing its job, on your laptop,
in 200ms, with no lab involved.

### 2. Make a real change, on a branch

```bash
git switch -c ws07/banner-and-targets
```

Edit `data/fabric.yaml`:

- set `student` to **your** number,
- fix the `login` banner,
- put your lab's real edge hostnames under `targets.edges`,
- change the `motd` to something of your own — that is the visible change.

Then run the two local stages:

```bash
python validate.py          # must exit 0 now
python render.py --print    # see exactly what Terraform will receive
```

### 3. Push it and read the pipeline

```bash
git commit -am "ws07: banner and targets"
git push -u origin ws07/banner-and-targets
```

Open the merge request. Two things to look at, in this order:

- the **`validate`** jobs — they ran on the branch, before anyone reviewed
  anything;
- the **`plan`** job's `tfplan.txt` artifact — the answer to *"what exactly is
  going to change?"*, attached to the review rather than discovered after it.

Merge. On the default branch the `deploy` job appears — and waits, because it
is `when: manual` behind the `fabric-lab` environment. Press it.

### 4. Run the deploy stage by hand first

Before you trust the button, run what it runs:

```bash
cd 06-pipeline
python pipeline.py --dry-run      # both snapshots, changes nothing
python pipeline.py                # the full cycle
python pipeline.py --wait 10      # shorter convergence wait, for a demo
```

Exit code `0` = fabric intact. `1` = regressed, **and already rolled back**.
That exit code is the whole interface between your Python and the pipeline.

---

## The four decisions the exercise asks for

The TODOs in `pipeline.py` don't have one right answer. They have a
**justification** — write yours down, in the MR description or here.

### TASK 1 — should precheck abort if a device is down?

In a shared lab, aborting because *some* device is down is unworkable:
somebody always has one deliberately down, and a gate that fires on other
people's work is a gate that gets commented out in week two.

Aborting because a device **this change targets** is down is a different
thing entirely. That is what `targets.edges` is for, and it is why the data
model carries a key Terraform never reads.

The other half, easy to forget: `compare()` only looks at the *difference*. A
device that was down before and after produces no finding at all. Report it
even when you don't abort on it.

### TASK 2 — where does the rendering happen?

`plan` rendered the data model already. `deploy` renders it again, because
`plan` was a different container. The alternative is to pass the saved plan
between jobs as an artifact — which this repo deliberately does not do:
Terraform persists every data source it read into the plan file, and module 5
PART B has it read the Manager password out of Vault. `terraform show`
redacts; the binary file does not.

### TASK 3 — how long before the postcheck?

BFD and OMP do not reconverge instantly. An immediate postcheck reports a
regression that isn't real — and **a pipeline that cries wolf is a pipeline
people switch off.** The solution waits 60s. Defend your number.

### TASK 4 — rollback by re-applying, or by destroying?

Destroying the config group is more violent than the change you are undoing.
**A rollback that causes more impact than the original problem isn't a
rollback — it's a second incident.**

The rollback target is not a backup somebody remembered to take. It is the
previous commit of `data/fabric.yaml`, and it has been in Git the whole time:

```bash
git show HEAD~1:06-pipeline/data/fabric.yaml
```

Two cases the solution handles explicitly, because both look like success:

- **no previous version** (first commit, or a shallow clone — GitLab clones
  shallow by default, which is why `.gitlab-ci.yml` sets `GIT_DEPTH`);
- **the previous version is identical**, which means the regression did not
  come from this file. Re-applying it is a no-op, and reporting "rolled back"
  would be a lie. Say so and escalate.

---

## The `test` stage

One job, and it is three lines:

```bash
terraform plan -input=false -detailed-exitcode
```

`0` = nothing to do. `2` = there is a diff. Anything else = the plan itself
failed. A plain `terraform plan` collapses those three into one exit code,
which is why nobody notices when it matters.

A second plan that still wants to change something means one of three things,
and all three are worth failing a pipeline over:

- a resource is **not idempotent** — it rewrites itself on every apply, so
  every future pipeline shows a change that is not a change;
- the **Manager normalised** something you sent (trailing whitespace, a case
  change), so your data model and the fabric now disagree permanently;
- somebody is **editing the fabric in the GUI** while the pipeline runs.

This is the cheapest test in the pipeline and the one people skip.

> The GitHub workflow runs the same job, but that runner has no credentials
> for GitLab-managed state, so it works from local state that does not
> survive the container. The check is only honest on the GitLab pipeline.
> That is not a GitHub problem — it is what "state that lives for the length
> of a container" costs you.

## The `notify` stage

A deploy that succeeded and told nobody is fine. A deploy that **failed** and
told nobody is an outage with a delay fuse on it.

```bash
python notify.py success
python notify.py failure --text "rollback did not complete"
```

⚠️ **`SLACK_WEBHOOK_URL` is not set yet** — create an incoming webhook for
your channel and add it as a **masked, protected** CI/CD variable. Until then
both jobs are skipped, and `notify.py` exits 0 if you call it anyway: a
pipeline that fails because Slack is down is a pipeline that teaches everyone
to ignore it.

---

## What's in this directory

```
06-pipeline/
├── data/fabric.yaml    THE CHANGE. The only file you edit.      ← stage 1 input
├── validate.py         schema + semantic rules                  ← stage 1   (TASK 1)
├── render.py           data model → Terraform's inputs          ← stage 2
├── pipeline.py         precheck → apply → postcheck → rollback  ← stage 3   (TASKS 1-4)
├── notify.py           Slack, on both outcomes                  ← stage 5
└── solution/           validate.py and pipeline.py, finished and annotated
```

`render.py` and `notify.py` ship complete — they have no TODOs. The two files
with work in them are `validate.py` (one rule of your own) and `pipeline.py`
(the four decisions below).

The schema and the rules themselves live in `sdwan_toolkit/datamodel.py`,
with `tests/test_datamodel.py` covering them offline — because a validator
nobody tests is a validator nobody should trust.

```bash
python -m pytest tests/test_datamodel.py -q
```

## Secrets and variables

| Where | Name | What |
|---|---|---|
| GitLab CI/CD variables | `VAULT_USERNAME` | protected |
| | `VAULT_PASSWORD` | protected **and masked** |
| | `SLACK_WEBHOOK_URL` | protected and masked — ⚠️ not set yet |
| GitLab state backend | — | authenticates with the job's own `CI_JOB_TOKEN` |

That is the entire list. Everything else — the Manager URL, username and
password — comes out of Vault at runtime, which is module 1 and module 5
PART B paying off.

## Where to go next

- Post `tfplan.txt` automatically as an MR comment, so the reviewer doesn't
  have to open a job log.
- Swap the homegrown rollback for the Manager's native **config-rollback
  timer**, and compare the two failure modes.
- Add an **integration test** to the `test` stage: read the config group back
  off the Manager and assert it matches `data/fabric.yaml`. You have
  everything you need in `sdwan_toolkit/configgroup.py`.
- Extend `compare()` with app-route SLA, not just session counts.
- Manager alarms over webhook → event-driven automation.
