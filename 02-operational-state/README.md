# Module 2 — Operational state as data (50 min)

## The central idea of the bootcamp

> A change is only safe if you can **prove** the fabric came out the same or
> better.

Proving it requires a comparable snapshot, as data. Not a `show` command pasted
into the team chat.

## What we're learning

| Automation | SD-WAN |
|---|---|
| Normalize at the edge | Hyphenated keys and inconsistent fields |
| Model with dataclasses | `DeviceState`, `FabricSnapshot` |
| Serialize and version | Snapshot as JSON |
| A diff with an opinion | Losing BFD is a regression; gaining isn't |

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
client has a rate limiter — and why the lab is shared with the whole class.

## Get to work

```bash
python exercise.py --save snapshots/before.json
# … something changes (or you wait) …
python exercise.py --save snapshots/after.json
python exercise.py --compare snapshots/before.json snapshots/after.json
```

Check the judge's logic without touching the lab:

```bash
python -m pytest ../tests/test_diff.py -q
```

## The diff is asymmetric on purpose

Gaining a BFD session is good. Losing one is bad. A text `diff` doesn't know
that — yours does. That opinion is what lets the module 5 pipeline decide on
its own between moving forward and rolling back.

## Proof you actually ran it

**Which edge has the most BFD sessions `up`?**

## Something to think about

`compare()` only looks at the **difference**. A device that was already down
before and is still down after produces no finding at all. Is that correct, or
a defect?

(The answer lives in module 5's `precheck()`.)
