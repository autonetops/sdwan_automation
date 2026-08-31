# ─────────────────────────────────────────────────────────────────────
# Module 4 — the same change as module 3, now declarative
#
# In module 3 you wrote the "how": POST, grab the id, poll, handle failure.
# Here you write only the "what", and the provider handles the rest.
#
# The point of this lesson is NOT that Terraform is better. It is that
# Terraform is only usable by someone who understands what it is hiding —
# which is exactly what you implemented by hand an hour ago.
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

# ── STEP 1 ──────────────────────────────────────────────────────────
# A system feature profile to hold the banner parcel.
resource "sdwan_system_feature_profile" "bootcamp" {
  name        = "${local.prefix}system-profile"
  description = "System feature profile created in the automation bootcamp"
}

# ── STEP 2 ──────────────────────────────────────────────────────────
# The banner. This is the change that shows up in the plan and in the fabric.
#
# The MOTD attribute is called `motd`, not `message_of_the_day`. Found with
# `terraform providers schema -json` — and that is how you settle any attribute
# question, in any provider, without depending on the docs being current.
resource "sdwan_system_banner_feature" "motd" {
  name               = "${local.prefix}banner"
  description        = "MOTD managed by Terraform"
  feature_profile_id = sdwan_system_feature_profile.bootcamp.id
  login              = var.banner_motd

  motd = var.banner_motd
}

# ── STEP 3 ──────────────────────────────────────────────────────────
# The config group that ties the profile together.
resource "sdwan_configuration_group" "bootcamp" {
  name        = "${local.prefix}config-group"
  description = "Config group for the automation bootcamp"
  solution    = "sdwan"

  feature_profile_ids = [
    sdwan_system_feature_profile.bootcamp.id
  ]
}
