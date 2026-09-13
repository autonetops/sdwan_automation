# Cisco's official provider for Catalyst SD-WAN, plus HashiCorp's Vault
# provider (PART B) — the one that lets Terraform fetch its own credentials
# instead of trusting whatever the shell exported.
#
# ⚠️ VERSION PINNING: resource names moved around a lot across the 0.x
#    releases of the sdwan provider (`..._profile_parcel` became `..._feature`
#    in some releases). Pin the version, and when something doesn't exist,
#    read the real schema instead of guessing:
#
#        terraform providers schema -json | jq '.provider_schemas
#          | .["registry.terraform.io/ciscodevnet/sdwan"].resource_schemas
#          | keys'
#
#    Reading a provider's schema is an automation skill, not a workaround.

terraform {
  required_version = ">= 1.6"

  required_providers {
    sdwan = {
      source  = "CiscoDevNet/sdwan"
      version = "~> 0.11"
    }
    vault = {
      source  = "hashicorp/vault"
      version = "5.11.0"
    }
  }

  # State lives on disk for PART A and PART B. PART C moves it to GitLab —
  # see backend.tf.
}

# Note what this block does NOT contain: a credential. It contains a
# reference to one. `local.manager` is resolved in vault.tf, and which way
# it resolves is the whole of PART B.
provider "sdwan" {
  url      = local.manager.url
  username = local.manager.username
  password = local.manager.password
  insecure = true # lab with a self-signed certificate
}
