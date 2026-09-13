#!/usr/bin/env bash
# Export the Manager credentials from Vault.
#
# Usage:  source scripts/vault-env.sh
#
# Requires VAULT_ADDR and VAULT_TOKEN already in the environment. Nothing is
# written to disk — a credential that touches disk becomes a leaked credential
# sooner or later.

set -u

: "${VAULT_ADDR:=https://vault.autonetops.com}"
: "${VAULT_SDWAN_MOUNT:=secret}"
: "${VAULT_SDWAN_PATH:=sdwan/manager}"

if [ -z "${VAULT_TOKEN:-}" ]; then
  echo "VAULT_TOKEN is not set. Ask the instructor for yours." >&2
  return 1 2>/dev/null || exit 1
fi

if ! command -v vault >/dev/null 2>&1; then
  echo "The vault CLI was not found. Install it, or use the .env fallback." >&2
  return 1 2>/dev/null || exit 1
fi

_secret="${VAULT_SDWAN_MOUNT}/${VAULT_SDWAN_PATH}"

VMANAGE_URL=$(vault kv get -field=url "${_secret}") || return 1 2>/dev/null || exit 1
VMANAGE_USERNAME=$(vault kv get -field=username "${_secret}")
VMANAGE_PASSWORD=$(vault kv get -field=password "${_secret}")

export VMANAGE_URL VMANAGE_USERNAME VMANAGE_PASSWORD

# The Terraform provider reads TF_VAR_*.
export TF_VAR_vmanage_url="${VMANAGE_URL}"
export TF_VAR_vmanage_username="${VMANAGE_USERNAME}"
export TF_VAR_vmanage_password="${VMANAGE_PASSWORD}"
export TF_VAR_student="${WS_STUDENT:-00}"

echo "Credentials loaded for ${VMANAGE_URL} (user ${VMANAGE_USERNAME})."

# ── Module 4, PART C: credentials for the GitLab state backend ──────
# The http backend reads TF_HTTP_USERNAME and TF_HTTP_PASSWORD from the
# environment, which is why backend.hcl only ever holds addresses. If the
# instructor has stored a state token in Vault, pick it up here; otherwise
# stay quiet — PART C is not where most of the class is yet.
_state_secret="${VAULT_SDWAN_MOUNT}/${VAULT_GITLAB_STATE_PATH:-gitlab/terraform-state}"

if vault kv get -field=token "${_state_secret}" >/dev/null 2>&1; then
  TF_HTTP_USERNAME=$(vault kv get -field=username "${_state_secret}")
  TF_HTTP_PASSWORD=$(vault kv get -field=token "${_state_secret}")
  export TF_HTTP_USERNAME TF_HTTP_PASSWORD
  echo "GitLab state credentials loaded (user ${TF_HTTP_USERNAME})."
fi

unset _secret _state_secret
