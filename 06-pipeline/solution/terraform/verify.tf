# ─────────────────────────────────────────────────────────────────────
# TASKS 2, 3 and 4, solved — the fabric failing its own change
#
# The thesis of the whole bootcamp:
#
#     A change without automatic verification is not automation.
#     It is faster typing.
#
# In module 4 you wrote that verification in Python: snapshot, apply,
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
# Which is exactly why all three are here.
# ─────────────────────────────────────────────────────────────────────


# ── TASK 2 — the gate (precondition, an ERROR) ──────────────────────
# Consumed by the preconditions on sdwan_system_feature_profile in main.tf.
#
# The decision worth arguing about in the room: in a shared lab, refusing to
# act because SOME device is down is unworkable — somebody always has one
# deliberately down, and a gate that fires on other people's work is a gate
# that gets commented out in week two.
#
# Refusing because a device THIS CHANGE TARGETS is down is a different thing
# entirely. That is what `sdwan.targets.edges` is for, and it is why the data
# model carries a key that produces no resource at all.

locals {
  # Named but not in the fabric — a typo in the data model, and a far more
  # common mistake than a device actually being down.
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


# ── TASK 3 — the proof (postcondition, an ERROR) ────────────────────
# The "after" snapshot, and the only part of this file that can fail an
# apply that has already touched the fabric.
#
# `depends_on` is doing something specific and easy to miss: without it,
# Terraform reads this data source during PLAN, along with every other one,
# and the postcondition would be checking the fabric BEFORE the change —
# which would pass, always, and mean nothing. With it, the read is deferred
# to apply time, after the config group exists.

data "sdwan_device" "after" {
  depends_on = [
    sdwan_configuration_group.pipeline,
    sdwan_system_banner_feature.motd,
  ]

  lifecycle {
    # `self` is how a postcondition refers to the object it is attached to.
    # The comparison is deliberately asymmetric, exactly as the Python
    # `compare()` was: a target that came back reachable is fine, a target
    # that went away is not.
    postcondition {
      condition = alltrue([
        for hostname in local.targets :
        contains([
          for d in self.devices : d.hostname if d.reachability == "reachable"
        ], hostname)
      ])
      error_message = "REGRESSION: a target edge is unreachable AFTER the change. The apply has failed; the deploy job will roll the data model back to the previous commit."
    }
  }
}


# ── TASK 4 — the observation (check block, a WARNING) ────────────────
# Everything the Python precheck REPORTED but refused to abort on.
#
# A device that was down before and is still down after produces no finding
# in any diff — it did not change. Without something like this, nobody ever
# notices it, and the fabric quietly degrades one device at a time between
# deployments.
#
# A warning is the honest severity here: it is real information, and it is
# not this change's fault.

check "shared_lab_health" {
  # A scoped data source: it belongs to the check, is read on every plan and
  # apply, and — unlike a top-level data source — an error reading it
  # downgrades to a warning instead of failing the run.
  data "sdwan_device" "observed" {}

  assert {
    condition = length([
      for d in data.sdwan_device.observed.devices : d.hostname
      if d.reachability != "reachable"
    ]) == 0

    error_message = "Devices unreachable in the shared lab (not necessarily caused by this change): ${join(", ", [
      for d in data.sdwan_device.observed.devices : d.hostname
      if d.reachability != "reachable"
    ])}"
  }
}
