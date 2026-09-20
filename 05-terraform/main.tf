# ─────────────────────────────────────────────────────────────────────
# Module 5 — the same change as module 4, now declarative
#
#
# The module runs in three parts. This file is PART A:
#
#   PART A  the change itself          locals.tf    TASK 1
#                                      main.tf      TASK 2, 3
#   PART B  credentials out of Vault   vault.tf     TASK 4
#   PART C  state in GitLab            backend.tf   TASK 5
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
# You should create a list of config groups in the terraform.tfvars
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

# ── TASK 3 ──────────────────────────────────────────────────────────
# Uncomment the block and give `for_each` its map.
# Hints: for_each takes a map, not a list — see `sla_class` above.
#        The list is at local.policy_file.sdwan.policy_objects.policer.
#        Key on `name`: the key becomes the resource address, so it must be
#        stable (key on an index and inserting a policer recreates the rest).

#resource "sdwan_policer_policy_object" "this" {
#  for_each      = ....
#  name          = each.value.name
#  burst         = each.value.burst
#  exceed_action = each.value.exceed_action
#  rate          = each.value.rate
#}

# ── TASK 4 is in vault.tf, TASK 5 in backend.tf ─────────────────────
