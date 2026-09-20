variable "credentials_from_vault" {
  description = <<-EOT
    false → Manager credentials arrive as TF_VAR_vmanage_* (PART A).
    true  → Terraform reads them from Vault itself (PART B / TASK 4).
  EOT
  type        = bool

  default = true
}


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
  description = "Vault userpass password. Required when vault_username is set."
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
  default     = null
}


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
