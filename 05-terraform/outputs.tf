#output "config_group_id" {
#  description = "Use this id in the module 6 exercise."
#  value       = sdwan_configuration_group.this.id
#}

output "prefix" {
  value = local.prefix
}

# Which way PART B resolved. The value is deliberately a description of the
# source and never the secret itself — an output is written to state and
# printed to a terminal, which are two places a password must not be.
output "credentials_source" {
  description = "Where the Manager credentials came from on this run."
  value       = var.credentials_from_vault ? "vault: ${var.vault_mount}/${var.vault_secret_path}" : "environment: TF_VAR_vmanage_*"
}
