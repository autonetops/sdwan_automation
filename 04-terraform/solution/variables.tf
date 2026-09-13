# ─────────────────────────────────────────────────────────────────────
# Inputs
#
# Credentials show up here as variables — never as values. Where those
# values come from changes once during this module:
#
#   PART A  the shell exports TF_VAR_vmanage_*   (source ../scripts/vault-env.sh)
#   PART B  Terraform reads Vault itself         (TASK 4, var below)
#
# Part B is the one you want in a pipeline: the only secret anyone holds
# is a Vault token, and Terraform fetches the rest at plan time.
# ─────────────────────────────────────────────────────────────────────

variable "credentials_from_vault" {
  description = <<-EOT
    false → Manager credentials arrive as TF_VAR_vmanage_* (PART A).
    true  → Terraform reads them from Vault itself (PART B / TASK 4).
  EOT
  type        = bool

  # The finished version defaults to the Vault path: the fallback is there
  # for the environment that already fetched the secret some other way (the
  # GitHub workflow does exactly that), not for daily use.
  default = true
}

# ── PART A credentials ──────────────────────────────────────────────
# Optional on purpose: once credentials_from_vault = true, nothing sets
# these and Terraform must not demand them.

variable "vmanage_url" {
  description = "Manager URL. Comes from Vault via TF_VAR_vmanage_url. Unused when credentials_from_vault = true."
  type        = string
  default     = null
}

variable "vmanage_username" {
  description = "Unused when credentials_from_vault = true."
  type        = string
  default     = null
  sensitive   = true
}

variable "vmanage_password" {
  description = "Unused when credentials_from_vault = true."
  type        = string
  default     = null
  sensitive   = true
}

# ── PART B: where the secret lives ──────────────────────────────────
# These are addresses, not secrets — they belong in version control. The
# token that opens them does not: it stays in VAULT_TOKEN.

variable "vault_address" {
  description = "Vault address. VAULT_ADDR overrides it for the provider."
  type        = string
  default     = "https://vault.autonetops.com"
}

variable "vault_mount" {
  description = "KV v2 mount holding the Manager secret."
  type        = string
  default     = "secret"
}

variable "vault_secret_path" {
  description = "Path of the secret INSIDE the mount — no mount prefix, no /data."
  type        = string
  default     = "sdwan/manager"
}

# ── The rest ────────────────────────────────────────────────────────

variable "student" {
  description = "Your bootcamp number — becomes the prefix on everything you create."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{2}$", var.student))
    error_message = "Use two digits. e.g. \"07\"."
  }
}

variable "banner_motd" {
  description = "The text we push to the fabric. This is the module's visible change."
  type        = string
  default     = "Managed by Terraform - AutoNetOps Bootcamp"
}
