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
     shape +    what will   apply,     is it      who
     meaning    it do?      verify,    settled?   finds out
                            roll back
```

**There is no application code in this module.** No Python, no renderer, no
orchestrator. Terraform reads the YAML itself and Terraform's own
preconditions and postconditions are what make the fabric able to refuse its
own change. What you write is the pipeline, and the Terraform under it:

| | | |
|---|---|---|
| **PART A** | the pipeline | `.gitlab-ci.yml` — TASK 1 to 6 |
| **PART B** | the verification | `terraform/` — TASK 1 to 4 |

PART A is the shape: which jobs run, on which branches, and who is allowed to
touch the fabric. PART B is the part that can say no. Do them in that order —
PART A gives you somewhere to put PART B.

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
| **validate** | `data-model-validate`, `terraform-validate`, `offline-tests` | Is this change even coherent? | **No** |
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

## The change is a YAML file, and Terraform reads it

In module 5 the change lived in `terraform.tfvars` — HCL, read by one tool,
reviewable by whoever knows that tool. Here it lives one level up, and
**nothing sits in between**:

```
data/fabric.yaml  ──yamldecode()──▶  terraform  ──▶  the fabric
```

```yaml
sdwan:
  student: "07"
  system:
    banner:
      motd: "Managed by the AutoNetOps pipeline"
      login: "Authorized access only"
  config_group:
    name: pipeline
    description: "Config group deployed by the module 6 pipeline"
  targets:
    edges:
      - Site1-Edge1
