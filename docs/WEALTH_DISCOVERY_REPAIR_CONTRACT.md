# Wealth OS discovery repair contract — 2026-09-20

## Current baseline and scope
The accompanying `supabase/functions/wealth-discovery-internal/index.ts` is the verified deployed v6 readiness/containment adapter, copied without environment secrets. Preserve its authentication boundary and default readiness behavior. This PR is NOT deployed. Do not alter ClaimShield's existing runner or workflow.

The original v5 crashed on an undeclared `j`, had a hardcoded fallback credential and classified government-domain search snippets as funded procurement. Those defects must not recur. V6 safely provides readiness only. The new task is to add a bounded, genuinely free search path without restoring either weak authentication or paid fallback.

## Verified free-provider mechanism
Official Tavily documentation checked September 20, 2026:
https://docs.tavily.com/documentation/keyless
- POST `https://api.tavily.com/search`
- Headers: `Content-Type: application/json`, `X-Tavily-Access-Mode: keyless`
- Do NOT include an Authorization header or API key. If both are present the account key takes precedence.
- Keyless access is free and rate-limited; rate limiting must stop or produce a partial/failure receipt. Never silently fall back to a keyed provider.
- Success uses standard Tavily response schema.

A real keyless test from the connected database returned HTTP 200 with two public results on September 20. One result was a contract award. Successful transport does not prove an active opportunity.

## Implement with Codex
1. Preserve default `readiness`. Add an explicit `keyless_search` mode; keep `provider_search` blocked because no positive spend is authorized.
2. Retain database RPC `wealth_validate_machine_token(p_token text)` validation before private reads, writes or search. No hardcoded token or secret fallback; fail closed on RPC errors, malformed success payload or timeout. Never return or log credentials.
3. Use the existing REST adapter/dependency injection so tests can run offline. Add pure helpers as needed; no new service, database migration or paid API.
4. Bound to at most three public-safe query templates per run, one each for current buyer/job intent, Nebraska procurement break-in, and local public auction/acquisition discovery. Support selecting a single lane for a smoke test. Do not send private archive texts, user profiles or raw intelligence records to the provider. Keep candidate counts, query counts and source-result counts distinct. Query templates must not imply that a result is current, accessible or valuable merely because search returned it.
5. Request basic search, at most three results per query, no generated answer/raw-content fields, explicit timeouts, no automatic retries. Reject malformed response bodies. Report no-results, failed, rate-limited and partial cases distinctly. No-result coverage is only the checked query scope.
6. Persist returned public snippets only as UNVERIFIED `market_search_signal` records in existing public.demand_evidence. No automatic claim of funded procurement, actual transaction, buyer count, event independence, confidence, demand proof or economic action. Do not change existing ranking or lifecycle fields. Unlinked research observations are acceptable; do not fabricate universe IDs.
7. Use deterministic observation UUIDs based on normalized source URL and content (not an invented buyer event key), and conflict-ignore inserts so repeated identical observations do not duplicate. Materially changed snippets may be preserved as new unverified observations. Query strings/fragments used only for tracking can be stripped conservatively; do not collapse different listing IDs. Do not overwrite any preexisting verified record on retry.
8. Persist a run receipt in intelligence_discovery_runs, including mode, version, start/end, exact query coverage, actual result counts, persisted observation IDs, duplicate count, provider calls, failures and zero provider spend. Return the saved run ID only after successful persistence and validate the REST representation. A persistence failure must not look like success. Do not pretend phone delivery was tested by this worker.
9. Keep failed and unsearched queries explicit. Do not report all-source coverage or global opportunity optimality. Avoid blanket catch blocks that erase the failing stage; error details must be useful but must not echo tokens or private bodies.
10. Add no-network tests and a dedicated PR workflow with pinned actions, no repository secrets and no production or provider calls. Keep the existing workflow unchanged.

## Current database fields (use as documented; no schema guessing)
`demand_evidence`: id uuid default gen_random_uuid(); opportunity_id uuid nullable; intelligence_record_id uuid nullable; economic_universe_id uuid nullable; buyer_problem text; buyer_type text; observable_behavior text; evidence_class text; actual_transaction bool; posted_budget_low/high numeric; buyer_count int nullable; frequency_signal text; channel text; source_url text; observed_at timestamptz; confidence int nullable; freshness_status text; contrary bool; created_at timestamptz; independent_event_key text nullable; verification_status text default UNVERIFIED; verification_ref text nullable; notice_type text nullable; source_valid_until timestamptz nullable. id is a primary key. There is no evidence that URLs alone identify independent buyers. Leave missing fields null.
`intelligence_discovery_runs`: id uuid; status text; candidate_count int; searched_count int; evidence_added int; started_at/completed_at/created_at timestamptz; error_message text; receipt jsonb. No restrictive status check was found. Existing default values may be used.
The service key remains server-side in SUPABASE_SERVICE_ROLE_KEY; the browser never receives it. V6 uses native fetch rather than installing a Supabase SDK.

## Required regression cases
Anonymous request; former fallback token; wrong 64-hex token; RPC 500/timeout/nonboolean response; wrong HTTP method; invalid JSON; oversized request; unsupported mode; unchanged readiness with zero provider requests; paid mode remains blocked; keyless headers contain no key or Authorization even when env has TAVILY_API_KEY; valid results; valid zero results; provider 429; timeout; partial one-lane failure; malformed response; duplicate retry; changed observation content; receipt insert failure; malicious provider instructions stay inert data; government award/RFI snippets remain unverified nontransactions; no privacy-sensitive archive reads during keyless mode.

## Delivery boundary
Commit tested changes only to this branch and report tests and remaining uncertainties. Do NOT merge, deploy, access live private data, change account settings, spend, publish, contact buyers or enable keyed fallback. The integrating assistant will re-read the deployed version immediately before any separately controlled deployment. A stale baseline must not overwrite newer live code.
