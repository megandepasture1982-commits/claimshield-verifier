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

MAX_EVIDENCE_ITEMS = 6
MAX_CHUNKS = 12
CHUNK_CHARS = 900
CHUNK_OVERLAP = 120


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


def split_text(text, size=CHUNK_CHARS, overlap=CHUNK_OVERLAP):
    text = " ".join((text or "").split())
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks = []
    start = 0
    while start < len(text) and len(chunks) < MAX_CHUNKS:
        end = min(len(text), start + size)
        chunk = text[start:end]

        if end < len(text):
            boundary = max(chunk.rfind(". "), chunk.rfind("; "), chunk.rfind(", "))
            if boundary >= int(size * 0.60):
                end = start + boundary + 1
                chunk = text[start:end]

        chunks.append(chunk.strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)

    return [c for c in chunks if c]


def build_chunks(items):
    chunks = []
    for i, evidence in enumerate(items[:MAX_EVIDENCE_ITEMS], 1):
        title = evidence.get("title") or evidence.get("url") or "Unknown source"
        excerpt = evidence.get("excerpt") or ""
        source_text = f"Source {i}: {title}\n{excerpt}"

        for chunk in split_text(source_text):
            chunks.append(chunk)
            if len(chunks) >= MAX_CHUNKS:
                return chunks

    return chunks


def main():
    payload = post("claimshield-verifier-pull", {})
    if payload.get("status") == "idle":
        print("No pending claim with evidence.")
        return
    if payload.get("status") != "ready":
        raise RuntimeError(payload)

    claim = payload["claim"]
    evidence = payload.get("evidence") or []
    claim_text = claim["text"]
    chunks = build_chunks(evidence)

    if not chunks:
        raise RuntimeError("No usable evidence chunks returned for claim.")

    print(
        json.dumps(
            {
                "claim_id": claim["id"],
                "evidence_items": len(evidence),
                "verification_chunks": len(chunks),
                "max_chunk_chars": max(len(c) for c in chunks),
            }
        )
    )

    # HHEM: score each bounded chunk separately so the custom model never
    # receives the prior multi-source 1,000+ token document.
    started = time.time()
    hhem = AutoModelForSequenceClassification.from_pretrained(
        HHEM_MODEL,
        trust_remote_code=True,
    )
    hhem.eval()

    hhem_scores = []
    with torch.no_grad():
        for chunk in chunks:
            score = float(hhem.predict([(chunk, claim_text)])[0].item())
            hhem_scores.append(max(0.0, min(1.0, score)))

    hhem_score = max(hhem_scores)
    hhem_ms = int((time.time() - started) * 1000)
    del hhem

    # MiniCheck: evaluate the same evidence windows, then use the strongest
    # support probability. This preserves evidence coverage without feeding
    # one oversized document into either verifier.
    started = time.time()
    minicheck = MiniCheck(
        model_name=MINICHECK_MODEL,
        cache_dir=os.environ.get("HF_HOME", ".cache/huggingface"),
    )
    pred_label, raw_prob, _, _ = minicheck.score(
        docs=chunks,
        claims=[claim_text] * len(chunks),
    )

    mini_scores = [max(0.0, min(1.0, float(x))) for x in raw_prob]
    mini_score = max(mini_scores)
    mini_label = "supported" if mini_score >= 0.5 else "unsupported"
    mini_ms = int((time.time() - started) * 1000)

    result = post(
        "claimshield-verifier-push",
        {
            "claim_id": claim["id"],
            "runner": "github-actions-oidc",
            "hhem": {
                "score": hhem_score,
                "label": "supported" if hhem_score >= 0.5 else "unsupported",
                "model": HHEM_MODEL,
                "version": "2.1-open",
                "latency_ms": hhem_ms,
                "chunks_scored": len(hhem_scores),
            },
            "minicheck": {
                "score": mini_score,
                "label": mini_label,
                "model": f"minicheck:{MINICHECK_MODEL}",
                "version": "0.1.0",
                "latency_ms": mini_ms,
                "chunks_scored": len(mini_scores),
            },
        },
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
