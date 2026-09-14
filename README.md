# ClaimShield GitHub Actions Verifier

This repository runs HHEM-2.1-Open and MiniCheck on GitHub's standard public-repository runner.

Security:
- No Supabase service-role key is stored in GitHub.
- The workflow requests a short-lived GitHub OIDC token.
- Supabase verifies the token signature, audience, repository owner, repository name, and public visibility.
- Only `megandepasture1982-commits/claimshield-verifier` is trusted.

Workflow:
1. Pull one UNKNOWN claim that already has candidate evidence.
2. Run HHEM-2.1-Open.
3. Run MiniCheck RoBERTa-large.
4. Push both scores back to Supabase.
5. ClaimShield accepts only when both accept, rejects only when both reject, and leaves disagreement UNKNOWN.

The workflow runs every 5 minutes and can also be started manually.
