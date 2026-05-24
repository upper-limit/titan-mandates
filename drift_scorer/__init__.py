"""drift_scorer — measure output-style drift from a baseline.

Built originally to catch "AI accidentally adopts jargon the operator never
uses." Generalizes to any output-style invariant: vocabulary overlap,
sentence-length consistency, jargon density, contraction usage.

Public API:
    score(baseline_corpus, candidate_corpus, window_hours=24) -> DriftResult

The score is a weighted composite of four measurements:
  0.40 * (1 - Jaccard-top-200)   vocabulary overlap gap
  0.20 * sentence-length-delta    normalized
  0.30 * jargon-density-delta     per 100 words, vs curated list
  0.10 * contraction-delta        normalized

Score ranges 0.0 (perfect match to baseline) to ~1.0 (full drift).

Threshold bands (see thresholds.yaml):
    < 0.25 → aligned
    0.25 - 0.40 → mild drift
    0.40 - 0.55 → drift detected
    > 0.55 → high drift
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


__version__ = "0.1.0"
__all__ = ["score", "DriftResult", "load_jargon_list"]


# Curated jargon list — words common in AI agent output but rare in plain
# operator English. Customize for your domain via load_jargon_list().
DEFAULT_JARGON = {
    "idempotent", "idempotency", "invariant", "invariants",
    "orchestrate", "orchestration", "atomic", "atomically",
    "refactor", "refactoring", "payload", "schema", "schemas",
    "canonical", "canonically", "semantic", "semantically",
    "heuristic", "heuristics", "bootstrap", "scaffold", "scaffolding",
    "instantiate", "instantiation", "latency", "throughput",
    "entrypoint", "affordance", "affordances", "observability",
    "telemetry", "deterministic", "topology", "primitives",
    "abstraction", "abstractions", "quiescent", "homogeneous",
    "heterogeneous", "dogfood", "dogfooding",
}


@dataclass
class DriftResult:
    """Result of drift measurement."""

    score: float  # 0.0 to ~1.0
    band: str  # "aligned" | "mild" | "drift_detected" | "high"
    breakdown: dict = field(default_factory=dict)
    baseline_word_count: int = 0
    candidate_word_count: int = 0


def load_jargon_list(path: str | Path | None = None) -> set[str]:
    """Load jargon word set from a newline-delimited file.

    If path is None, returns DEFAULT_JARGON.
    """
    if path is None:
        return set(DEFAULT_JARGON)
    text = Path(path).read_text()
    return {w.strip().lower() for w in text.splitlines() if w.strip() and not w.startswith("#")}


def _tokenize(text: str) -> list[str]:
    """Lowercase tokenization stripping punctuation."""
    return re.findall(r"[a-z']+", text.lower())


def _top_n_vocab(tokens: list[str], n: int = 200) -> set[str]:
    """Top-N most-frequent tokens as a set."""
    return {w for w, _ in Counter(tokens).most_common(n)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def _avg_sentence_length(text: str) -> float:
    """Mean tokens per sentence; rough but good enough for drift detection."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    return sum(len(_tokenize(s)) for s in sentences) / len(sentences)


def _jargon_density(tokens: list[str], jargon: set[str]) -> float:
    """Per-100-words jargon hit rate."""
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in jargon)
    return (hits / len(tokens)) * 100.0


def _contraction_rate(tokens: list[str]) -> float:
    """Fraction of tokens containing an apostrophe (don't, it's, etc.)."""
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if "'" in t) / len(tokens)


def score(
    baseline_corpus: str | Path,
    candidate_corpus: str | Path,
    jargon_path: str | Path | None = None,
) -> DriftResult:
    """Score how far candidate has drifted from baseline.

    Args:
        baseline_corpus: Path to baseline text file (operator's natural voice).
        candidate_corpus: Path to candidate text file (recent agent output).
        jargon_path: Optional path to custom jargon word list.

    Returns:
        DriftResult with score 0.0-1.0, band, and breakdown.
    """
    baseline_text = Path(baseline_corpus).read_text()
    candidate_text = Path(candidate_corpus).read_text()
    jargon = load_jargon_list(jargon_path)

    bl_tokens = _tokenize(baseline_text)
    cd_tokens = _tokenize(candidate_text)

    # Vocabulary overlap (top 200)
    vocab_jaccard = _jaccard(_top_n_vocab(bl_tokens, 200), _top_n_vocab(cd_tokens, 200))
    vocab_gap = 1.0 - vocab_jaccard

    # Sentence length delta (normalized by baseline)
    bl_sent_len = _avg_sentence_length(baseline_text)
    cd_sent_len = _avg_sentence_length(candidate_text)
    sent_delta = abs(cd_sent_len - bl_sent_len) / max(1.0, bl_sent_len)
    sent_delta = min(1.0, sent_delta)  # cap at 1

    # Jargon density delta
    bl_jargon = _jargon_density(bl_tokens, jargon)
    cd_jargon = _jargon_density(cd_tokens, jargon)
    jargon_delta = min(1.0, abs(cd_jargon - bl_jargon) / 5.0)  # 5% delta = max

    # Contraction rate delta
    bl_contr = _contraction_rate(bl_tokens)
    cd_contr = _contraction_rate(cd_tokens)
    contr_delta = min(1.0, abs(cd_contr - bl_contr) / 0.1)  # 10% delta = max

    final = (
        0.40 * vocab_gap
        + 0.20 * sent_delta
        + 0.30 * jargon_delta
        + 0.10 * contr_delta
    )

    if final < 0.25:
        band = "aligned"
    elif final < 0.40:
        band = "mild"
    elif final < 0.55:
        band = "drift_detected"
    else:
        band = "high"

    return DriftResult(
        score=round(final, 3),
        band=band,
        breakdown={
            "vocabulary_gap": round(vocab_gap, 3),
            "sentence_length_delta": round(sent_delta, 3),
            "jargon_density_delta": round(jargon_delta, 3),
            "contraction_delta": round(contr_delta, 3),
        },
        baseline_word_count=len(bl_tokens),
        candidate_word_count=len(cd_tokens),
    )
