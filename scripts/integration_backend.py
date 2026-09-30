"""Capture one-time credentials inside the disposable integration Backend container."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from alos.main import app

_CREDENTIALS = Path("/tmp/alos-integration-activation.jsonl")

if app.state.settings.APP_ENV != "development" or not app.state.settings.ENABLE_TEST_TOOLS:
    raise RuntimeError("Integration credential capture requires development test tools")


def _capture_credential(email: str, token: str) -> None:
    record = (json.dumps({"email": email, "token": token}) + "\n").encode()
    descriptor = os.open(_CREDENTIALS, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, record)
    finally:
        os.close(descriptor)


app.state.auth_service._activation_sink = _capture_credential


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Expected exactly one employee email")
    for line in reversed(_CREDENTIALS.read_text(encoding="utf-8").splitlines()):
        entry = json.loads(line)
        if entry["email"] == sys.argv[1]:
            sys.stdout.write(entry["token"])
            break
    else:
        raise SystemExit("Activation credential was not captured")
