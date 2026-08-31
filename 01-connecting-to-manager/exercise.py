"""Module 1 — Connecting to the Manager (45 min)

You are going to write the handshake by hand, with plain `requests`. After
this the `sdwan_toolkit` does it for you forever — but only once you have felt
why it exists.

Run:    python exercise.py
Check:  python -m pytest ../tests/test_client.py -q
"""

import os
import sys

import requests
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sdwan_toolkit.vault import load_credentials  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ─────────────────────────────────────────────────────────────────────
# TASK 1 — Authenticate
#
# The Manager does not use bearer tokens. There are two steps:
#
#   1. POST {base_url}/j_security_check
#      form-encoded body: j_username / j_password
#      → returns the JSESSIONID cookie
#
#   2. GET {base_url}/dataservice/client/token
#      → returns, as plain text, the value for the X-XSRF-TOKEN header
#
# ⚠️ THE TRAP: a wrong password does NOT return 401. It returns HTTP 200 with
#    the login page HTML. If you don't check for this, you will debug a
#    KeyError for an hour when the right answer was "your password is wrong".
# ─────────────────────────────────────────────────────────────────────

def authenticate(base_url: str, username: str, password: str) -> requests.Session:
    """Return a requests.Session that is authenticated and ready to write."""
    session = requests.Session()
    session.verify = False  # lab with a self-signed certificate

    # TODO 1.1: POST to /j_security_check with the form data.
    #           Hint: data={"j_username": ..., "j_password": ...}

    # TODO 1.2: detect the trap. If "<html" shows up at the start of the
    #           response body, raise RuntimeError("invalid username or password").

    # TODO 1.3: confirm the JSESSIONID cookie landed in session.cookies.

    # TODO 1.4: fetch the token from /dataservice/client/token and put it in
    #           session.headers as "X-XSRF-TOKEN".

    return session


# ─────────────────────────────────────────────────────────────────────
# TASK 2 — List the fabric
#
# GET /dataservice/device returns {"header": {...}, "data": [...]}.
# What you want is always inside "data" — this envelope will follow you
# through the entire API.
# ─────────────────────────────────────────────────────────────────────

def list_devices(session: requests.Session, base_url: str) -> list[dict]:
    """Return the device list, already unwrapped from 'data'."""
    # TODO 2.1: perform the GET and return resp.json()["data"].
    return []


# ─────────────────────────────────────────────────────────────────────
# TASK 3 — Answer the instructor's question
#
# Run against the lab and note the answer. It only exists in the real fabric.
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    creds = load_credentials()
    print(f"Connecting to {creds.url} as {creds.username}…")

    session = authenticate(creds.url, creds.username, creds.password)
    devices = list_devices(session, creds.url)

    if not devices:
        print("No devices. Are the TODOs still open?")
        return

    print(f"\n{'HOSTNAME':<20} {'SYSTEM-IP':<16} {'TYPE':<10} {'SITE':<6} REACHABLE")
    print("-" * 68)
    for d in devices:
        print(
            f"{d.get('host-name', '?'):<20} "
            f"{d.get('system-ip', '?'):<16} "
            f"{d.get('personality', '?'):<10} "
            f"{str(d.get('site-id', '?')):<6} "
            f"{d.get('reachability', '?')}"
        )

    # TODO 3.1: how many WAN Edges (personality other than vmanage/vsmart/vbond)
    #           are 'reachable'? Note the number — that is your answer.
    edges = [
        d for d in devices
        if d.get("personality") not in ("vmanage", "vsmart", "vbond")
    ]
    print(f"\nTotal devices: {len(devices)}")
    print(f"WAN Edges: {len(edges)}")


if __name__ == "__main__":
    main()
