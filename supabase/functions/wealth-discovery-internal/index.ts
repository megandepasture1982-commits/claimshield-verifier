/** Wealth OS discovery containment adapter v6.
 * No embedded credential and no paid provider calls. Native supervised research
 * is the active discovery path until a separately approved provider budget exists.
 */
declare const Deno: { env: { get(name: string): string | undefined }; serve(handler: (request: Request) => Promise<Response>): void };
type Env = (name: string) => string | undefined;
type Fetcher = typeof fetch;
const json = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
});
export function makeHandler(env: Env, send: Fetcher = fetch) {
  return async (request: Request): Promise<Response> => {
    if (request.method !== 'POST') return json({ error: 'method_not_allowed' }, 405);
    const token = request.headers.get('x-wos-discovery') ?? '';
    if (!/^[a-f0-9]{64}$/.test(token)) return json({ error: 'unauthorized' }, 401);
    const url = env('SUPABASE_URL');
    const service = env('SUPABASE_SERVICE_ROLE_KEY');
    if (!url || !service) return json({ error: 'server_configuration_missing' }, 503);
    const headers = { apikey: service, authorization: `Bearer ${service}`, 'content-type': 'application/json' };
    const db = (path: string, init: RequestInit = {}) => send(`${url}/rest/v1/${path}`, {
      ...init, headers: { ...headers, ...init.headers }, signal: AbortSignal.timeout(10000),
    });
    try {
      const auth = await db('rpc/wealth_validate_machine_token', { method: 'POST', body: JSON.stringify({ p_token: token }) });
      if (!auth.ok) return json({ error: 'authorization_verification_unavailable' }, 503);
      if ((await auth.json()) !== true) return json({ error: 'unauthorized' }, 401);
      const text = await request.text();
      if (text.length > 2048) return json({ error: 'request_too_large' }, 413);
      let input: { mode?: unknown } = {};
      try { input = text ? JSON.parse(text) : {}; } catch { return json({ error: 'invalid_json' }, 400); }
      if (!input || typeof input !== 'object' || Array.isArray(input)) return json({ error: 'invalid_request' }, 400);
      const mode = input.mode ?? 'readiness';
      if (mode !== 'readiness' && mode !== 'provider_search') return json({ error: 'unsupported_mode' }, 400);
      const response = await db('economic_universe?select=id,domain,origin,last_discovery_at&eligible_for_ranking=eq.true&order=last_discovery_at.asc.nullsfirst,id.asc&limit=25');
      if (!response.ok) return json({ error: 'candidate_read_failed', upstream_status: response.status }, 502);
      const candidates: unknown = await response.json();
      if (!Array.isArray(candidates)) return json({ error: 'invalid_candidate_response' }, 502);
      const receipt = {
        worker_version: 6, purpose: 'private_discovery_readiness', authorization_verified: true,
        selection_scope: 'at_most_25_eligible_candidates', candidate_count: candidates.length,
        searched_count: 0, evidence_added: 0, provider_requests: 0, amount_spent_usd: 0,
        provider_status: 'BLOCKED_EXPLICIT_SPEND_APPROVAL',
        active_research_path: 'native_scheduled_research_with_explicit_persistence',
        source_coverage: 'NOT_SEARCHED_BY_THIS_WORKER', phone_delivery: 'NOT_TESTED',
        full_discovery_claimed: false,
      };
      const now = new Date().toISOString();
      const saved = await db('intelligence_discovery_runs', {
        method: 'POST', headers: { Prefer: 'return=representation' }, body: JSON.stringify({
          status: mode === 'readiness' ? 'completed' : 'blocked', candidate_count: candidates.length,
          searched_count: 0, evidence_added: 0, started_at: now, completed_at: now,
          error_message: mode === 'provider_search' ? 'Paid API discovery needs explicit spend approval; no provider was called.' : null,
          receipt,
        }),
      });
      if (!saved.ok) return json({ error: 'receipt_persistence_failed', upstream_status: saved.status }, 502);
      const rows = await saved.json();
      if (!Array.isArray(rows) || !rows[0]?.id) return json({ error: 'receipt_identity_missing' }, 502);
      return json({ ok: mode === 'readiness', mode, run_id: rows[0].id, ...receipt }, mode === 'readiness' ? 200 : 409);
    } catch {
      return json({ error: 'dependency_unavailable', retry_safe: true, provider_requests: 0 }, 503);
    }
  };
}
if (typeof Deno !== 'undefined') Deno.serve(makeHandler((name) => Deno.env.get(name)));
