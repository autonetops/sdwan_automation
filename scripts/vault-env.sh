#!/usr/bin/env bash
# Exporta as credenciais do Manager a partir do Vault.
#
# Uso:  source scripts/vault-env.sh
#
# Requer VAULT_ADDR e VAULT_TOKEN já no ambiente. Nada é escrito em disco —
# credencial que toca o disco vira credencial vazada mais cedo ou mais tarde.

set -u

: "${VAULT_ADDR:=https://vault.autonetops.com}"
: "${VAULT_SDWAN_MOUNT:=secret}"
: "${VAULT_SDWAN_PATH:=sdwan/manager}"

if [ -z "${VAULT_TOKEN:-}" ]; then
  echo "VAULT_TOKEN não definido. Peça o seu ao instrutor." >&2
  return 1 2>/dev/null || exit 1
fi

if ! command -v vault >/dev/null 2>&1; then
  echo "CLI do vault não encontrada. Instale ou use o fallback do .env." >&2
  return 1 2>/dev/null || exit 1
fi

_secret="${VAULT_SDWAN_MOUNT}/${VAULT_SDWAN_PATH}"

VMANAGE_URL=$(vault kv get -field=url "${_secret}") || return 1 2>/dev/null || exit 1
VMANAGE_USERNAME=$(vault kv get -field=username "${_secret}")
VMANAGE_PASSWORD=$(vault kv get -field=password "${_secret}")

export VMANAGE_URL VMANAGE_USERNAME VMANAGE_PASSWORD

# O provider do Terraform lê TF_VAR_*.
export TF_VAR_vmanage_url="${VMANAGE_URL}"
export TF_VAR_vmanage_username="${VMANAGE_USERNAME}"
export TF_VAR_vmanage_password="${VMANAGE_PASSWORD}"

echo "Credenciais carregadas para ${VMANAGE_URL} (usuário ${VMANAGE_USERNAME})."
unset _secret
