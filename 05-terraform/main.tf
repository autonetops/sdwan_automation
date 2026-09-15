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
  prefix = "ws${var.student}-"
}

# ── Discovery ───────────────────────────────────────────────────────
# A data source instead of hardcoded UUIDs.
data "sdwan_device" "all" {}

locals {
  # IMPORTANT LESSON: notice what is NOT here.
  #
  # The data source exposes device_id, hostname, reachability, serial_number,
  # site_id, state, status and uuid — and nothing else. There is no
  # `personality`. Which means: through Terraform you cannot tell an edge from
  # a controller, something `/dataservice/device` gives you for free.
  #
  # That is why the Python toolkit does not become junk when you adopt
  # Terraform. The provider covers the declarative path; the API covers the
  # rest. A good tool is one you know when NOT to use.
  reachable_devices = [
    for d in data.sdwan_device.all.devices : d
    if d.reachability == "reachable"
  ]
}

# ── TASK 1 ──────────────────────────────────────────────────────────
# A system feature profile to hold the banner parcel.
resource "sdwan_system_feature_profile" "bootcamp" {
  name        = "${local.prefix}system-profile"
  description = "System feature profile created in the automation bootcamp"

  # Guard, not decoration: without it, forgetting to load credentials shows
  # up as an authentication error from the provider, which sends you looking
  # at the Manager instead of at your shell. A precondition is the cheapest
  # documentation there is — it only speaks when you need it.
  lifecycle {
    precondition {
      condition     = local.manager.url != null && local.manager.password != null
      error_message = "No Manager credentials. PART A: run `source ../scripts/vault-env.sh`. PART B: set credentials_from_vault = true with VAULT_TOKEN exported."
    }
  }
}

# ── TASK 2 ──────────────────────────────────────────────────────────
# The banner. This is the change that shows up in the plan and in the fabric.
#
# TODO 2.1: this attribute is NOT called `message_of_the_day`. Find the right
#           name by reading the schema (the command is in versions.tf) and fix
#           the line marked below. This error is deliberate: reading a
#           provider's schema is the skill, not memorising attribute names.
resource "sdwan_system_banner_feature" "motd" {
  name               = "${local.prefix}banner"
  description        = "MOTD managed by Terraform"
  feature_profile_id = sdwan_system_feature_profile.bootcamp.id
  login              = var.banner_motd

  message_of_the_day = var.banner_motd # ← TODO 2.1: wrong attribute
}

# ── TASK 3 ──────────────────────────────────────────────────────────
# The config group that ties the profile together.
resource "sdwan_configuration_group" "bootcamp" {
  name        = "${local.prefix}config-group"
  description = "Config group for the automation bootcamp"
  solution    = "sdwan"

  feature_profile_ids = [
    sdwan_system_feature_profile.bootcamp.id
  ]
}

# ── TASK 4 is in vault.tf, TASK 5 is in backend.tf ──────────────────
