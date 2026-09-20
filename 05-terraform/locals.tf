locals {
  prefix = var.student

  # ── TASK 1 ────────────────────────────────────────────────────────
  # Read configs/policy_objects.yaml into a Terraform object.
  # Hints: path.module (not "./"), file(), yamldecode().
  policy_file = ....

  # A `for` in braces with `key => value` gives a map — what for_each needs.
  application_list = {
    for app in local.policy_file.sdwan.policy_objects.application_list : app.name => app
  }
}
