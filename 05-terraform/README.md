# Module 5 — Terraform, properly (~55 min)

The same change as module 4, now declarative — plus two things the module 4
script never had: credentials it fetches itself, and state someone else can
read.

| | | | |
|---|---|---|---|
| **PART A** | the change itself | `locals.tf`, `main.tf` | TASK 1, 2, 3 · 10 min |
| **PART B** | credentials out of Vault | `vault.tf` | TASK 4 · 45 min |

The point isn't that Terraform beats Python. It's that **Terraform is only
usable by someone who understands what it's hiding**: you write the *what*,
the provider does the polling and the error handling, and the state file —
not you — knows what's out there. The cost is that you only get what the
provider covers.

---

# PART A — the change

```bash
cp terraform.tfvars.example terraform.tfvars    # set your "student" number
terraform init
```

| Task | File | What |
|---|---|---|
| **1** | `locals.tf` | Read `configs/policy_objects.yaml` in. Nothing else parses until you do |
| **2** | `main.tf` | One config group becomes a list in `terraform.tfvars`, driven by a `for` |
| **3** | `main.tf` | Uncomment the policer and give `for_each` its map |

```bash
terraform plan
terraform apply
```

**When a name doesn't exist**, don't google it — resource and attribute names
moved between the 0.x releases of this provider (`..._profile_parcel` became
`..._feature`). Ask the provider:

```bash
terraform providers schema -json \
  | jq '.provider_schemas
        | .["registry.terraform.io/ciscodevnet/sdwan"].resource_schemas
        | .sdwan_system_banner_feature.block.attributes | keys'
```

**Drift.** Change the banner by hand in the GUI, then `terraform plan` again.
It finds it — the module 4 script never could.

**The limit.** The `sdwan_device` data source exposes `hostname`,
`reachability`, `site_id`, `uuid` and little else. No `personality`, so
through Terraform you can't tell an edge from a controller — something
`/dataservice/device` gives you for free. The provider covers the declarative
path; the API covers the rest.

---

# PART B — stop exporting secrets

`source ../scripts/vault-env.sh` puts the Manager password in your shell,
where every process you launch inherits it and one `env` exposes it on a
screenshare. And the pipeline only works if a human remembers to run it.
Terraform can fetch it itself.

```bash
echo 'credentials_from_vault = true' >> terraform.tfvars
terraform init      # the lock file has never seen the vault provider
```

**TASK 4** — the read in `vault.tf` is unconditional, so PART A would now need
a Vault token it never needed before. Add `count` to the data source; the
`one()` below it already expects a zero-or-one list.

Prove it, with the credentials deliberately gone from the environment:

```bash
env -u TF_VAR_vmanage_url -u TF_VAR_vmanage_username -u TF_VAR_vmanage_password \
  terraform plan
```

The only secret left in your shell is `VAULT_TOKEN`, which expires on its own.
Two details in `vault.tf` worth stealing:

- **`skip_child_token = true`** — by default the provider mints a child token,
  which needs `auth/token/create`. A read-only token doesn't have it, and the
  403 explains nothing.
- **`count` on the data source** — at `count = 0` the provider is never
  configured, so PART A runs with no Vault token at all.

> **Is the toggle good practice?** No — in production you delete the branch
> you don't use. It's here so the class survives Vault being down.

---

# What's still missing

Two things, and both are module 6's.

```bash
jq '.resources[] | select(.type == "vault_kv_secret_v2")
    | .instances[0].attributes.data' terraform.tfstate
```

There's the Manager password, cleartext, on your laptop. Terraform persists
**every data source it reads** — into the state and into any saved plan.
`sensitive` redacts output, not bytes on disk.

`terraform.tfstate` being a local file costs you more than that:

| Local state | What it costs you |
|---|---|
| Contains your credentials | See above. It's a credential file, hence `.gitignore` |
| One copy, one laptop | Nobody else can plan, so nobody else can review |
| No backup | Lose it and the next apply recreates the config group — the fabric says the name is taken |
| No lock | Two people applying at once is two writers on one fabric |
| Invisible to CI | `plan` and `apply` are separate containers; apply starts from an empty state **every run** |

That last one is why module 6 moves the state to GitLab before it builds the
pipeline: with local state, the apply job starts from nothing every run, and
that bug stays invisible until the day it duplicates everything you own.

---

|  | module 4 | PART A | PART B | module 6 |
|---|---|---|---|---|
| change | imperative | declarative | declarative | declarative |
| credentials | in your shell | in your shell | from Vault | from Vault |
| state | none | your laptop | your laptop | GitLab, locked |
| runs without you | no | no | no | **yes** |

Only the last column can be handed to a pipeline. Module 6 is that pipeline.

> Ansible (`cisco.catalystwan`) and Sastre solve the same problem with
> different trade-offs — the first without state, the second specialised in
> backup/restore/migration. Left out for time, not on merit.
