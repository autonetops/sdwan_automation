# Module 3 — From functions to a client (35 min)

## Module 2 works. So why change it?

This is the honest version of the question, and "because classes are better"
is not an answer. Look at what module 2 actually left you with:

```python
session = authenticate(creds.url, creds.username, creds.password)
devices = list_devices(session, creds.url)
peers   = list_bfd(session, creds.url, system_ip)     # and so on, forever
```

Four problems, none of them theoretical:

1. **Every function takes `session` and `base_url`.** Two arguments that are
   always the same, threaded through every call site in the codebase.
2. **Nothing logs out.** Manager sessions are a finite resource. Leaked
   sessions are the usual cause of "I can't log in any more" by mid-afternoon.
3. **No rate limiting.** The lab is shared, and `/device/*` is real-time.
4. **Every call repeats `raise_for_status()` and `["data"]`** — until the one
   place somebody forgets.

None of that is fixed by a new feature. It's fixed by **one object holding the
session and the base URL**, so the caller stops carrying them and the things
that must always happen happen whether anyone remembers or not.

```python
with SDWANClient.from_vault() as mgr:
    devices = mgr.get("/device")
```

## What we're learning

| Automation | SD-WAN |
|---|---|
| Encapsulating state instead of passing it | One session, one base URL |
| Context managers (`__enter__` / `__exit__`) | Guaranteed logout |
| A single choke point for cross-cutting concerns | Rate limiting, error context, unwrapping |
| Alternative constructors (`classmethod`) | `from_vault()` vs. a test's fake credentials |
| Specific exception types | `AuthenticationError` vs. every `RuntimeError` |

## You are refactoring, not retyping

`exercise.py` opens with your module 2 code, working. Read it once more with a
different question in mind: *what does every caller have to remember, and what
should the object remember instead?*

The `RateLimiter` is given — it's threading, not SD-WAN. Understand why it
exists, then leave it alone.

## Get to work

```bash
cd 03-building-the-client
python exercise.py
```

TODOs: two in `__init__`/`from_vault`, three in the lifecycle, seven in
`request()`/`_unwrap()`, four one-line verbs, two in `main()`.

The offline suite is the spec. Your class must do what this one does:

```bash
python -m pytest ../tests/test_client.py -q
```

Six behaviours, all of them things module 2 got wrong or didn't do:
cookie and token stored, the HTTP 200 trap caught, the envelope unwrapped, the
`/dataservice` prefix optional, HTTP errors carrying context, and an expired
XSRF token getting its own message.

## The one that matters later: `unwrap=False`

`request()` takes `unwrap` for a reason you'll hit in module 4. Most endpoints
answer `{"header": …, "data": […]}` and you only want `data`. But the task
status endpoint answers:

```json
{ "summary": { "status": "success" }, "data": [ … per-device rows … ] }
```

Unwrap that and you throw away `summary` — **the only place the task state
lives**. A default that's right 95% of the time still needs an escape hatch,
and building it now is cheaper than discovering it during a deployment.

## Why `from_vault()` is a classmethod

Because constructing an object and performing network I/O are different jobs.
`SDWANClient(credentials)` builds a client and touches nothing; `.login()`
talks to the Manager; `from_vault()` is the convenience that does all three.

That separation is what lets `tests/test_client.py` run on a plane with no
VPN. An `__init__` that logs in would make the class untestable, and
untestable code is code you only find out about in the lab.

## Proof you actually ran it

**Which software release is the lab Manager running?**

And a second one, for yourself: print `mgr.request("GET", "/device",
unwrap=False).keys()` and look at what the convenience threw away.

## If you get stuck

- `NotImplementedError` → that TODO is still open.
- `AttributeError: 'SDWANClient' has no attribute 'base_url'` → TODO 1.1.
- Tests pass but the lab hangs → you called `self.limiter.wait()` inside the
  retry path, or not at all. It belongs at the top of `request()`.
- Everything works but sessions pile up → `__exit__` isn't calling `logout()`.

## Afterwards

Compare your class with `sdwan_toolkit/client.py`. It's the same code — that
file is now *yours*, in the sense that you know every line in it.

From module 4 onward you import it and stop thinking about HTTP. The rest of
the toolkit — `inventory.py`, `state.py`, `tasks.py`, `configgroup.py` — is
already written on top of it, and every one of those modules is short
*because* this one exists.
