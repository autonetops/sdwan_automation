# ─────────────────────────────────────────────────────────────────────
# TASKS 2, 3 and 4 — the fabric failing its own change
#
# The thesis of the whole bootcamp:
#
#     A change without automatic verification is not automation.
#     It is faster typing.
#
# In module 4 you wrote that verification by hand: snapshot, apply,
# snapshot, compare. Terraform has three constructs for the same job, and
# THEY ARE NOT INTERCHANGEABLE. Picking the wrong one gives you a pipeline
# that looks like it is checking something and is not:
#
#   ┌────────────────┬──────────────┬──────────────┬─────────────────────┐
#   │                │ evaluated    │ on failure   │ use it for          │
#   ├────────────────┼──────────────┼──────────────┼─────────────────────┤
#   │ precondition   │ before the   │ ERROR —      │ refusing to start   │
#   │                │ resource     │ stops the    │                     │
#   │                │              │ apply        │                     │
#   │ postcondition  │ after the    │ ERROR —      │ proving the change  │
#   │                │ object is    │ FAILS the    │ did no harm         │
#   │                │ read/created │ apply        │                     │
#   │ check block    │ plan AND     │ WARNING —    │ things worth        │
#   │                │ apply        │ apply still  │ knowing that are    │
#   │                │              │ SUCCEEDS     │ not yours to fix    │
#   └────────────────┴──────────────┴──────────────┴─────────────────────┘
#
# ⚠️ Read that last row twice. A `check` block CANNOT fail a pipeline. It
#    emits a warning and terraform exits 0. If the only verification in your
#    configuration is a check block, you have written a pipeline that reports
#    problems to a log nobody reads and then deploys anyway.
#
#    This is the single most common mistake people make with these three,
#    and it is invisible until the day it matters.
# ─────────────────────────────────────────────────────────────────────


# ── TASK 2 — the inputs to the gate (given) ─────────────────────────
# You write the precondition BLOCKS in main.tf. These two lists are the
# facts they act on.

locals {
  # Named in the data model but not in the fabric — a typo in
  # sdwan.targets.edges, and a far more common mistake than a device
  # actually being down.
  unknown_targets = [
    for hostname in local.targets : hostname
    if !contains(local.known_hostnames, hostname)
  ]

  # In the fabric, but not reachable right now.
  targets_down_before = [
    for hostname in local.targets : hostname
    if contains(local.known_hostnames, hostname) && !contains(local.reachable_before, hostname)
  ]
}


# ── TASK 3 — the proof ──────────────────────────────────────────────
# The "after" snapshot: the only thing in this configuration that can fail
# an apply which has ALREADY touched the fabric.
#
# `depends_on` is doing something specific and easy to miss. Without it,
# Terraform reads this data source during PLAN along with every other one,
# and the postcondition would be checking the fabric BEFORE the change —
# which would pass, always, and mean nothing. With it, the read is deferred
# to apply time, after the config group exists.

data "sdwan_device" "after" {
  depends_on = [
    sdwan_configuration_group.pipeline,
    sdwan_system_banner_feature.motd,
  ]

  lifecycle {
    postcondition {
      # TODO 3.1: assert that every hostname in `local.targets` is still
      #           reachable. Replace the `true` below.
      #
      #           `self` is how a postcondition refers to the object it is
      #           attached to — here, `self.devices`.
      #
      #           Make the comparison ASYMMETRIC, exactly as the module 4
      #           diff was: a target that came back reachable is fine, a
      #           target that went away is not. Hint: alltrue([...]) over
      #           local.targets, contains(...) over the reachable hostnames.
      #
      #           ⚠️ The placeholder below passes no matter what the fabric
      #              does. Leave it and you have a deploy stage that verifies
      #              nothing while looking like it does.
      #
      #              Terraform will not let you write `condition = true` here
      #              at all — "the condition expression must refer to at least
      #              one object from elsewhere in the configuration, or else
      #              its result would not be checking anything." Even the
      #              placeholder has to touch something real.
      condition     = length(self.devices) >= 0 # ← always true. Replace it.
      error_message = "REGRESSION: a target edge is unreachable AFTER the change. The apply has failed; the deploy job will roll the data model back to the previous commit."
    }
  }
}


# ── TASK 4 — the observation ────────────────────────────────────────
# Everything the gate should REPORT but must not abort on.
#
# A device that was down before and is still down after produces no finding
# in any diff — it did not change. Without something like this, nobody ever
# notices, and the fabric quietly degrades one device at a time between
# deployments.

check "shared_lab_health" {
  # A scoped data source: it belongs to the check, is read on every plan and
  # apply, and — unlike a top-level data source — an error reading it
  # downgrades to a warning instead of failing the run.
  data "sdwan_device" "observed" {}

  assert {
    # TODO 4.1: warn when ANY device in the lab is unreachable, not just
    #           your targets. Replace the `true`.
    #
    #           Then answer the question this raises: you now have the same
    #           fact expressed twice, once as an error (TASK 2) and once as
    #           a warning. Why is that not duplication? Write it down.
    condition     = length(data.sdwan_device.observed.devices) >= 0 # ← always true. Replace it.
    error_message = "Devices unreachable in the shared lab (not necessarily caused by this change)."
  }
}
