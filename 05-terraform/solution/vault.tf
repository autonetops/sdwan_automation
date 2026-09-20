ephemeral "vault_kv_secret_v2" "manager" {
  count = var.credentials_from_vault ? 1 : 0

  mount = var.vault_mount
  name  = var.vault_secret_path
}

locals {
  vault_manager = one(ephemeral.vault_kv_secret_v2.manager[*].data)

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
