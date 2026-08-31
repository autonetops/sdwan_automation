# Module 4 — Terraform, properly (45 min)

The same change as module 3, now declarative.

## The point of this lesson

It isn't that Terraform beats Python. It's that **Terraform is only usable by
someone who understands what it's hiding** — which is exactly what you
implemented by hand an hour ago.

| Module 3 (imperative) | Module 4 (declarative) |
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

## Get to work

```bash
source ../scripts/vault-env.sh                  # exports TF_VAR_*
cp terraform.tfvars.example terraform.tfvars    # set your "student" number

terraform init
terraform plan      # ← this will fail. On purpose.
```

### TODO 2.1 — the planted error

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

It finds it. That's the superpower the module 3 script didn't have: Terraform
knows what the state *should* be, so it notices when someone else moved it.

## What about the others?

Ansible (`cisco.catalystwan`) and Sastre solve the same problem with different
trade-offs — the first without state, the second specialised in
backup/restore/migration. They were left out because of the four hours, not on
merit. We chose depth in one over a tour of three.
