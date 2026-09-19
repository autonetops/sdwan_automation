# Module 5 — Terraform, properly (45 min + extensions)

The same change as module 4, now declarative — and then two things the
module 4 script never had: credentials it fetches itself, and state someone
other than you can read.

| | | |
|---|---|---|
| **PART A** | credentials out of Vault | `vault.tf` — TASK 1 |
| **PART B** | the change itself | `main.tf` — TASK 2, 3, 4 |
| **PART C** | state in GitLab | `backend.tf` — TASK 5 |

PART A is the 10 minutes. PART B 45 and PART C ~15 minutes each

## The point of this lesson

It isn't that Terraform beats Python. It's that **Terraform is only usable by
someone who understands what it's hiding**

| Module 4 (imperative) | Module 5 (declarative) |
|---|---|
| You write the **how** | You write the **what** |
| You do the polling | The provider does |
| You handle the failure | The provider does |
| Do you know the state? No | The `state` does |
| Works against any endpoint | Only what the provider covers |

## What we're learning

| Automation | SD-WAN |
|---|---|
| Declarative vs. imperative | Config group as code |
| State and drift detection | Who touched the GUI after you |
| `plan` as change review | The diff before the push |
| Reading a provider's schema | Resource names that move between versions |
| Secrets fetched, not exported | One token instead of three credentials |
| Remote state, locking, review | Two engineers, one fabric |

---

# PART A — the change

```bash
cp terraform.tfvars.example terraform.tfvars    # set your "student" number

terraform init
terraform plan      # ← this will fail. On purpose.
```

### TASK 2.1 — the planted error

The `plan` will complain about a non-existent attribute on
`sdwan_system_banner_feature`. **Don't google it.** Ask the provider itself:

```bash
terraform providers schema -json \
  | jq '.provider_schemas
        | .["registry.terraform.io/ciscodevnet/sdwan"].resource_schemas
        | .sdwan_system_banner_feature.block.attributes | keys'
```

Reading a provider's schema is the skill. Memorising attribute names is not —
these names moved between the 0.x releases of this provider, and they'll move
again.

## The uncomfortable discovery

Look at the `locals` block in `main.tf`. The `sdwan_device` data source exposes
`device_id`, `hostname`, `reachability`, `serial_number`, `site_id`, `state`,
`status` and `uuid` — **and nothing else**. There is no `personality`.

Meaning: through Terraform you cannot tell an edge from a controller, something
`/dataservice/device` gives you for free.

That's why the Python toolkit doesn't become junk once you adopt Terraform. The
provider covers the declarative path; the API covers the rest. **A good tool is
one you know when not to use.**

## Drift

After the `apply`, go to the GUI and change the banner by hand. Come back and
run:

```bash
terraform plan
```

It finds it. That's the superpower the module 4 script didn't have: Terraform
knows what the state *should* be, so it notices when someone else moved it.

---

# PART B — stop exporting secrets (TASK 4)

Look at what you just did. `source ../scripts/vault-env.sh` put a Manager
password into your shell's environment, where it is now inherited by every
process you launch from that terminal, readable in `/proc`, and one `env`
away from a screenshare. And the pipeline can only work if a human remembers
to run the script.

Terraform can go get it itself.

```bash
# vault.tf already declares the provider. Point the config at it:
echo 'credentials_from_vault = true' >> terraform.tfvars

terraform init      # the lock file has never seen the vault provider
terraform plan      # ← this will fail too. Also on purpose.
```

### TASK 4.1 — the KV v1/v2 trap

The shipped data source is `vault_kv_secret`, which reads a **KV v1** mount.
The bootcamp's `secret/` is **KV v2**. They are different APIs wearing the
same-looking path: v2 keeps data at `<mount>/data/<path>` and metadata at
`<mount>/metadata/<path>`, and the v2 data source therefore takes the mount
and the path **separately** rather than one concatenated string.

Read the error first. Then find the right data source the same way you found
the banner attribute:

```bash
terraform providers schema -json \
  | jq '.provider_schemas
        | .["registry.terraform.io/hashicorp/vault"].data_source_schemas
        | keys'
```

Two things change when you fix it: the data source **type**, and the address
it's referenced by in `local.vault_manager` — a resource's address is its type
plus its name, so changing the type moves every reference to it.

### Prove it worked

```bash
env -u TF_VAR_vmanage_url -u TF_VAR_vmanage_username -u TF_VAR_vmanage_password \
  terraform plan
```

Same plan, with the credentials deliberately removed from the environment.
The only secret left in your shell is `VAULT_TOKEN` — which `vault-env.sh`
mints for you from the userpass login you got in module 1, and which expires
on its own. Terraform's Vault provider speaks tokens, not userpass; that
exchange is the whole reason the script still exists.

### Two things worth stealing from `vault.tf`

