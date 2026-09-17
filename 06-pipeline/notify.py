#!/usr/bin/env python3
"""Stage 5 of the pipeline — notify.

The half of a pipeline everyone forgets. A deploy that succeeded and told
nobody is fine; a deploy that *failed* and told nobody is an outage with a
delay fuse on it. The question a notify stage answers is not "did it work"
— the pipeline already knows that — it is **who finds out, and how fast**.

    python notify.py success
    python notify.py failure
    python notify.py failure --text "rollback did not complete"

Configuration, as one protected CI/CD variable:

    SLACK_WEBHOOK_URL   an incoming-webhook URL for the channel you want

⚠️ NOT SET YET. Create the webhook in Slack, then add it under
   Settings → CI/CD → Variables as **masked** and **protected**. Until then
   this script exits 0 and says so — a missing webhook must never be the
   thing that fails a good deploy.

Why a file and not six lines of curl in the YAML: because the payload is
JSON, and building JSON by pasting strings into a shell heredoc breaks the
first time a commit message contains a quote. `json.dumps` does not.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

EMOJI = {"success": "✅", "failure": "🚨"}


def context() -> dict[str, str]:
    """What GitLab tells a job about itself.

    Defaults so the script is runnable on a laptop — you should be able to
    test your webhook without pushing a commit to find out it was wrong.
    """
    return {
        "project": os.getenv("CI_PROJECT_PATH", "local"),
        "branch": os.getenv("CI_COMMIT_REF_NAME", "local"),
        "sha": os.getenv("CI_COMMIT_SHORT_SHA", "-"),
        "title": os.getenv("CI_COMMIT_TITLE", "(run by hand)"),
        "author": os.getenv("GITLAB_USER_LOGIN", os.getenv("USER", "unknown")),
        "url": os.getenv("CI_PIPELINE_URL", ""),
    }


def build_payload(status: str, extra: str | None) -> dict:
    ctx = context()
    headline = (
        "SD-WAN fabric change deployed and verified"
        if status == "success"
        else "SD-WAN fabric pipeline FAILED"
    )

    lines = [
        f"{EMOJI[status]} *{headline}*",
        f"`{ctx['project']}` · `{ctx['branch']}` · `{ctx['sha']}`",
        f"{ctx['title']} — {ctx['author']}",
    ]
    if extra:
        lines.append(extra)
    if ctx["url"]:
        lines.append(f"<{ctx['url']}|Open the pipeline>")

    return {"text": "\n".join(lines)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Post the pipeline result to Slack")
    parser.add_argument("status", choices=["success", "failure"])
    parser.add_argument("--text", help="one extra line of context")
    args = parser.parse_args()

    webhook = os.getenv("SLACK_WEBHOOK_URL")
    payload = build_payload(args.status, args.text)

    if not webhook:
        # Exit 0, deliberately. A student with no Slack must still be able to
        # run the whole pipeline — and on a real deploy, "we could not reach
        # Slack" is not a reason to mark a good change as failed.
        print("SLACK_WEBHOOK_URL is not set — nothing sent. Message would have been:\n")
        print(payload["text"])
        return 0

    request = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(f"Posted to Slack (HTTP {response.status}).")
    except urllib.error.URLError as exc:
        # Same argument: report it, do not fail the pipeline over it.
        print(f"Could not reach Slack: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
