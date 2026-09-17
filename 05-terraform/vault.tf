# ─────────────────────────────────────────────────────────────────────
# PART B — Terraform fetches its own credentials (TASK 4)
#
# In PART A you ran `source ../scripts/vault-env.sh` and the shell handed
# Terraform three TF_VAR_* values. That works, and it is how most teams
# start. It also means the secret exists, in the clear, in the environment
# of every process you launch from that shell — and that the correctness of
# your pipeline depends on a human remembering to run a script.
#
# Here Terraform reads Vault itself. Flip `credentials_from_vault` to true
# and the only secret in play is VAULT_TOKEN. Nothing else is exported,
# nothing else is typed, nothing else can be forgotten.
#
# The toggle is not production shape — in production you delete the branch
# you don't use. It exists so PART A keeps working when Vault is down, and
# so you can see both paths side by side. Note what it costs you: two ways
# to do one thing is two ways to be wrong.
# ─────────────────────────────────────────────────────────────────────



# ── TASK 4 ──────────────────────────────────────────────────────────
# Read the Manager secret out of Vault.
data "vault_kv_secret_v2" "this" {
  count = var.credentials_from_vault ? 1 : 0

  mount = var.vault_mount
  name  = var.vault_secret_path
}

# ── Which credentials win ───────────────────────────────────────────
locals {
  # `one()` turns a zero-or-one list into null-or-the-value. It is the
  # idiomatic companion to `use_vault` on a conditional data source, and it is
  # why the PART A path never touches Vault: at use_vault = 0 the provider is
  # not even configured, so no token is required to run PART A.
  vault_manager = one(data.vault_kv_secret_v2.this[*].data)

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
