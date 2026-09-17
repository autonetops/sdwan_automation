# ─────────────────────────────────────────────────────────────────────
# TASK 1, solved — the data model, read by Terraform itself
#
# There is no renderer here. No script turns YAML into tfvars, because
# Terraform has read YAML natively since 0.12:
#
#     yamldecode(file(...))  →  an ordinary Terraform object
#
# That is the whole integration. One file is the change, Terraform reads
# it, and nothing sits in between to drift or to be forgotten.
# ─────────────────────────────────────────────────────────────────────

locals {
  # `path.module` and not a bare relative path. `file("../data/fabric.yaml")`
  # resolves against the process's working directory, which is the directory
  # you happen to be standing in — fine on a laptop, wrong the moment CI runs
  # `terraform -chdir=…`. `path.module` is where this .tf file lives, which is
  # the thing you actually meant.
  model = yamldecode(file("${path.module}/../../data/fabric.yaml"))

  sdwan = local.model.sdwan

  # One shared Manager for the whole class. Everything carries the prefix.
  prefix = "ws${local.sdwan.student}-"
  name   = "${local.prefix}${local.sdwan.config_group.name}"

  targets = local.sdwan.targets.edges
}
