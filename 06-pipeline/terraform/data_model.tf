# ─────────────────────────────────────────────────────────────────────
# TASK 1 — the data model, read by Terraform itself
#
# There is no renderer in this module. No script turns YAML into tfvars,
# because Terraform does not need one — it has read YAML natively since
# 0.12. One built-in function is the entire integration:
#
#     <something>decode(file(...))  →  an ordinary Terraform object
#
# One file is the change, Terraform reads it, and nothing sits in between
# to drift or to be forgotten.
# ─────────────────────────────────────────────────────────────────────

locals {
  # TASK 1.1: this is the wrong decoder, and `terraform plan` will tell you
  #           so in its first ten lines. Fix the one word.
  #
  #           Not a trick question — but worth noticing that Terraform ships
  #           decoders for YAML, JSON, CSV and base64, which is why "we need
  #           a script to convert the data model" is usually untrue.
  #
  #           `terraform console` is the fastest way to try a decoder without
  #           running a plan — and `terraform validate` catches this one
  #           offline, with no credentials and no fabric.
  model = jsondecode(file("${path.module}/../data/fabric.yaml"))

  sdwan = local.model.sdwan

  # `path.module` and not a bare relative path, above. `file("../data/…")`
  # resolves against the process's working directory — the directory you
  # happen to be standing in. Fine on a laptop, wrong the moment CI runs
  # `terraform -chdir=…`. `path.module` is where this .tf file lives, which
  # is the thing you actually meant.

  # One shared Manager for the whole class. Everything carries the prefix.
  prefix = "ws${local.sdwan.student}-"
  name   = "${local.prefix}${local.sdwan.config_group.name}"

  targets = local.sdwan.targets.edges
}
