# ─────────────────────────────────────────────────────────────────────
# Module 5 — the same change as module 4, now declarative
#
#
# The module runs in three parts. This file is PART A:
#
#   PART A  the change itself          main.tf      TASK 1, 2
#   PART B  credentials out of Vault   vault.tf     TASK 3
#   PART C  state in GitLab            backend.tf   TASK 4
#
# Do them in order. Each one takes something you were holding by hand and
# gives it to the machine.
# ─────────────────────────────────────────────────────────────────────

locals {
  prefix = "${var.student}"
}


# System feature profile to hold the banner parcel.
resource "sdwan_system_feature_profile" "this" {
  name        = "${local.prefix}-system-profile"
  description = "System feature profile created in the automation bootcamp"

}

resource "sdwan_system_banner_feature" "this" {
  name               = "${local.prefix}-banner"
  description        = "MOTD managed by Terraform"
  feature_profile_id = sdwan_system_feature_profile.this.id
  login              = var.banner_motd
  motd = var.banner_motd
}

# ── TASK 2 ──────────────────────────────────────────────────────────
# The config group that ties the profile together.
# Let's explore loops (lists and sets) and the `for` expression. 
# You should create a list of config gorups in the terraform.tfvars 
# file and use it here to create multiple config groups.
# https://registry.terraform.io/providers/CiscoDevNet/sdwan/latest/docs/resources/configuration_group
resource "sdwan_configuration_group" "this" {
  name        = "${local.prefix}-config-group"
  description = "Config group for the automation bootcamp"
  solution    = "sdwan"

  feature_profile_ids = [
    sdwan_system_feature_profile.this.id
  ]
}

# ── TASK 3 is in backend.tf ──────────────────
