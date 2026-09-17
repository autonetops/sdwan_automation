output "config_group_name" {
  description = "What the pipeline created. Prefixed, so the class does not collide."
  value       = local.name
}

output "config_group_id" {
  value = sdwan_configuration_group.pipeline.id
}

output "targets" {
  description = "The edges this change was verified against."
  value       = local.targets
}

output "banner_motd" {
  description = "Straight from the data model — the visible change."
  value       = local.sdwan.system.banner.motd
}

# Which way the credentials resolved. Deliberately a description of the
# source and never the secret: an output is written to state and printed to
# a terminal, which are two places a password must not be.
output "credentials_source" {
  value = var.credentials_from_vault ? "vault: ${var.vault_mount}/${var.vault_secret_path}" : "environment: TF_VAR_vmanage_*"
}
