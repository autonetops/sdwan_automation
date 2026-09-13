# Note what this block does NOT contain: a credential. It contains a
# reference to one. `local.manager` is resolved in vault.tf, and which way
# it resolves is the whole of PART B.
provider "sdwan" {
  url      = local.manager.url
  username = local.manager.username
  password = local.manager.password
  insecure = true # lab with a self-signed certificate
}

provider "vault" {
  address = var.vault_address
  skip_child_token = true
  auth_login_userpass {
    username = var.vault_username
    password = var.vault_password
  }
}