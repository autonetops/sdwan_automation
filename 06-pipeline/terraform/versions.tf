terraform {
  # `check` blocks arrived in 1.5. Preconditions and postconditions in 1.2.
  # All three appear in verify.tf, and the difference between them is the
  # whole lesson of this module.
  required_version = ">= 1.10"

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

  # No backend block: this directory runs on your laptop, on a local state
  # file, which is all you need to work through the TASKs below.
  #
  # The solution carries `backend "http" {}` because the PIPELINE needs it —
  # `plan`, `deploy` and `test` are three jobs in three containers, and with
  # local state the deploy job would start from an empty state every run and
  # try to create a config group that already exists. See module 5 PART C.
}
