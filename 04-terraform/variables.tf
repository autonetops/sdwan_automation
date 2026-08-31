variable "vmanage_url" {
  description = "Manager URL. Comes from Vault via TF_VAR_vmanage_url."
  type        = string
}

variable "vmanage_username" {
  type      = string
  sensitive = true
}

variable "vmanage_password" {
  type      = string
  sensitive = true
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
