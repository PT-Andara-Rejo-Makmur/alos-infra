# Governed ARA acceptance

Run the integration compose stack with its existing test environment, then:

```text
python scripts/integration-smoke.py
python scripts/ara-smoke.py
```

The first command covers canonical business/identity/material authority and runtime foundation regressions.
The second logs in through Web BFF cookies, creates a canonical Sales lead, reads it through ARA/GENESIS/ToolExecutor,
checks evidence, restored history, actor/workspace denial, browser authority rejection, material proposals, factory drafts,
Executive cross-domain research and one narrowed child. These fixtures exist only in the disposable development stack.

`scripts/verify-ara-roundtrip.py` additionally proves scoped memory, stale/current precedence and cancellation at an actual
owner source boundary, including cancellation of the single governed child, using Backend/GENESIS authenticated ASGI
transports and a migrated PostgreSQL database. Run it
with Backend's development virtual environment and ALOS_TEST_DATABASE_URL, with sibling repository checkouts present.

The topology keeps Web on edge only, PostgreSQL internal, and GENESIS off the data network with no DATABASE_URL or public port.
GENESIS calls business tools through authenticated Backend routes. Production providers remain disconnected.

ARA transport deadlines follow the Backend-owned run budget (30 seconds for the parent and 10 seconds for the child).
The orchestration deadline also covers research and advisory review. Source errors remain FAILED with explicit failed
source IDs; unknown values and unavailable sources never become fabricated zeros.
