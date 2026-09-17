# ─────────────────────────────────────────────────────────────────────
# The change
#
# Compare this with 05-terraform/main.tf. The resources are the same; what
# changed is where the values come from. Module 5 read `var.banner_motd`,
# set in a tfvars file that only a Terraform user reviews. Here every value
# is a field of `local.sdwan`, which is a YAML file a network engineer can
# read, diff and argue about in a merge request.
#
# That is the entire difference between infrastructure as code and
# infrastructure as *reviewable* code.
# ─────────────────────────────────────────────────────────────────────

# The fabric as it stands BEFORE the change. No depends_on, so Terraform
# reads it during plan — which is what lets verify.tf refuse a change at
# plan time, before anything is written.
data "sdwan_device" "before" {}

locals {
  reachable_before = [
    for d in data.sdwan_device.before.devices : d.hostname
    if d.reachability == "reachable"
  ]
  known_hostnames = [for d in data.sdwan_device.before.devices : d.hostname]
}

resource "sdwan_system_feature_profile" "pipeline" {
  name        = "${local.name}-system"
  description = local.sdwan.config_group.description

  # The gate. See verify.tf — the preconditions live there, next to the
  # postcondition and the check, so the whole verification story is one file.
  lifecycle {
    precondition {
      condition     = local.manager.url != null && local.manager.password != null
      error_message = "No Manager credentials. Export VAULT_TOKEN, or set credentials_from_vault = false and provide TF_VAR_vmanage_*."
    }

    precondition {
      condition     = length(local.unknown_targets) == 0
      error_message = "sdwan.targets.edges names device(s) the fabric has never heard of: ${join(", ", local.unknown_targets)}. Check the hostnames the Manager reports."
    }

    precondition {
      condition     = length(local.targets_down_before) == 0
      error_message = "TARGET EDGE UNREACHABLE BEFORE THE CHANGE: ${join(", ", local.targets_down_before)}. Changing a device you cannot verify afterwards is not a change, it is a hope."
    }
  }
}

resource "sdwan_system_banner_feature" "motd" {
  name               = "${local.name}-banner"
  description        = "Banner managed by the module 6 pipeline"
  feature_profile_id = sdwan_system_feature_profile.pipeline.id

  motd  = local.sdwan.system.banner.motd
  login = local.sdwan.system.banner.login
}

resource "sdwan_configuration_group" "pipeline" {
  name        = local.name
  description = local.sdwan.config_group.description
  solution    = "sdwan"

  feature_profile_ids = [
    sdwan_system_feature_profile.pipeline.id
  ]
}
