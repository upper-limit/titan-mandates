"""council.cli — reference implementation using OpenAI-compatible API.

Works with: OpenAI, Anthropic (via proxy), Google Gemini (via proxy),
Mistral, local LLMs via Ollama / LM Studio / vLLM, any OpenAI-compatible
provider.

Usage:
    python3 -m council.cli \\
        --prompt "Is this loan application within risk policy?" \\
        --models model-a,model-b,model-c

    echo "your question" | python3 -m council.cli --models model-a,model-b
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone

from . import CouncilResult, ModelVote


def _call_one_model(
    model: str, prompt: str, timeout: int, base_url: str, api_key: str
) -> ModelVote:
    """Call a single model via OpenAI-compatible chat completions API."""
    import urllib.request
    import urllib.error

    start = time.monotonic()
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a council member. Read the question, give a "
                    "concise verdict (one phrase), your confidence 0.0-1.0, "
                    "and a one-paragraph rationale. Respond ONLY in JSON: "
                    '{"verdict": "...", "confidence": 0.X, "reasoning": "..."}'
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 500,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        content = data["choices"][0]["message"]["content"].strip()
        # Try parse the JSON response; fall back to text if model didn't comply
        try:
            parsed = json.loads(content)
            verdict = str(parsed.get("verdict", "")).strip() or "unparseable"
            confidence = float(parsed.get("confidence", 0.5))
            reasoning = str(parsed.get("reasoning", "")).strip() or content
        except (json.JSONDecodeError, ValueError):
            verdict = "unparseable"
            confidence = 0.0
            reasoning = content
        latency_ms = int((time.monotonic() - start) * 1000)
        return ModelVote(model, verdict, confidence, reasoning, latency_ms)
    except (urllib.error.URLError, TimeoutError) as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        return ModelVote(model, "unavailable", 0.0, f"error: {e}", latency_ms)


def _compute_consensus(votes: list[ModelVote]) -> tuple[str, str | None, float]:
    """Aggregate verdicts. Returns (consensus_label, consensus_verdict, mean_conf)."""
    valid = [v for v in votes if v.verdict not in ("unavailable", "unparseable")]
    if not valid:
        return "no_consensus", None, 0.0
    verdicts = [v.verdict.lower() for v in valid]
    if len(set(verdicts)) == 1:
        mean_conf = sum(v.confidence for v in valid) / len(valid)
        return "agree", verdicts[0], mean_conf
    return "split", None, sum(v.confidence for v in valid) / len(valid)


def run_vote(
    prompt: str,
    models: list[str],
    timeout: int = 30,
    base_url: str | None = None,
    api_key: str | None = None,
) -> CouncilResult:
    """Reference implementation of council vote.

    Uses OpenAI-compatible API at OPENAI_BASE_URL (default: api.openai.com).
    Each model called concurrently. Aggregates into a CouncilResult.
    """
    base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY (or compatible) not set")
    start = datetime.now(timezone.utc)
    monotonic_start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as ex:
        votes = list(
            ex.map(lambda m: _call_one_model(m, prompt, timeout, base_url, api_key), models)
        )
    consensus_label, consensus_verdict, mean_conf = _compute_consensus(votes)
    duration_ms = int((time.monotonic() - monotonic_start) * 1000)
    return CouncilResult(
        prompt=prompt,
        models_called=models,
        votes=votes,
        consensus=consensus_label,
        consensus_verdict=consensus_verdict,
        aggregate_confidence=mean_conf,
        started_at=start,
        duration_ms=duration_ms,
        audit_record={
            "prompt": prompt,
            "models": models,
            "consensus": consensus_label,
            "verdict": consensus_verdict,
            "mean_confidence": mean_conf,
            "started_at": start.isoformat(),
            "duration_ms": duration_ms,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Council vote — multi-model consensus.")
    parser.add_argument("--prompt", help="Decision question (or pipe via stdin)")
    parser.add_argument(
        "--models",
        help="Comma-separated model IDs. Required unless COUNCIL_MODELS is set.",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Per-model timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args(argv)

    prompt = args.prompt or sys.stdin.read().strip()
    if not prompt:
        print("ERROR: provide --prompt or pipe via stdin", file=sys.stderr)
        return 2

    model_source = args.models or os.environ.get("COUNCIL_MODELS", "")
    if not model_source:
        print("ERROR: provide --models or set COUNCIL_MODELS", file=sys.stderr)
        return 2
    models = [m.strip() for m in model_source.split(",") if m.strip()]
    if not models:
        print("ERROR: no usable model IDs supplied", file=sys.stderr)
        return 2
    result = run_vote(prompt, models, timeout=args.timeout)

    if args.json:
        out = asdict(result)
        out["started_at"] = result.started_at.isoformat()
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"Prompt: {result.prompt}")
        print(f"Consensus: {result.consensus} ({result.aggregate_confidence:.2f} mean conf)")
        if result.consensus_verdict:
            print(f"Agreed verdict: {result.consensus_verdict}")
        print(f"Duration: {result.duration_ms}ms")
        print()
        for v in result.votes:
            print(f"[{v.model}] {v.verdict} ({v.confidence:.2f}, {v.latency_ms}ms)")
            print(f"  {v.reasoning[:200]}{'...' if len(v.reasoning) > 200 else ''}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
