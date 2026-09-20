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

  backend "http" {

  }
}