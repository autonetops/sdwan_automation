# O provider oficial da Cisco para Catalyst SD-WAN.
#
# ⚠️ PIN DE VERSÃO: os nomes de resource mudaram bastante entre as versões
#    0.x deste provider (`..._profile_parcel` virou `..._feature` em alguns
#    releases). Fixe a versão e, quando algo não existir, consulte o schema
#    de verdade em vez de adivinhar:
#
#        terraform providers schema -json | jq '.provider_schemas
#          | .["registry.terraform.io/ciscodevnet/sdwan"].resource_schemas
#          | keys'
#
#    Ler o schema do provider é uma habilidade de automação, não um contorno.

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
  insecure = true # lab com certificado self-signed
}
