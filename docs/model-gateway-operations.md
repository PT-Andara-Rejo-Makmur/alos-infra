# External production model gateway operations

9Router is already deployed. These configurations install no router or provider SDK. Only GENESIS
receives its endpoint and runtime key; Web and Backend keep their existing internal boundaries.
Staging GENESIS has a separate egress network and cannot join the PostgreSQL data network.
Production GENESIS retains its private listener and has no business database configuration.

Staging and production GENESIS select DEFAULT_MODEL_ROUTE=nine_router. Their examples intentionally
leave NINE_ROUTER_API_KEY and all model aliases blank. Inject NINE_ROUTER_API_KEY through the runtime
environment/secret manager. Never commit the key, bake it into an image, or print resolved compose config
containing it. Set DEFAULT_MODEL_ROUTE=disabled to disable production inference. The local example
defaults to disabled inference with `ENABLE_TEST_TOOLS=false` and `ENABLE_TEST_RUNTIME=false`;
set the route and model credentials explicitly to use NORMAL mode. Integration tests enable TEST
explicitly and need no provider credentials. Never enable TEST as a fallback for a provider outage.

Configure `NINE_ROUTER_BASE_URL` with a verified HTTPS router endpoint. Staging/production reject plaintext HTTP when the model route is enabled; business context and API credentials must use TLS. The earlier public HTTP IP endpoint must receive a TLS front end before production use. Timeout defaults to 10 seconds.
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
`CONNECTED` proves model discovery, authentication and selection; it does not prove that inference
will succeed or that provider quota is available. The manual completion smoke is a separate check.
On 4 October 2026, the configured development profile completed a connectivity request and synthetic
conversation/source reads, then returned HTTP 503 with quota/exhaustion indications. The operator
deferred further live testing until quota or a replacement profile is available. No complete live
acceptance or production readiness is claimed.

Optional live roundtrip acceptance: run `scripts/verify-ara-roundtrip.py --live-provider` in Infra
with `ALOS_ALLOW_LIVE_PROVIDER_TESTS=1`, `ALOS_TEST_DATABASE_URL` pointing to a disposable database
whose name ends in `_audit`, and `ALOS_LIVE_PROVIDER_ENV_FILE` pointing to the approved configuration.
The script creates synthetic accounts, records and release fixtures only in that audit database.
It must never target an operational database. Its `--production-mock` mode exercises the NORMAL
path without external inference or provider credentials.
