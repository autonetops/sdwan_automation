# ─────────────────────────────────────────────────────────────────────
# Módulo 4 — a mesma mudança do módulo 3, agora declarativa
#
# No módulo 3 você escreveu o "como": faça POST, pegue o id, faça polling,
# trate a falha. Aqui você escreve só o "o quê", e o provider cuida do resto.
#
# O ponto da aula NÃO é que Terraform é melhor. É que ele só é utilizável
# por quem entende o que ele está escondendo — que é exatamente o que você
# implementou na mão uma hora atrás.
# ─────────────────────────────────────────────────────────────────────

locals {
  prefixo = "ws${var.aluno}-"
}

# ── Descoberta ──────────────────────────────────────────────────────
# Data source em vez de UUID hardcoded.
data "sdwan_device" "todos" {}

locals {
  # LIÇÃO IMPORTANTE: repare no que NÃO existe aqui.
  #
  # O data source expõe device_id, hostname, reachability, serial_number,
  # site_id, state, status e uuid — e mais nada. Não há `personality`. Ou
  # seja: pelo Terraform você não consegue separar edge de controlador,
  # coisa que o `/dataservice/device` da API entrega de graça.
  #
  # É por isso que o toolkit em Python não vira lixo quando você adota
  # Terraform. O provider cobre o caminho declarativo; a API cobre o resto.
  # Ferramenta boa é a que você sabe quando NÃO usar.
  edges_alcancaveis = [
    for d in data.sdwan_device.todos.devices : d
    if d.reachability == "reachable"
  ]
}

# ── PASSO 1 ────────────────────────────────────────────────────────
# Feature profile de sistema: o contêiner dos parcels.
resource "sdwan_system_feature_profile" "bootcamp" {
  name        = "${local.prefixo}system-profile"
  description = "Feature profile de sistema criado no bootcamp de automação"
}

# ── PASSO 2 ────────────────────────────────────────────────────────
# O banner — a mudança que vai aparecer no plan e no fabric.
#
# O atributo do MOTD chama-se `motd`, não `message_of_the_day`. Descoberto
# com `terraform providers schema -json` — e é assim que se resolve qualquer
# dúvida de atributo, em qualquer provider, sem depender da documentação
# estar atualizada.
resource "sdwan_system_banner_feature" "motd" {
  name               = "${local.prefixo}banner"
  description        = "MOTD gerenciado por Terraform"
  feature_profile_id = sdwan_system_feature_profile.bootcamp.id
  login              = var.banner_motd

  motd = var.banner_motd
}

# ── PASSO 3 ────────────────────────────────────────────────────────
# O config group que amarra o profile.
resource "sdwan_configuration_group" "bootcamp" {
  name        = "${local.prefixo}config-group"
  description = "Config group do bootcamp de automação"
  solution    = "sdwan"

  feature_profile_ids = [
    sdwan_system_feature_profile.bootcamp.id
  ]
}
