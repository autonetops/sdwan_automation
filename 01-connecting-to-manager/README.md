# Module 1 — Connecting to the Manager (45 min)

## What you already know

You log into the Manager GUI every day. What you may not have noticed is that
the login is a **Java EE session**, not a modern REST API. That explains
everything that follows.

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
export VAULT_TOKEN=hvs.xxxx
python exercise.py
```

Four TODOs in `authenticate()`, one in `list_devices()`, one in `main()`.

## Proof you actually ran it

The instructor will ask: **how many WAN Edges are `reachable` right now?**

That answer isn't anywhere in the repository. Only the fabric knows.

## If you get stuck

- `CredentialsError` → `VAULT_TOKEN` isn't exported, or it expired.
- `SSLError` → you're missing `session.verify = False` (the lab has a
  self-signed certificate).
- `KeyError: 'data'` → you fell into the HTTP 200 trap. Back to TODO 1.2.
- `403` on a POST → the `X-XSRF-TOKEN` is missing. Back to TODO 1.4.

## Afterwards

Open `sdwan_toolkit/client.py`. It's the same handshake you just wrote, plus
rate limiting, error handling and the `data` unwrapping. From module 2 onwards
you use it — but now you know what's inside.
