terraform {
  required_version = ">= 1.6"

  required_providers {
    sdwan = {
      source  = "CiscoDevNet/sdwan"
      version = "~> 0.11.4"
    }
    vault = {
      source  = "hashicorp/vault"
      version = "5.11.0"
    }
  }

  # State lives on disk here. Module 6 moves it to GitLab.
}

