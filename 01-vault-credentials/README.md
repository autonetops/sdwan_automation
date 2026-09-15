# Module 1 — Credentials out of the code (30 min)

## Why this is first

Every module today opens with the same line:

```python
creds = load_credentials()
```

You're going to write it. Not because secret management is glamorous, but
because it's the one decision you can't retrofit: a password that reached Git
is a password you have to rotate, and rotating a password eighteen people
copied is not a five-minute job.

> Today's `.env` is tomorrow's accidental commit.

## What we're learning

| Automation | Vault |
|---|---|
| One entry point for secrets | `load_credentials()` and nothing else |
| Validate at the boundary | A pydantic model, not a dict |
| Secrets don't print | A `__repr__` that masks the password |
| Fail with a message, not a traceback | `CredentialsError` with context |

## Your Vault login

Authentication is **userpass** — a personal login, not a shared token. You get
yours at the start of the bootcamp.

```bash
export VAULT_ADDR=https://vault.autonetops.com
export VAULT_USERNAME=ws07       # yours
export VAULT_PASSWORD=...        # yours
```

The Manager secret lives at `workshop/sdwan` with three keys: `url`,
`username`, `password`.

> [!WARNING]
> **The trap: KV v2 wraps the secret twice.** The API response envelope is
> `data`, and inside it the version wrapper is `data` again. What you want is
> at `secret["data"]["data"]`. Everyone hits this exactly once — today is your
> once.

```
secret
└── "data"            ← API response envelope
    ├── "metadata"    ← version, created_time, …
    └── "data"        ← YOUR SECRET
        ├── "url"
        ├── "username"
        └── "password"
```

## Get to work

```bash
cd 01-vault-credentials
python exercise.py
```

Six TODOs in `_from_vault()`, two in `ManagerCredentials`, one in
`load_credentials()`.

Validate the parts that don't need Vault to be up:

```bash
python -m pytest ../tests/test_vault.py -q
```

## Why no `.env` fallback

An earlier version of this toolkit fell back to `VMANAGE_URL` /
`VMANAGE_USERNAME` / `VMANAGE_PASSWORD` when Vault wasn't configured. It's
gone, deliberately.

A fallback is a door. A door that exists "only for CI" is a door somebody
eventually uses on a laptop, and then the credential is in a shell history, a
Dockerfile and a screenshot. One source of truth, or none.

## Proof you actually ran it

The instructor will ask: **what URL and username did Vault hand you?**

That answer isn't anywhere in this repository. Only Vault knows.

## If you get stuck

- `ModuleNotFoundError: hvac` → `pip install -e ".[dev]"` from the repo root.
- `CredentialsError: No credentials` → `VAULT_PASSWORD` isn't exported.
- `Vault login failed … permission denied` → wrong username or password.
- `KeyError: 'url'` on a secret you can see in the UI → you unwrapped once
  instead of twice. Back to TODO 2.4.
- `InvalidPath` → the mount or path is wrong. Defaults are `workshop` /
  `sdwan`; override with `VAULT_SDWAN_MOUNT` / `VAULT_SDWAN_PATH`.

## Afterwards

Copy your work into `sdwan_toolkit/vault.py` (or compare it with what's
already there — it's the same code, annotated). From module 2 onwards you just
call `load_credentials()` and stop thinking about it.

That's the whole point. Secret management you have to think about daily is
secret management people route around.
