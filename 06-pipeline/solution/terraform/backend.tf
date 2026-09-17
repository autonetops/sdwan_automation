# ─────────────────────────────────────────────────────────────────────
# State in GitLab — module 5 PART C, applied to module 6's own root.
#
# `plan`, `deploy` and `test` are three jobs in three containers. With a
# local state file the deploy job would start from an empty state on every
# run and try to create a config group that already exists. Shared state is
# not a nicety in a pipeline, it is the thing that makes it correct.
#
# The block is EMPTY — a partial configuration. A backend block cannot use
# variables (it is read before Terraform evaluates anything), so every
# argument arrives from the environment as TF_HTTP_*, set in .gitlab-ci.yml.
# That is what makes one configuration usable from a laptop and from a
# pipeline without editing it.
#
# It lives in its own file rather than inside versions.tf for a practical
# reason: the GitHub workflow has no credentials for GitLab-managed state,
# so it deletes this one file and falls back to local state. You cannot
# delete a backend block that shares a file with required_providers.
# ─────────────────────────────────────────────────────────────────────

terraform {
  backend "http" {}
}
