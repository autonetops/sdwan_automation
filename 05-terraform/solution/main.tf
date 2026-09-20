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