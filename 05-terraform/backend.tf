# ─────────────────────────────────────────────────────────────────────
# PART C — the state stops being yours (TASK 5)
#
# Until now `terraform.tfstate` has been a file in this directory. Ask what
# that actually means:
#
#   • It is on ONE laptop. Nobody else can plan against it, so nobody else
#     can be told "you are about to destroy something".
#   • It is not backed up. Lose it and Terraform forgets it owns the config
#     group — the next apply tries to create it again, and the fabric says
#     the name is taken.
#   • It has no lock. Two people applying at once is not a merge conflict,
#     it is two writers on one fabric.
#   • It contains your credentials in cleartext. From PART B onward Terraform
#     reads the Manager secret itself, and Terraform persists every data
#     source it reads — into the state file and into any saved plan. The
#     `sensitive` flag redacts output, not bytes on disk.
#   • The pipeline never had it at all. Look at .gitlab-ci.yml: `plan` and
#     `apply` are separate jobs in separate containers. With local state the
#     apply job starts from an empty state every time. That bug is invisible
#     until the day it duplicates everything you own.
#
# GitLab ships a Terraform state backend on every tier — the `http` backend
# with GitLab as the server. It gives you locking, versioning, and one
# authority the whole team plans against.
#
# ── TASK 5 ──────────────────────────────────────────────────────────
# TASK 5.1: uncomment the block below, then:
#
#     cp backend.hcl.example backend.hcl     # edit it: project id + state name
#     export TF_HTTP_USERNAME="<your gitlab username>"
#     export TF_HTTP_PASSWORD="<PAT, scope: api>"
#     terraform init -migrate-state -backend-config=backend.hcl
#
# Terraform will show you what it is about to move and ask for a yes. Say
# yes, then confirm the local file is now inert:
#
#     terraform state list              # served from GitLab
#     mv terraform.tfstate /tmp/        # and plan again — still works
#
# Then open GitLab → Operate → Terraform states. Your state is there, with
# a serial number that goes up on every apply, and a lock you can see being
# taken while an apply runs.
#
# ── Why the block is empty ──────────────────────────────────────────
# A backend block cannot use variables — it is read before Terraform
# evaluates anything. So it stays empty here (a "partial configuration")
# and the values arrive from -backend-config at init time. That is not a
# workaround; it is how you keep one config that many people, and a
# pipeline, point at different state.

# terraform {
#   backend "http" {}
# }