```

```hcl
# terraform/data_model.tf — the entire integration
locals {
  model  = yamldecode(file("${path.module}/../data/fabric.yaml"))
  sdwan  = local.model.sdwan
  prefix = "ws${local.sdwan.student}-"
}
```

There is no renderer and no generated file, because Terraform has read YAML
natively since 0.12. "We need a script to convert the data model" is one of
the most common unnecessary moving parts in a network pipeline.

Two details worth the minute they cost:

- **`path.module`, not a bare relative path.** `file("../data/fabric.yaml")`
  resolves against the *process's* working directory — fine on a laptop,
  wrong the moment CI runs `terraform -chdir=…`, which it does.
- **`targets.edges` produces no resource at all.** Terraform never turns it
  into anything; `verify.tf` reads it to decide what to refuse. A data model
  describes the change, not one tool's inputs.

> **On Cisco's Network as Code.** This module is deliberately shaped like the
> [Net-as-Code pipeline lab](https://netascode.cisco.com/docs/labs/sdwan/understanding-pipelines/),
> which is worth reading. It is **not** built on NaC: no `nac-validate`, no
> `iac-test`, no `terraform-nac-sdwan` module. Everything here is a few
> hundred lines of Terraform and YAML you can read in one sitting, because
> the point of the bootcamp is to understand the machinery before adopting
> somebody's packaged version of it.
>
> | Net-as-Code | Here |
> |---|---|
> | `data/*.nac.yaml` | `data/fabric.yaml` |
> | `nac-validate` (schema) | `terraform validate` — it decodes the YAML for you |
> | `nac-validate` (semantic rules) | `validate-data-model.sh` (yq) |
> | `terraform-nac-sdwan` module | `terraform/` — yours, and readable |
> | `iac-test` integration tests | preconditions and postconditions in `verify.tf` |
> | `test-idempotency` | `terraform plan -detailed-exitcode` |
> | Webex notification | `jq` + `curl` → Slack |

---

## The one thing to take away: three constructs, three severities

Terraform has three ways to assert something. **They are not
interchangeable**, and picking the wrong one gives you a pipeline that looks
like it is checking something and is not.

| | evaluated | on failure | use it for |
|---|---|---|---|
| `precondition` | before the resource | **ERROR** — stops the apply | refusing to start |
| `postcondition` | after the object is read/created | **ERROR** — fails the apply | proving the change did no harm |
| `check` block | plan *and* apply | **WARNING** — apply still succeeds | things worth knowing that aren't yours to fix |

⚠️ **Read that last row twice.** A `check` block *cannot* fail a pipeline. It
emits a warning and `terraform` exits 0. If the only verification in your
configuration is a check block, you have written a pipeline that reports
problems to a log nobody reads and then deploys anyway.

This is the single most common mistake people make with these three, and it
is invisible until the day it matters. Which is why this module uses all
three, each for the thing it is actually good at.

---

## Get to work

### 1. Watch the gate refuse you

The shipped data model fails on purpose:

```bash
cd 06-pipeline
./validate-data-model.sh
```

```
── VALIDATE data/fabric.yaml ──
  ✓ student is two digits (it becomes your ws<NN>- prefix)
  ✓ the MOTD banner is not empty
  ✓ the login banner is not empty
  ✗ no placeholder text in the banners
  ✓ no ^C banner delimiter in the banners
  ...
Fix the ✗ lines above. Nothing reaches the fabric until they pass.
```

Exit code 1, in under a second, with no lab involved. That is stage 1.

Needs [yq](https://github.com/mikefarah/yq) — one binary, and the pipeline
installs it for you.

### 2. PART A — write the pipeline

`06-pipeline/.gitlab-ci.yml` is the repository's real pipeline with six
pieces cut out of it. Everything else is given, comments included, because
reading those is half the exercise.

| | Where | What |
|---|---|---|
| **TASK 1** | `stages:` | Five correct stages, sorted alphabetically. Put them in running order. |
| **TASK 2** | `data-model-validate` | The job's `script:`. One line, two things to get right. |
| **TASK 3** | `plan` | `artifacts:` (what the reviewer opens) and `rules:` (MR + default branch). |
| **TASK 4** | `deploy` | The four lines that stop this job running on every push. |
| **TASK 5** | `test-idempotency` | Turn `terraform plan -detailed-exitcode`'s three exit codes into a verdict. |
| **TASK 6** | `notify-*` | `on_success` vs `on_failure`, and why one job has no `needs:`. |

GitLab only reads `.gitlab-ci.yml` at the **root** of the repository, so the
exercise copy does nothing where it sits. Break it freely. Two ways to check
your work:

1. **CI Lint** — the fast loop. Open
   `https://gitlab.autonetops.com/<your-project>/-/ci/lint`, paste the file,
   tick *Simulate a pipeline creation*, read what it says. It catches more
   than you would expect, stage ordering included.
2. **Run it for real.** Settings → CI/CD → General pipelines → *CI/CD
   configuration file*, set it to `06-pipeline/.gitlab-ci.yml`. Now your
   version is the one that runs on every push. Set it back to empty when
   you're done.

The finished version is the root `.gitlab-ci.yml` — compare, but only after
you've tried. Notice that comparing is even possible because the whole
pipeline is one readable file rather than a product you configure.

### 3. PART B — solve the four TASKs in `terraform/`

```bash
cd 06-pipeline/terraform
terraform init
terraform validate      # ← this will fail. On purpose.
```

| | Where | What |
|---|---|---|
| **TASK 1** | `data_model.tf` | The wrong decoder. One word. `terraform validate` names it. |
| **TASK 2** | `main.tf` | The `precondition` blocks that refuse to start. |
| **TASK 3** | `verify.tf` | The `postcondition` that fails the apply on a regression. |
| **TASK 4** | `verify.tf` | The `check` block that reports without blocking. |

`terraform validate` gets you through TASK 1 with no credentials at all.
For TASKs 2, 3 and 4 you need a plan, so load your Vault token first
(module 5 PART B) and run `terraform plan`.

Note the two placeholder conditions in `verify.tf` — Terraform will not even
let you write `condition = true`:

> The condition expression must refer to at least one object from elsewhere
> in the configuration, or else its result would not be checking anything.

Terraform is making the same argument this module is.

### 4. Make a real change, on a branch

```bash
git switch -c ws07/banner-and-targets
```

Edit `data/fabric.yaml`: your `student` number, a fixed `login` banner, your
lab's real edge hostnames under `targets.edges`, and a `motd` of your own —
that last one is the visible change.

```bash
./validate-data-model.sh                                  # must exit 0 now
terraform -chdir=terraform plan                           # the gate, live
```

### 5. Push it and read the pipeline

```bash
git commit -am "ws07: banner and targets"
git push -u origin ws07/banner-and-targets
```

Open the merge request. Two things to look at, in this order:

- the **`validate`** jobs — they ran on the branch, before anyone reviewed
  anything;
- the **`plan`** job's `tfplan.txt` artifact — the answer to *"what exactly is
  going to change?"*, attached to the review rather than discovered after it.

Something subtle happens here that the Python version could not do. The
preconditions are evaluated at **plan** time, because
`data.sdwan_device.before` has no `depends_on` and Terraform therefore reads
the fabric during plan. **A change that targets an unreachable device is
refused on the merge request**, before anyone presses deploy.

Merge. On the default branch the `deploy` job appears — and waits, because it
is `when: manual` behind the `fabric-lab` environment. Press it.

---

## The decisions these ask for

Several TASKs do not have one right answer. They have a
**justification** — write yours down, in the MR description or here.

### TASK 4 — `allow_failure: false` is redundant. Why write it?

Because GitLab gives the same two words two different defaults depending on
where you put them:

| | default `allow_failure` |
|---|---|
| `when: manual` as a job keyword | `true` — the job is **optional** |
| `when: manual` inside `rules:` | `false` — the job is **blocking** |

`true` means the pipeline goes green whether or not anyone ran the job, and
whether or not it failed: success reported for a deploy that never happened.
This pipeline uses the `rules:` form, so the safe value is already the
default — but nobody reading the file should have to know that to trust it,
and a refactor that lifts `when: manual` out of `rules:` would flip it
silently.

### TASK 6 — why does `notify-failure` have no `needs:`?

`needs:` ties a job to specific upstream jobs. A failure notifier tied to
`deploy` never fires when `validate` was what failed — and the change that
got stopped at the gate is exactly the one somebody might be waiting on.

### TASK 1 — why is there no renderer?

Because Terraform reads YAML. The interesting question is the one underneath:
how many moving parts in your pipeline exist only because nobody checked
whether the tool already did it?

### TASK 2 — should the gate refuse when a device is down?

In a shared lab, refusing because *some* device is down is unworkable:
somebody always has one deliberately down, and a gate that fires on other
people's work is a gate that gets commented out in week two.

Refusing because a device **this change targets** is down is a different
thing entirely. That is what `targets.edges` is for.

The other half, easy to forget: the far more common failure is a *typo* in
`targets.edges` — a hostname the fabric has never heard of. A gate that only
checks reachability silently passes a change aimed at nothing.

### TASK 3 — why `depends_on` on a data source?

Without it, Terraform reads `data.sdwan_device.after` during **plan**, along
with every other data source — and the postcondition would be checking the
fabric *before* the change. It would pass, always, and mean nothing.

`depends_on` defers the read to apply time. One line, and it is the
difference between verification and theatre.

### TASK 4 — isn't the check block duplicating TASK 2?

It asserts a related fact at a different severity, and that is the point. The
precondition is about **your** targets and it blocks. The check is about
**everyone's** devices and it does not.

A device that was down before and is still down after produces no finding in
any diff — it did not change. Without something like the check block, nobody
ever notices, and the fabric degrades one device at a time between
deployments.

### And the one the pipeline decides, not Terraform

Terraform can fail an apply. It cannot decide what to do next. The rollback
lives in `.gitlab-ci.yml`, and the target is not a backup somebody remembered
to take — it is the previous commit of the data model:

```bash
git checkout HEAD~1 -- 06-pipeline/data/fabric.yaml
terraform -chdir="$TF_DIR" apply -auto-approve
```

Chosen over `terraform destroy`: destroying the config group is more violent
than the change being undone, and **a rollback that causes more impact than
the original problem isn't a rollback — it's a second incident.**

Two cases the job handles explicitly, because both look like success:

- **no previous version** (first commit, or a shallow clone — GitLab clones
  shallow by default, which is why the pipeline sets `GIT_DEPTH`);
- **the data model is unchanged in this commit**, which means the failure did
  not come from this file. Re-applying it is a no-op and reporting "rolled
  back" would be a lie. Escalate instead.

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

⚠️ **`SLACK_WEBHOOK_URL` is not set yet** — create an incoming webhook for
your channel and add it as a **masked, protected** CI/CD variable. Until then
both jobs are skipped entirely: a pipeline that fails because Slack is down
is a pipeline that teaches everyone to ignore it.

The message is built with `jq -n --arg`, not by pasting strings into a shell
heredoc. A commit title containing a quote would break the latter on the day
you least want a broken notifier.

---

## What's in this directory

```
06-pipeline/
├── .gitlab-ci.yml             ← YOU COMPLETE THIS (PART A, TASK 1-6)
│                                inert where it sits; GitLab reads the root one
├── data/fabric.yaml           THE CHANGE. The only file you edit.
├── validate-data-model.sh     stage 1 — the semantic rules, in yq
├── terraform/                 ← YOU COMPLETE THIS (PART B, TASK 1-4)
│   ├── data_model.tf            yamldecode                      TASK 1
│   ├── main.tf                  the change, and the gate        TASK 2
│   ├── verify.tf                postcondition, check block      TASKS 3, 4
│   ├── providers.tf             sdwan + vault
│   ├── vault.tf                 credentials Terraform fetches itself
│   ├── variables.tf             plumbing only — nothing about the change
│   ├── versions.tf              (no backend: local state, your laptop)
│   └── outputs.tf
└── solution/terraform/        the finished version, annotated
    └── backend.tf               + GitLab state, which the pipeline needs
```

The pipeline that actually runs is `.gitlab-ci.yml` at the repository root —
the finished version of PART A. `.github/workflows/change-validation.yml` is
the same five stages on GitHub Actions.

> Your `terraform/` and the pipeline's `solution/terraform/` both create
> `ws<NN>-pipeline` on the same Manager, from two different states. Run one
> or the other, not both — the same caveat module 5 carries.

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
- Add BFD and OMP session counts to the postcondition, not just
  reachability — the `sdwan_device` data source won't give you those, so this
  is where the Python toolkit from modules 1–4 earns its keep again.
- Swap the homegrown rollback for the Manager's native **config-rollback
  timer**, and compare the two failure modes.
- Split `data/fabric.yaml` into one file per site and `yamldecode` a
  directory — that is the step where a data model becomes a data *model*.
- Manager alarms over webhook → event-driven automation.
