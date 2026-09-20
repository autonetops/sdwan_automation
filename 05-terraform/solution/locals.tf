# ─────────────────────────────────────────────────────────────────────
# PART A — the fabric config lives in YAML, not in HCL
#
# `configs/policy_objects.yaml` is the source of truth for the policy
# objects. Terraform reads it at plan time, so adding a policer to the
# fabric is a change to a YAML file — not to this code.
# ─────────────────────────────────────────────────────────────────────

locals {
  prefix = var.student

  policy_file = yamldecode(file("${path.module}/../configs/policy_objects.yaml"))
  application_list = {
    for app in local.policy_file.sdwan.policy_objects.application_list : app.name => app
  }
}
