# Module 4 — Change the fabric, and prove it (50 min)

The first time you write to the fabric — and the first time you make the
fabric prove you didn't break it. Those two are one module because separating
them teaches the wrong habit.

```
snapshot BEFORE  →  preview  →  deploy  →  wait  →  snapshot AFTER  →  compare
```

## The central idea of the bootcamp

> A change is only safe if you can **prove** the fabric came out the same or
> better.

Proving it requires a comparable snapshot, as data. Not a `show` command
pasted into the team chat.

## What we're learning

| Automation | SD-WAN |
|---|---|
| Normalize at the edge | Hyphenated keys, `state` vs `status` vs `operstate` |
| Model and serialize | `DeviceState`, `FabricSnapshot` as JSON |
| A diff with an opinion | Losing BFD is a regression; gaining isn't |
| Dry-run before writing | Config group `preview` |
| The async model and polling | `parentTaskId` → `/device/action/status/{id}` |
| An exit code a machine can act on | PASS / FAIL |

## The mental map, coming from templates

| What you know | What it's called now |
|---|---|
| Feature template | **Parcel** (inside a feature profile) |
| Device template | **Config group** |
| Attach | **Associate** + **deploy** |
| Variable CSV | **Device variables** |

Config groups require Manager 20.12+ / IOS-XE 17.12+. Classic templates still
exist and are still the reality of most brownfield fabrics — `attachfeature`
is the deploy equivalent, and the asynchronous task model is **identical** in
both. What you learn here applies to both worlds.

## Real-time vs. the statistics database

The distinction that most separates people who automate well from people who
take the Manager down:

| | `/dataservice/device/*` | `/dataservice/statistics/*` |
|---|---|---|
| Source | Queries the device **now**, across the control plane | Reads the statistics database |
| Cost | High — every call crosses the fabric | Low |
| Freshness | Instant | Minutes behind |
| Use for | Pre/post change | Trends, reports, dashboards |

This module uses real-time, because we want *now*. Which is exactly why the
client you built in module 3 has a rate limiter.

## The lesson that matters

Writing to the Manager is **not synchronous**. The POST returns an `id` and
walks away:

```
POST /v1/config-group/{id}/device/deploy   →  {"parentTaskId": "abc-123"}
                                                       │
GET /device/action/status/abc-123  ← polling ──────────┘
```

A script that doesn't wait **lies**. It reports success when all that happened
was the Manager accepting the request — before the fabric changed, or before
it failed.

This is also where module 3's `unwrap=False` earns its keep: the status
endpoint answers `{"summary": …, "data": […]}`, and `summary` is the only
place the task state lives. Unwrap it and you throw away the answer.

## Get to work

```bash
export WS_STUDENT=07
cd 04-change-and-verify

python exercise.py --list                   # find your config group
python exercise.py --snapshot before.json   # just look, change nothing
python exercise.py --preview                # the CLI that WOULD be pushed
python exercise.py --deploy                 # before → deploy → wait → after → verdict
```

Five tasks: `count_up()`, `collect()`, `my_config_group()` + `show_preview()`,
`run_deploy()`, and `change_and_verify()` — the one that ties them together.

Check the logic without touching the lab:

```bash
python -m pytest ../tests/test_diff.py ../tests/test_tasks.py -q
```

While the deployment runs, open the GUI under **Monitor → Tasks**. That's the
same task your code is polling. This is the moment the API stops being
abstract.

## The diff is asymmetric on purpose

Gaining a BFD session is good. Losing one is bad. A text `diff` doesn't know
that — yours does. Only regressions fail the change; improvements appear in
the report and don't block.

That opinion is what lets module 6's pipeline decide on its own between moving
forward and rolling back.

`compare()` also checks the **peer list**, not just the count. "6 before, 6
after" can still hide a swapped peer — and a tunnel that moved is a change you
want to know about.

## Namespace

The lab is shared. Everything you create carries `ws<NN>-`. The code raises
`SystemExit` if `WS_STUDENT` isn't set — on purpose.

## When a payload returns 400

Don't guess. Open the browser Developer Tools, perform the same action by
clicking in the GUI, and compare the request body. The GUI uses exactly the
same API you do. **That's the technique, not a workaround.**

## Proof you actually ran it

Two answers:

1. **Which edge has the most BFD sessions `up`?**
2. **Did your change pass or fail — and what did the diff say?**

## Something to think about

`compare()` only looks at the **difference**. A device that was already down
before and is still down after produces no finding at all. Is that correct, or
a defect?

(The answer lives in module 6's `precheck()`.)

And the one TASK 5 asks you to defend: **how long should you wait between the
deploy finishing and the "after" snapshot?** BFD and OMP don't reconverge
instantly. Check too early and you report a regression that isn't real — and a
pipeline that cries wolf is a pipeline people switch off.
