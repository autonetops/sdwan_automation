# ─────────────────────────────────────────────────────────────────────
# The change
#
# Compare this with 05-terraform/main.tf. The resources are the same; what
# changed is where the values come from. Module 5 read `var.banner_motd`,
# set in a tfvars file that only a Terraform user reviews. Here every value
# is a field of `local.sdwan` — a YAML file a network engineer can read,
# diff and argue about in a merge request.
#
# That is the whole difference between infrastructure as code and
# infrastructure as *reviewable* code.
# ─────────────────────────────────────────────────────────────────────

# The fabric as it stands BEFORE the change. No depends_on, so Terraform
# reads it during plan — which is what lets the preconditions below refuse a
# change at plan time, before anything is written.
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

  lifecycle {
    # Given, as in module 5: a missing credential should send you to your
    # shell, not to the Manager.
    precondition {
      condition     = local.manager.url != null && local.manager.password != null
      error_message = "No Manager credentials. Export VAULT_TOKEN, or set credentials_from_vault = false and provide TF_VAR_vmanage_*."
    }

    # TASK 2.1: refuse the change when the data model names a device the
    #           fabric has never heard of. `local.unknown_targets` in
    #           verify.tf already computes the list — you write the
    #           precondition block that acts on it.
    #
    #           A precondition is an ERROR: it stops the plan. That is the
    #           right severity here, because the alternative is deploying a
    #           change nobody can verify.

    # TASK 2.2: refuse the change when a device THIS CHANGE TARGETS is
    #           already unreachable (`local.targets_down_before`).
    #
    #           The decision to justify in the README: why not refuse when
    #           ANY device in the lab is down? Twenty people share this
    #           fabric. Write down your answer — it is the difference
    #           between a gate people keep and a gate people delete.
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
