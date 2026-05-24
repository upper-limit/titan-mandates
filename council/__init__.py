"""council — multi-model consensus engine for high-risk AI decisions.

Routes a prompt through multiple independent language models simultaneously,
collects each model's verdict + reasoning, and surfaces consensus or
disagreement.

Compliance value: EU AI Act Article 14 requires human oversight of
high-risk AI decisions. A multi-model vote creates a documented,
repeatable oversight step with a full audit trail of every model's
input.

Public API:
    vote(prompt, models=None, budget="medium") -> CouncilResult

Example:
    from council.cli import run_vote

    result = run_vote(
        prompt="Should we approve this loan given context X?",
        models=["model-a", "model-b", "model-c"],
    )
    print(result.consensus)   # "agree" | "split" | "no_consensus"
    print(result.votes)       # list of (model, verdict, confidence, reasoning)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


__version__ = "0.1.0"
__all__ = ["vote", "CouncilResult", "ModelVote"]


@dataclass
class ModelVote:
    """One model's response in a council vote."""

    model: str
    verdict: str  # plain-language verdict, model-defined
    confidence: float  # 0.0 to 1.0
    reasoning: str  # model's explanation
    latency_ms: int


@dataclass
class CouncilResult:
    """Aggregated result across all models in a council vote."""

    prompt: str
    models_called: list[str]
    votes: list[ModelVote]
    consensus: str  # "agree" | "split" | "no_consensus"
    consensus_verdict: Optional[str]  # if consensus="agree", the agreed verdict
    aggregate_confidence: float  # mean confidence across voters
    started_at: datetime
    duration_ms: int
    audit_record: dict = field(default_factory=dict)


def vote(
    prompt: str,
    models: Optional[list[str]] = None,
    budget: str = "medium",
    timeout_seconds: int = 30,
) -> CouncilResult:
    """Run a council vote.

    Args:
        prompt: The decision question to put to the council.
        models: List of model identifiers. If None, defaults are picked
            based on `budget` by the production implementation.
        budget: "high" | "medium" | "low". Controls which model tier is
            selected when `models` is not specified.
        timeout_seconds: Per-model timeout. Slower models that exceed
            this contribute an unavailable vote (not a no-vote).

    Returns:
        CouncilResult with each model's vote, the consensus, and an
        audit_record suitable for write_audit_event().

    Raises:
        CouncilConfigError: if no models configured or budget invalid.
        CouncilNoResponseError: if all models fail to respond.
    """
    # This is the public API definition. Implementation in the commercial
    # product wraps actual provider SDKs (Anthropic, OpenAI, Google, etc.)
    # with retry, rate-limit handling, and cost accounting.
    #
    # For OSS users: this docstring + signature is the contract.
    # See `council/cli.py` for a working reference implementation that
    # uses the OpenAI-compatible API (works with most providers including
    # local LLMs via Ollama / LM Studio / vLLM).
    raise NotImplementedError(
        "OSS reference implementation in council.cli.run_vote(). "
        "For production-grade implementation with retry + rate-limit + "
        "cost accounting + audit-chain integration, see CruxApex commercial."
    )


class CouncilConfigError(Exception):
    """Raised when council configuration is invalid."""


class CouncilNoResponseError(Exception):
    """Raised when all models fail to respond within timeout."""
