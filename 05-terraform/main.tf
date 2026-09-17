# ─────────────────────────────────────────────────────────────────────
# Module 5 — the same change as module 4, now declarative
#
# In module 4 you wrote the "how": POST, grab the id, poll, handle failure.
# Here you write only the "what", and the provider handles the rest.
#
# The point of this lesson is NOT that Terraform is better. It is that
# Terraform is only usable by someone who understands what it is hiding —
# which is exactly what you implemented by hand an hour ago.
#
# The module runs in three parts. This file is PART A:
#
#   PART A  the change itself          main.tf      TASK 1, 2, 3
#   PART B  credentials out of Vault   vault.tf     TASK 4
#   PART C  state in GitLab            backend.tf   TASK 5
#
# Do them in order. Each one takes something you were holding by hand and
# gives it to the machine.
# ─────────────────────────────────────────────────────────────────────

locals {
  prefix = "${var.student}"
}

# ── Discovery ───────────────────────────────────────────────────────
# A data source instead of hardcoded UUIDs.
data "sdwan_device" "all" {}

locals {
  reachable_devices = [
    for d in data.sdwan_device.all.devices : d
    if d.reachability == "reachable"
  ]
}

# System feature profile to hold the banner parcel.
resource "sdwan_system_feature_profile" "this" {
  name        = "${local.prefix}-system-profile"
  description = "System feature profile created in the automation bootcamp"

}

# ── TASK 2 ──────────────────────────────────────────────────────────
# The banner. This is the change that shows up in the plan and in the fabric.
#
# TODO 2.1: this attribute is NOT called `message_of_the_day`. Find the right
#           name by reading the schema (the command is in versions.tf) and fix
#           the line marked below. This error is deliberate: reading a
#           provider's schema is the skill, not memorising attribute names.
resource "sdwan_system_banner_feature" "this" {
  name               = "${local.prefix}-banner"
  description        = "MOTD managed by Terraform"
  feature_profile_id = sdwan_system_feature_profile.this.id
  login              = var.banner_motd

  message_of_the_day = var.banner_motd # ← TODO 2.1: wrong attribute
}

# ── TASK 3 ──────────────────────────────────────────────────────────
# The config group that ties the profile together.
resource "sdwan_configuration_group" "this" {
  name        = "${local.prefix}-config-group"
  description = "Config group for the automation bootcamp"
  solution    = "sdwan"

  feature_profile_ids = [
    sdwan_system_feature_profile.this.id
  ]
}

# ── TASK 4 is in vault.tf, TASK 5 is in backend.tf ──────────────────
