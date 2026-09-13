# ─────────────────────────────────────────────────────────────────────
# PART C — the state stops being yours (TASK 5, solved)
#
# Local state is a file on one laptop: no lock, no backup, no second reader,
# and — the one that actually bites — invisible to the pipeline, whose `plan`
# and `apply` are separate containers. With local state the apply job starts
# from an empty state every single run.
#
# It is also a credential file. PART B has Terraform read the Manager secret
# from Vault, and Terraform persists every data source it reads: into state,
# and into any saved plan. `sensitive` redacts output, not bytes on disk.
# Which is the real argument for putting state somewhere with access control,
# versioning and an audit trail.
#
# GitLab ships a Terraform state backend on every tier: the standard `http`
# backend with GitLab as the server. Locking, versioning, and one authority
# the whole team plans against.
#
# ── Why this block is empty ─────────────────────────────────────────
# A backend block cannot reference variables — it is read before Terraform
# evaluates anything. So it stays empty (a "partial configuration") and the
# real values arrive at init time, from whichever of the two sources fits:
#
#   Laptop:   terraform init -migrate-state -backend-config=backend.hcl
#             (see backend.hcl.example; TF_HTTP_USERNAME / TF_HTTP_PASSWORD
#             carry the credentials so no token touches disk)
#
#   Pipeline: TF_HTTP_ADDRESS and friends, exported in .gitlab-ci.yml from
#             $CI_PROJECT_ID and $CI_JOB_TOKEN. The job authenticates as
#             itself, for the length of the job. Nobody issues it a secret.
#
# One config, many states. That is the point of a partial configuration.
#
# ⚠️ Reading this directory without GitLab credentials? `terraform init
#    -backend=false` initialises the providers and skips the backend, which
#    is enough for `terraform validate` and `terraform providers schema`.
terraform {
  backend "http" {}
}
