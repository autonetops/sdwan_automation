output "config_group_id" {
  description = "Use este id no exercício do módulo 5."
  value       = sdwan_configuration_group.bootcamp.id
}

output "edges_descobertos" {
  description = "Dispositivos alcançáveis que o data source encontrou — sem UUID hardcoded."
  value       = [for d in local.edges_alcancaveis : d.hostname]
}

output "prefixo" {
  value = local.prefixo
}
