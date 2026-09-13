# ─────────────────────────────────────────────────────────────────────
# PART B — Terraform fetches its own credentials (TASK 4, solved)
#
# In PART A the shell handed Terraform three TF_VAR_* values. That works,
# and it is how most teams start. It also means the secret sits in the clear
# in the environment of every process launched from that shell, and that the
# correctness of your pipeline depends on a human remembering a script.
#
# Here Terraform reads Vault itself. The only secret in play is VAULT_TOKEN.
# Nothing else is exported, nothing else can be forgotten.
# ─────────────────────────────────────────────────────────────────────

provider "vault" {
  address = var.vault_address

  # No `token` here. The provider reads VAULT_TOKEN from the environment,
  # which is the only place a token should ever be. Putting it in a variable
  # means it lands in a .tfvars file, and a .tfvars file lands in a commit.

  # By default this provider spends your token to mint a short-lived child
  # token — which needs the `auth/token/create` capability. The bootcamp
  # token is read-only and does NOT have it, so the default fails with a 403
  # that says nothing about why. Use the token as issued.
  skip_child_token = true
}

# ── TASK 4 ──────────────────────────────────────────────────────────
# The KV **v2** data source. The exercise ships `vault_kv_secret`, which is
# the v1 one, and that is the single most common Vault integration mistake:
# KV v1 and KV v2 are different APIs wearing the same path. v2 stores data
# under `<mount>/data/<path>` and metadata under `<mount>/metadata/<path>`,
# which is why it takes the mount and the path separately instead of one
# concatenated string — the provider inserts the `/data/` for you.
#
# Confirmed with `terraform providers schema -json`, not from memory:
#   v1 takes `path`. v2 takes `mount` + `name`. Both expose `data`.
data "vault_kv_secret_v2" "manager" {
  count = var.credentials_from_vault ? 1 : 0

  mount = var.vault_mount
  name  = var.vault_secret_path
}

# ── Which credentials win ───────────────────────────────────────────
locals {
  # `one()` turns a zero-or-one list into null-or-the-value. It is the
  # idiomatic companion to `count` on a conditional data source, and it is
  # why the fallback path never touches Vault: at count = 0 the provider is
  # not configured at all, so no token is required to use it.
  vault_manager = one(data.vault_kv_secret_v2.manager[*].data)

  manager = var.credentials_from_vault ? {
    url      = local.vault_manager["url"]
    username = local.vault_manager["username"]
    password = local.vault_manager["password"]
    } : {
    url      = var.vmanage_url
    username = var.vmanage_username
    password = var.vmanage_password
  }
}
