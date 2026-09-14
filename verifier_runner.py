import json
import os
import time
import urllib.request

import torch
from transformers import AutoModelForSequenceClassification
from minicheck.minicheck import MiniCheck

SUPABASE_BASE = "https://fenabmfwqsiygajwxczu.supabase.co/functions/v1"
OIDC_TOKEN = os.environ["GITHUB_OIDC_TOKEN"]
HHEM_MODEL = "vectara/hallucination_evaluation_model"
MINICHECK_MODEL = "roberta-large"

def post(path, payload):
    req = urllib.request.Request(
        f"{SUPABASE_BASE}/{path}",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {OIDC_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())

def build_document(items):
    chunks = []
    for i, e in enumerate(items[:6], 1):
        title = e.get("title") or e.get("url") or "Unknown source"
        excerpt = (e.get("excerpt") or "")[:3500]
        chunks.append(f"Source {i}: {title}\n{excerpt}")
    return "\n\n".join(chunks)[:18000]

def main():
    payload = post("claimshield-verifier-pull", {})
    if payload.get("status") == "idle":
        print("No pending claim with evidence.")
        return
    if payload.get("status") != "ready":
        raise RuntimeError(payload)

    claim = payload["claim"]
    document = build_document(payload["evidence"])
    claim_text = claim["text"]

    started = time.time()
    hhem = AutoModelForSequenceClassification.from_pretrained(
        HHEM_MODEL,
        trust_remote_code=True,
    )
    hhem.eval()
    with torch.no_grad():
        hhem_score = float(hhem.predict([(document, claim_text)])[0].item())
    hhem_ms = int((time.time() - started) * 1000)
    del hhem

    started = time.time()
    minicheck = MiniCheck(
        model_name=MINICHECK_MODEL,
        cache_dir=os.environ.get("HF_HOME", ".cache/huggingface"),
    )
    pred_label, raw_prob, _, _ = minicheck.score(
        docs=[document],
        claims=[claim_text],
    )
    mini_score = float(raw_prob[0])
    mini_label = "supported" if int(pred_label[0]) == 1 else "unsupported"
    mini_ms = int((time.time() - started) * 1000)

    result = post(
        "claimshield-verifier-push",
        {
            "claim_id": claim["id"],
            "runner": "github-actions-oidc",
            "hhem": {
                "score": max(0.0, min(1.0, hhem_score)),
                "label": "supported" if hhem_score >= 0.5 else "unsupported",
                "model": HHEM_MODEL,
                "version": "2.1-open",
                "latency_ms": hhem_ms,
            },
            "minicheck": {
                "score": max(0.0, min(1.0, mini_score)),
                "label": mini_label,
                "model": f"minicheck:{MINICHECK_MODEL}",
                "version": "0.1.0",
                "latency_ms": mini_ms,
            },
        },
    )
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
