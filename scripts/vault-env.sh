#!/usr/bin/env bash
# Export the Manager credentials from Vault, for the tools that can't fetch
# them themselves (Terraform in module 5 PART A, mainly).
#
# Usage:  source scripts/vault-env.sh
#
# Requires VAULT_ADDR, VAULT_USERNAME and VAULT_PASSWORD in the environment.
# Nothing is written to disk — a credential that touches disk becomes a leaked
# credential sooner or later.
#
# The Python toolkit does NOT need this: sdwan_toolkit.vault talks to Vault
# directly. This script exists for the TF_VAR_* handoff and nothing else.

set -u

: "${VAULT_ADDR:=https://vault.autonetops.com}"
: "${VAULT_SDWAN_MOUNT:=workshop}"
: "${VAULT_SDWAN_PATH:=sdwan}"

if [ -z "${VAULT_USERNAME:-}" ] || [ -z "${VAULT_PASSWORD:-}" ]; then
  echo "VAULT_USERNAME and VAULT_PASSWORD must be set. Ask the instructor for yours." >&2
  return 1 2>/dev/null || exit 1
fi

if ! command -v vault >/dev/null 2>&1; then
  echo "The vault CLI was not found. Install it — this script is the only" >&2
  echo "place that needs it; the Python toolkit uses hvac." >&2
  return 1 2>/dev/null || exit 1
fi

# userpass login. The token lands in VAULT_TOKEN for the rest of this shell,
# and is short-lived by policy.
VAULT_TOKEN=$(vault write -field=token \
  "auth/userpass/login/${VAULT_USERNAME}" \
  password="${VAULT_PASSWORD}") || return 1 2>/dev/null || exit 1
export VAULT_TOKEN

_secret="${VAULT_SDWAN_MOUNT}/${VAULT_SDWAN_PATH}"

_url=$(vault kv get -field=url "${_secret}") || return 1 2>/dev/null || exit 1
_username=$(vault kv get -field=username "${_secret}")
_password=$(vault kv get -field=password "${_secret}")

# The Terraform provider reads TF_VAR_*. Note what is NOT exported: the
# VMANAGE_* trio is gone, because the Python toolkit has no environment
# fallback any more. One source of truth — see 01-vault-credentials.
export TF_VAR_vmanage_url="${_url}"
export TF_VAR_vmanage_username="${_username}"
export TF_VAR_vmanage_password="${_password}"
export TF_VAR_student="${WS_STUDENT:-00}"

echo "Credentials loaded for ${_url} (user ${_username})."

# ── Module 5, PART C: credentials for the GitLab state backend ──────
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

unset _secret _state_secret _url _username _password
