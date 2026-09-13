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

provider "vault" {
  address = var.vault_address

  # No `token` here. The provider reads VAULT_TOKEN from the environment,
  # which is the only place a token should ever be. Putting it in a
  # variable means it lands in a .tfvars file, and a .tfvars file lands in
  # a commit.

  # By default this provider spends your token to mint a short-lived child
  # token — which needs the `auth/token/create` capability. The bootcamp
  # token is read-only and does NOT have it, so the default would fail with
  # a 403 that says nothing about why. Skip it and use the token as issued.
  skip_child_token = true
}

# ── TASK 4 ──────────────────────────────────────────────────────────
# Read the Manager secret out of Vault.
#
# TODO 4.1: this data source is the WRONG one. `vault_kv_secret` reads a
#           KV **v1** mount; `secret/` in this lab is KV **v2**, and the two
#           are different APIs behind the same-looking path. Enable the
#           toggle and run `terraform plan` — read the error before you fix
#           anything, because that error is the one you will meet again on
#           every Vault integration you ever build.
#
#           The v2 data source does not take a `path`. It takes the mount
#           and the path within the mount, separately. Confirm the argument
#           names the same way you confirmed the banner attribute in TASK 2:
#
#             terraform providers schema -json | jq '.provider_schemas
#               | .["registry.terraform.io/hashicorp/vault"].data_source_schemas
#               | keys'
#
#           Two things change when you fix this: the data source type here,
#           and the address it is referenced by in `local.vault_manager`
#           below. A resource's address is its type plus its name — change
#           the type and every reference to it moves too.
data "vault_kv_secret" "manager" {
  count = var.credentials_from_vault ? 1 : 0

  path = "${var.vault_mount}/${var.vault_secret_path}" # ← TODO 4.1: v1 shape
}

# ── Which credentials win ───────────────────────────────────────────
locals {
  # `one()` turns a zero-or-one list into null-or-the-value. It is the
  # idiomatic companion to `count` on a conditional data source, and it is
  # why the PART A path never touches Vault: at count = 0 the provider is
  # not even configured, so no token is required to run PART A.
  vault_manager = one(data.vault_kv_secret.manager[*].data)

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
