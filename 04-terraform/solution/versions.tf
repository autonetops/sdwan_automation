# Cisco's official provider for Catalyst SD-WAN.
#
# ⚠️ VERSION PINNING: resource names moved around a lot across the 0.x
#    releases of this provider (`..._profile_parcel` became `..._feature` in
#    some releases). Pin the version, and when something doesn't exist, read
#    the real schema instead of guessing:
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
  }
}

provider "sdwan" {
  url      = var.vmanage_url
  username = var.vmanage_username
  password = var.vmanage_password
  insecure = true # lab with a self-signed certificate
}
