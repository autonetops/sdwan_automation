variable "vmanage_url" {
  description = "URL do Manager. Vem do Vault via TF_VAR_vmanage_url."
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

variable "aluno" {
  description = "Seu número no bootcamp — vira o prefixo de tudo que você criar."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{2}$", var.aluno))
    error_message = "Use dois dígitos. Ex: \"07\"."
  }
}

variable "banner_motd" {
  description = "O texto que vamos empurrar para o fabric. É a mudança visível do módulo."
  type        = string
  default     = "Gerenciado por Terraform - AutoNetOps Bootcamp"
}