- **`skip_child_token = true`.** By default the provider spends your token to
  mint a short-lived child token, which needs the `auth/token/create`
  capability. A genuinely read-only token doesn't have it, and the failure is
  a 403 that explains nothing.
- **`count` on the data source.** At `count = 0` Terraform doesn't just skip
  the read — it never configures the provider, so PART A keeps working with
  no Vault token at all. That's what makes the fallback a real fallback.

### What PART B just cost you

```bash
jq '.resources[]
    | select(.type == "vault_kv_secret_v2")
    | .instances[0].attributes.data' terraform.tfstate
```

There it is: the Manager password, cleartext, in a file on your laptop.
Terraform persists **every data source it reads**, and the same applies to any
saved plan (`terraform plan -out=tfplan`). The Vault provider's own
documentation says so in its first paragraph. Marking an attribute
`sensitive` only redacts it from *output* — `terraform show` prints
`(sensitive value)` while the bytes on disk stay in the clear.

That isn't an argument against PART B. It's the argument for PART C: a secret
Terraform is going to write down anyway belongs somewhere with access control,
versioning and an audit trail — not in `~/`. It's also why `.gitlab-ci.yml`
publishes the human-readable plan as its review artifact and never the binary
one: job artifacts are downloadable by every Reporter on the project.

> **Is the toggle good practice?** No. In production you delete the branch you
> don't use. It's here so the class survives Vault being down, and so you can
> see both paths side by side — but two ways to do one thing is two ways to be
> wrong, and the GitHub workflow in this repo is already the exception that
> proves it.

---

# PART C — the state stops being yours (TASK 5)

`terraform.tfstate` is currently a file in this directory. PART B already
showed you the first reason that's a problem — since Terraform reads the
secret, the state file *is* a credential file, which is why it's in
`.gitignore` and why it doesn't belong on a laptop.

There are four more:

| Local state | What it costs you |
|---|---|
| One copy, one laptop | Nobody else can plan, so nobody else can review |
| No backup | Lose it and Terraform forgets it owns the config group — the next apply tries to create it again and the fabric says the name is taken |
| No lock | Two people applying at once isn't a merge conflict, it's two writers on one fabric |
| Invisible to CI | `plan` and `apply` are separate containers. The apply job starts from an empty state **every run** |

That last one is the one that matters today. Open `.gitlab-ci.yml` and note
that `terraform-plan` and `apply-and-verify` are different jobs. Shared state
isn't a nicety there — it's what makes the pipeline correct.

GitLab serves Terraform state on every tier: the standard `http` backend with
GitLab as the server.

```bash
# 1. Uncomment the backend block in backend.tf (TASK 5.1)

# 2. Addresses go in a file...
cp backend.hcl.example backend.hcl     # fill in PROJECT_ID and your state name

# 3. ...secrets go in the environment.
export TF_HTTP_USERNAME="<your gitlab username>"
export TF_HTTP_PASSWORD="<personal access token, scope: api>"

# 4. Move it. Terraform shows you what it's about to copy and asks for a yes.
terraform init -migrate-state -backend-config=backend.hcl
```

Then prove the local file is inert:

```bash
terraform state list        # served from GitLab now
mv terraform.tfstate /tmp/  # and plan again — still works
terraform plan
```

Open **GitLab → Operate → Terraform states**. Your state is there, with a
serial number that climbs on every apply and a lock you can watch being taken.

### Why the backend block is empty

A backend block can't reference variables — it's read before Terraform
evaluates anything. So it stays empty (a *partial configuration*) and the
values arrive at `init` time. That's not a workaround, it's the mechanism
that lets one config serve many states: your laptop passes `backend.hcl`, and
the pipeline passes `TF_HTTP_*` built from `$CI_PROJECT_ID` and
`$CI_JOB_TOKEN` — a credential GitLab mints when the job starts and revokes
when it ends. Nobody stores it. Nobody rotates it.

### When a job dies mid-apply

The lock stays held. GitLab shows it under Terraform states, and you clear it
deliberately — after confirming nothing is still running:

```bash
terraform force-unlock <LOCK_ID>
```

"Deliberately" is the word. A lock you break while someone else is applying
is exactly the failure the lock existed to prevent.

---

## Where this leaves you

```
                    PART A            PART B              PART C
change              declarative       declarative         declarative
credentials         in your shell     fetched from Vault  fetched from Vault
state               on your laptop    on your laptop      in GitLab, locked
runs without you    no                no                  yes
```

The third column is the only one you can hand to a pipeline, and module 6 is
that pipeline.

## What about the others?

Ansible (`cisco.catalystwan`) and Sastre solve the same problem with different
trade-offs — the first without state, the second specialised in
backup/restore/migration. They were left out because of the four hours, not on
merit. We chose depth in one over a tour of three.
