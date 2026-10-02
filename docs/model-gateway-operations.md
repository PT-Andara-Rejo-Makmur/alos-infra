# External production model gateway operations

9Router is already deployed. These configurations install no router or provider SDK. Only GENESIS
receives its endpoint and runtime key; Web and Backend keep their existing internal boundaries.
Staging GENESIS has a separate egress network and cannot join the PostgreSQL data network.
Production GENESIS retains its private listener and has no business database configuration.

Staging and production GENESIS select DEFAULT_MODEL_ROUTE=nine_router. Their examples intentionally
leave NINE_ROUTER_API_KEY and all model aliases blank. Inject NINE_ROUTER_API_KEY through the runtime
environment/secret manager. Never commit the key, bake it into an image, or print resolved compose config
containing it. Set DEFAULT_MODEL_ROUTE=disabled to disable production inference. Local/integration stays
explicitly deterministic by default and needs no provider credentials.

Endpoint: `NINE_ROUTER_BASE_URL=http://103.93.135.49:20128/v1`. Timeout defaults to 10 seconds.
Change the URL to HTTPS/private transport through environment configuration when available; current
public HTTP transmits the bearer credential and authorized data without encryption.

Operator steps:

1. Supply `NINE_ROUTER_API_KEY=<ISI_SENDIRI>` to GENESIS's deployment environment.
2. Run `python scripts/model-provider-smoke.py` inside the GENESIS deployment environment. The script
   lives in genesis-ai. It prints discovery/readiness and safe completion telemetry, without the key.
3. If discovery has multiple candidates and no configured default, select an actual discovered ID using
   NINE_ROUTER_MODEL_DEFAULT or STANDARD/REASONING/FAST/CODING/CRITICAL overrides. No production IDs are
   assumed in the repository. A single discovered usable model needs no model alias configuration.
4. Verify the existing governance prerequisite: the current workspace must have one released ACTIVE
   ara.workspace-assistant definition with a production policy and finite budget, and a compatible
   released ara.business-reader for governed research delegation. Credentials do not activate drafts.
   If absent, use the existing canonical human review/release workflow; do not bypass it or use TEST.
5. In disposable/staging data, log in through Web and run Sales, Executive summary/research, Sales→Finance
   denial, material proposal, injection-as-data, invalid/admin tool rejection, source honesty, malformed
   model output, and outage scenarios. Check persisted messages/evidence and cancellation propagation.

The authority endpoint displays provider Terhubung only from GENESIS readiness. Service availability
also requires released agent authority. Missing key/model mapping, classification or budget rejection,
router failure, and invalid output fail closed. Production never falls back to deterministic answers.

Normal CI runs provider mocks and deterministic integration without secrets. The final integration
workflow records all five repository SHAs and runs a production router mock with real PostgreSQL through
the same application/runtime/tool boundaries. The fixture creates only disposable test release snapshots;
production application code never registers, approves, releases, or activates an agent automatically.

For implementation details, token/cost limitations, policy mapping, and error semantics, see
[GENESIS routing documentation](https://github.com/PT-Andara-Rejo-Makmur/genesis-ai/blob/development/docs/model-provider-routing.md).
No live acceptance is claimed until an operator supplies the key and all live scenarios pass.
