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
  motd               = var.banner_motd
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



## (CLASSIC) POLICY OBJECTS
resource "sdwan_sla_class_policy_object" "this" {
  for_each = { for sla in local.policy_file.sdwan.policy_objects.sla_class : sla.name => sla }
  name     = each.value.name
  loss     = each.value.loss
  latency  = each.value.latency
}

resource "sdwan_application_list_policy_object" "this" {
  for_each = local.application_list
  name     = each.value.name
  entries  = [for app in each.value.applications : { "application" : app }]
}

resource "sdwan_policer_policy_object" "this" {
  for_each      = { for policer in local.policy_file.sdwan.policy_objects.policer : policer.name => policer }
  name          = each.value.name
  burst         = each.value.burst
  exceed_action = each.value.exceed_action
  rate          = each.value.rate
}

# ── TASK 3 is in backend.tf ──────────────────
