#!/usr/bin/env sh
# ─────────────────────────────────────────────────────────────────────
# Stage 1 of the pipeline — the data model's semantic rules.
#
#     ./validate-data-model.sh [path/to/fabric.yaml]
#
# Exit 0 = the change may proceed to plan. 1 = it may not.
#
# There are two kinds of check in the validate stage and they live in two
# different places, on purpose:
#
#   SHAPE      `terraform validate` on 06-pipeline/terraform. Is the YAML
#              decodable, do the keys the configuration reads exist, does
#              the HCL make sense? Terraform already answers all of that,
#              offline, and re-implementing it here would be a second
#              source of truth about the schema.
#
#   MEANING    this script. `motd` being a string is shape. A string
#              containing "CHANGEME" is a perfectly good string that must
#              not reach a router.
#
# Neither needs Vault, the Manager or the network. That is the point: this
# is the gate that still works on the day the thing it is gating is down.
#
# Written in `sh` and yq rather than a program, because a validator nobody
# can run on their laptop in two seconds is a validator people route around.
# ─────────────────────────────────────────────────────────────────────

set -u

MODEL="${1:-$(dirname "$0")/data/fabric.yaml}"

if ! command -v yq >/dev/null 2>&1; then
  echo "yq is not installed. https://github.com/mikefarah/yq — one binary." >&2
  exit 127
fi

if [ ! -f "$MODEL" ]; then
  echo "No data model at $MODEL" >&2
  exit 1
fi

echo "── VALIDATE $MODEL ──"
failed=0

# check "<what it means>" "<yq expression that must be true>"
#
# `yq -e` exits non-zero when the expression is false or null, which is what
# turns each rule into a one-liner instead of a parser.
check() {
  if yq -e "$2" "$MODEL" >/dev/null 2>&1; then
    printf '  \033[32m✓\033[0m %s\n' "$1"
  else
    printf '  \033[31m✗\033[0m %s\n' "$1"
    failed=1
  fi
}

check "student is two digits (it becomes your ws<NN>- prefix)" \
  '.sdwan.student | test("^[0-9]{2}$")'

check "the MOTD banner is not empty" \
  '.sdwan.system.banner.motd | length > 0'

check "the login banner is not empty" \
  '.sdwan.system.banner.login | length > 0'

# A banner is read by everyone who logs in, every day, for as long as nobody
# notices — which is how CHANGEME ends up in a customer screenshot.
check "no placeholder text in the banners" \
  '[.sdwan.system.banner.motd, .sdwan.system.banner.login]
   | map(test("(?i)CHANGEME|TODO|FIXME|XXX")) | any | not'

# IOS-XE terminates a banner with a delimiter, and the rendered CLI uses ^C.
# Text carrying the delimiter truncates the banner there: the config applies,
# and it is wrong.
check "no ^C banner delimiter in the banners" \
  '[.sdwan.system.banner.motd, .sdwan.system.banner.login]
   | map(test("\^C")) | any | not'

# The rule a schema cannot express. Terraform prefixes the name with ws<NN>-,
# so a name that carries the prefix already becomes ws07-ws07-pipeline —
# valid, deployable and wrong. Knowing that is knowledge about the pipeline,
# not about the shape of the document.
check "config_group.name does not already carry a ws<NN>- prefix" \
  '.sdwan.config_group.name | test("^ws[0-9]") | not'

check "config_group.description is not empty (in six months it is the only clue)" \
  '.sdwan.config_group.description | length > 0'

# A change that targets nothing cannot be verified, and an unverifiable
# change is the one you should not be pushing through a pipeline.
check "targets.edges names at least one device" \
  '.sdwan.targets.edges | length > 0'

check "targets.edges has no duplicates" \
  '.sdwan.targets.edges | length == (unique | length)'

echo
if [ "$failed" -eq 0 ]; then
  echo "The data model is valid. Safe to plan."
else
  echo "Fix the ✗ lines above. Nothing reaches the fabric until they pass."
fi
exit "$failed"
