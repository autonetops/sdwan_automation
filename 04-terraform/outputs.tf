output "config_group_id" {
  description = "Use this id in the module 5 exercise."
  value       = sdwan_configuration_group.bootcamp.id
}

output "discovered_devices" {
  description = "Reachable devices the data source found — no hardcoded UUIDs."
  value       = [for d in local.reachable_devices : d.hostname]
}

output "prefix" {
  value = local.prefix
}
