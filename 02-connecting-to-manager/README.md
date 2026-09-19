# Module 2 — Connecting to the Manager (30 min)

## What you already know

You log into the Manager GUI every day. What you may not have noticed is that
the login is a **Java EE session**, not a modern REST API. That explains
everything that follows.

You already have the credentials — module 1's `load_credentials()` is the
first line of this exercise. From here on, the password is somebody else's
problem.

## What we're learning

| Automation | SD-WAN |
|---|---|
| HTTP sessions and cookie jars | `j_security_check` and `JSESSIONID` |
| CSRF protection | `X-XSRF-TOKEN` (required since 19.2) |
| Secrets out of the code | Vault |
| Fail loudly, early, with context | The HTTP 200 trap |

## The handshake

```
1.  POST /j_security_check              →  JSESSIONID cookie
    body: j_username=…&j_password=…        (form-encoded, not JSON)

2.  GET  /dataservice/client/token      →  the X-XSRF-TOKEN value
                                            (plain text, no envelope)
```

> [!WARNING]
> **The trap that catches everyone.** A wrong password does not return `401`.
> It returns **`200 OK` with the login page HTML**. If your code doesn't test
> for that, you'll spend an hour debugging a `KeyError: 'data'` when the right
> answer was "your password is wrong".

## Get to work

```bash
export VAULT_USERNAME=ws07 VAULT_PASSWORD=...   # from module 1
cd 02-connecting-to-manager
python exercise.py
```

Four TASKs in `authenticate()`, one in `list_devices()`, one in `main()`.

Write it with plain `requests` and plain functions. Deliberately: you need to
feel the session, the cookie and the token as separate things before you wrap
them in anything.

## Proof you actually ran it

The instructor will ask: **how many WAN Edges are `reachable` right now?**

That answer isn't anywhere in the repository. Only the fabric knows.

## If you get stuck

- `CredentialsError` → `VAULT_USERNAME` / `VAULT_PASSWORD` aren't exported.
  Back to module 1.
- `SSLError` → you're missing `session.verify = False` (the lab has a
  self-signed certificate).
- `KeyError: 'data'` → you fell into the HTTP 200 trap. Back to TASK 1.2.
- `403` on a POST → the `X-XSRF-TOKEN` is missing. Back to TASK 1.4.

## Afterwards

Keep this file. You don't throw it away — **module 3 refactors it.** Those two
functions become a class that logs in once, spaces its calls, unwraps the
envelope and logs out on the way past, and that class is what the rest of the
bootcamp runs on.

Working code first, abstraction second. That order matters: an abstraction
written before you've felt the problem is just a guess with indentation.
