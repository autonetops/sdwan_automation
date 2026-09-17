terraform {
  # `check` blocks arrived in 1.5. Preconditions and postconditions in 1.2.
  # All three appear in verify.tf, and the difference between them is the
  # whole lesson of this module.
  required_version = ">= 1.5"

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

  # The backend lives in backend.tf, on its own. See that file for why.
}
