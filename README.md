# titan-mandates · CruxApex AI Governance Open Core

[![License: FSL-1.1](https://img.shields.io/badge/license-FSL--1.1-orange.svg)](LICENSE)
> Operational AI-governance primitives for enterprise agent fleets.
> Extracted from 6 months of live internal multi-agent operations.
> Not slideware. Working code.

---

## What this is

`titan-mandates` is the open-core layer of [CruxApex AI Governance](https://cruxapex.com). It packages five operational primitives that any team running AI agents in production can use today:

| Primitive | What it does | Status |
|---|---|---|
| **Mandate library** | Policy-as-code rules that govern agent behavior. This public package includes a starter mandate set drawn from the broader internal library. | Public starter set |
| **Council vote** | Multi-model consensus reference engine for high-risk AI decisions. Runs the same prompt against multiple LLMs and surfaces agreement vs disagreement. | Reference implementation |
| **Drift scorer** | Measures whether an agent's output style is drifting from a defined baseline. Catches model behavior changes before they reach users. | Reference implementation |
| **Audit chain** | Tamper-evident SQLite-WAL hash chain that records AI decision evidence and detects historical tampering. | Reference implementation |
| **PWCS** | Work-claim authorization framework. Every agent action requires a claim before executing — full accountability chain. | Public examples |

This is the **substrate**. The CruxApex commercial product wraps these with managed deployment, access controls, integrations, reporting workflows, support, and the operations cockpit. See [Open Core vs Commercial](#open-core-vs-commercial) below.

---

## Quickstart

```bash
git clone https://github.com/upper-limit/titan-mandates.git
cd titan-mandates
pip install -e .

# Run a council vote with any OpenAI-compatible endpoint
python3 -m council.cli \
  --prompt "Is this loan application within risk policy?" \
  --models claude,gpt,gemini

# Verify audit chain integrity with the smoke example
python3 examples/audit_chain_smoke.py

# Verify mandate YAML structure
python3 examples/verify_mandate_schemas.py
```

---

## Why this exists

Most AI governance tooling on the market today is one of three things:

1. **Compliance-checklist software** (Vanta-style) — proves your IT controls exist; can't see what your AI agents actually did at 2pm on Tuesday or why.
2. **Model-monitoring platforms** (Arize, Datadog) — track model performance metrics; don't enforce policy or create operational governance.
3. **GRC consultancies** (Deloitte, PwC) — manual work, $300/hour, 6-month engagements.

We built `titan-mandates` because we needed something different: **operational** governance code that can run alongside agent fleets, enforce policy at decision time, and produce evidence that security, risk, and compliance teams can inspect.

This is what's underneath. The commercial product is what's on top.

---

## The five primitives

### 1. Mandates (`mandates/`)

Each mandate is a YAML file describing a rule + when it applies + what to do if violated. Designed for compliance teams to read, lawyers to redline, and engineers to execute.

```yaml
# mandates/dual_channel_delivery.yaml
id: M30
name: Dual-channel delivery
applies_to: ["agent_outbound_critical"]
rule: |
  Any critical agent message to a human stakeholder must
  be delivered via at least two independent channels.
verification: |
  Check the message log: each `priority=critical` outbound
  should have entries in 2+ channel tables within 60 seconds.
violation_action: alert_owner_and_log
```

10 mandates ship in this release covering: dual-channel delivery, build-first-not-delete defaults, no-spend authorization gates, peer-flag duty, receipt-then-act on action messages, etc. The broader internal mandate library is packaged commercially with implementation support.

### 2. Council vote (`council/`)

Multi-model consensus engine. Same prompt to multiple LLMs simultaneously. Returns each model's verdict + reasoning + a synthesized aggregate.

```python
from council.cli import run_vote

result = run_vote(
    prompt="Should we approve this loan given context X?",
    models=["model-a", "model-b", "model-c"],
)

# result.consensus -> "agree" | "split" | "no_consensus"
# result.votes -> list of model verdicts, confidences, and reasoning
# result.audit_record → dict for the audit chain
```

Compliance value: EU AI Act Article 14 requires human oversight of high-risk AI decisions. A multi-model vote creates a documented, repeatable oversight step.

### 3. Drift scorer (`drift_scorer/`)

Continuously measures whether agent output style drifts from a defined baseline. Built originally to catch "AI accidentally adopts jargon the operator never uses" but generalizes to any output-style invariant.

```python
from drift_scorer import score

drift = score(
    baseline_corpus="path/to/operator_voice.txt",
    candidate_corpus="path/to/agent_recent_output.txt",
)

# drift.score → 0.0 (aligned) to ~1.0 (full drift)
# drift.breakdown → {vocabulary, sentence_length, jargon, contractions}
```

Threshold bands: under 0.25 = aligned, 0.25-0.40 = mild, 0.40-0.55 = drift detected, 0.55+ = high.

### 4. Audit chain (`audit_chain/`)

Tamper-evident SQLite-WAL hash chain for every AI decision. Each row is hashed with the prior row's hash; any modification breaks the chain.

```python
import hashlib
from audit_chain import write_audit_event, verify_chain

body = b"sample request"
write_audit_event(
    caller_orch="orch-1",
    pwcs_claim_uuid="abc-123",
    layer="L2",
    model="model-a",
    decision="allow",
    reason="policy_check_passed",
    request_hash=hashlib.sha256(body).digest(),
)

# Later, regulator asks for proof:
assert verify_chain() is True
```

The package includes a smoke example that writes events, verifies the chain, tampers with a row, and confirms tamper detection.

### 5. PWCS — Provisional Work Claim System (`pwcs/`)

*Coming in 0.2.0.* Authorization framework for agent actions. Each action requires a claim before executing; claims are ratified, executed, then closed with evidence. Creates full accountability chain.

---

## Open Core vs Commercial

`titan-mandates` (this repo) gives you:
- The five primitives as callable libraries
- 10 mandates from the broader 45-mandate library
- Documentation + examples + tests
- Run anywhere (laptop, your VPC, your container)
- Forever-free

[CruxApex Commercial](https://cruxapex.com) is the managed product path around this package:
- Hosted deployment and operations support
- Industry-specific mandate bundles
- Operations cockpit for agent status, review, usage, and audit evidence
- Integration planning for CRM, phone, ticketing, and workflow systems
- Compliance evidence workflows and implementation services

The pattern follows Supabase, PostHog, and Cal.com: open source is real and useful; commercial captures value from teams that prefer hosting + compliance + support to building all that themselves.

---

## License

[FSL 1.1](LICENSE) (Functional Source License, two-year transition to Apache 2.0).

The TL;DR: you can use this for almost any purpose including internal commercial use. The narrow restriction is on building a competing hosted-governance-platform service against CruxApex within the first two years. After two years, the code auto-converts to Apache 2.0 with no restrictions.

If you want a different license (Apache 2.0, MIT, commercial) email [brad@cruxapex.com](mailto:brad@cruxapex.com).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

Short version: PRs welcome on bug fixes, documentation, additional mandates, and improvements to the five primitives. We ask contributors to sign a DCO.

---

## Roadmap

- **0.1.0** (this release) — mandates + council + drift_scorer + audit_chain as separate packages
- **0.2.0** (Q3 2026) — PWCS public release; integration helpers (langgraph, crewai, openai-agents-sdk)
- **0.3.0** (Q4 2026) — policy bundle generator; bring-your-own-model adapters; auto-redaction helpers

---

## Production usage

This code is **not academic**. It was extracted from live internal agent operations and packaged as a public reference implementation. If your team is using it in production, [tell us](mailto:brad@cruxapex.com).

---

## Maintainers

Built and maintained by the CruxApex team.
