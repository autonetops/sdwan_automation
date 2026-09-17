# ─────────────────────────────────────────────────────────────────────
# Inputs
#
# Note how few there are, and note what is NOT among them: nothing that
# describes the change. The banner, the names, the targets all live in
# data/fabric.yaml, where a reviewer can read them.
#
# What is left here is plumbing — where Vault is, how to reach it — and
# plumbing is exactly what belongs in variables rather than in a data model.
# ─────────────────────────────────────────────────────────────────────

variable "credentials_from_vault" {
  description = <<-EOT
    true  → Terraform reads the Manager credentials from Vault itself.
    false → they arrive as TF_VAR_vmanage_* (the GitHub workflow does this).
  EOT
  type        = bool
  default     = true
}

variable "vmanage_url" {
  description = "Unused when credentials_from_vault = true."
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

variable "vault_address" {
  description = "Vault address. VAULT_ADDR overrides it for the provider."
  type        = string
  default     = "https://vault.autonetops.com"
}

variable "vault_username" {
  description = "Vault userpass username. Null → authenticate with VAULT_TOKEN."
  type        = string
  default     = null
}

variable "vault_password" {
  description = "Required when vault_username is set."
  type        = string
  default     = null
  sensitive   = true

  validation {
    condition     = var.vault_username == null || var.vault_password != null
    error_message = "vault_username is set, so vault_password must be too (export TF_VAR_vault_password)."
  }
}

variable "vault_mount" {
  description = "KV v2 mount holding the Manager secret."
  type        = string
  default     = "workshop"
}

variable "vault_secret_path" {
  description = "Path of the secret INSIDE the mount — no mount prefix, no /data."
  type        = string
  default     = "sdwan"
}
