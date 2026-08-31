"""Module 1 — annotated solution."""

import os
import sys

import requests
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sdwan_toolkit.vault import load_credentials  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def authenticate(base_url: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    session.verify = False

    # Step 1 — the session. Note the form encoding: this endpoint is a Java EE
    # inheritance (j_security_check comes from the Servlet spec), not a REST API.
    resp = session.post(
        f"{base_url}/j_security_check",
        data={"j_username": username, "j_password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    resp.raise_for_status()

    # The trap. 200 + HTML = a login failure disguised as success.
    if "<html" in resp.text[:512].lower():
        raise RuntimeError("Invalid username or password (the Manager returned the login page).")

    if "JSESSIONID" not in session.cookies:
        raise RuntimeError("Login did not return JSESSIONID.")

    # Step 2 — the anti-CSRF token. Required on POST/PUT/DELETE since 19.2.
    # It is harmless on GET, so we pin it to the session headers.
    token = session.get(f"{base_url}/dataservice/client/token", timeout=60)
    token.raise_for_status()
    session.headers.update({"X-XSRF-TOKEN": token.text.strip()})

    return session


def list_devices(session: requests.Session, base_url: str) -> list[dict]:
    resp = session.get(f"{base_url}/dataservice/device", timeout=60)
    resp.raise_for_status()
    # The Manager API's ever-present envelope.
    return resp.json()["data"]


def main() -> None:
    creds = load_credentials()
    print(f"Connecting to {creds.url} as {creds.username}…")

    session = authenticate(creds.url, creds.username, creds.password)
    devices = list_devices(session, creds.url)

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

    controllers = {"vmanage", "vsmart", "vbond"}
    edges = [d for d in devices if d.get("personality") not in controllers]
    edges_up = [e for e in edges if e.get("reachability") == "reachable"]

    print(f"\nTotal devices: {len(devices)}")
    print(f"WAN Edges: {len(edges)}  |  reachable: {len(edges_up)}")
    print(f"\n>>> TASK 3 ANSWER: {len(edges_up)} reachable WAN Edges")


if __name__ == "__main__":
    main()
