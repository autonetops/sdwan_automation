# Module 3 — Config Groups and the asynchronous model (50 min)

This is where you write to the fabric for the first time.

## The mental map, coming from templates

| What you know | What it's called now |
|---|---|
| Feature template | **Parcel** (inside a feature profile) |
| Device template | **Config group** |
| Attach | **Associate** + **deploy** |
| Variable CSV | **Device variables** |

Config groups require Manager 20.12+ / IOS-XE 17.12+. Classic templates still
exist and are still the reality of most brownfield fabrics — `attachfeature` is
the deploy equivalent, and the asynchronous task model is **identical** in both.
What you learn here applies to both worlds.

## What we're learning

| Automation | SD-WAN |
|---|---|
| Dry-run before writing | Config group `preview` |
| The async model and polling | `parentTaskId` → `/device/action/status/{id}` |
| Idempotency | An associate that doesn't re-associate |
| GET → modify → PUT | Device variables |

## The lesson that matters

Writing to the Manager is **not synchronous**. The POST returns an `id` and
walks away:

```
POST /v1/config-group/{id}/device/deploy   →  {"parentTaskId": "abc-123"}
                                                       │
GET /device/action/status/abc-123  ← polling ──────────┘
```

A script that doesn't wait **lies**. It reports success when all that happened
was the Manager accepting the request — before the fabric changed, or before it
failed.

Waiting properly is four things: an interval between polls, a realistic
timeout, telling "finished well" from "finished badly", and returning enough
context for someone to debug at 3am.

## Preview: the `terraform plan` almost nobody uses

`preview_device_config()` returns the CLI that **would** be applied, without
applying it. It's free, it's safe, and it's the only honest answer to "what
exactly is going to change?". Use it every time.

## Get to work

```bash
export WS_STUDENT=07
python exercise.py --list      # find your config group
python exercise.py --preview   # look before you leap
python exercise.py --deploy    # do it, and wait for it
```

While the deployment runs, open the GUI under **Monitor → Tasks**. That's the
same task your code is polling. This is the moment the API stops being
abstract.

Check the polling without the lab:

```bash
python -m pytest ../tests/test_tasks.py -q
```

## Namespace

The lab is shared. Everything you create carries `ws<NN>-`. The code raises
`SystemExit` if `WS_STUDENT` isn't set — on purpose.

## When a payload returns 400

Don't guess. Open the browser Developer Tools, perform the same action by
clicking in the GUI, and compare the request body. The GUI uses exactly the
same API you do. **That's the technique, not a workaround.**
