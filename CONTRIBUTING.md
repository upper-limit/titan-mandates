# Contributing to titan-mandates

Thanks for considering a contribution. Here's how to make it land cleanly.

## What we welcome

- Bug fixes with reproduction steps
- New mandate YAML files (especially industry-specific ones)
- Integration helpers for popular agent frameworks (LangGraph, CrewAI, OpenAI Agents SDK)
- Documentation improvements + clearer examples
- Test coverage for the five primitives
- Performance improvements with before/after measurements

## What we don't merge

- Changes that break the audit-chain hash format (it's a forward-compatibility commitment to existing users)
- Changes that add cloud-vendor lock-in (the whole point is multi-cloud and on-premise)
- New runtime dependencies without a strong rationale
- Mandate YAML files that are vague — every mandate must have `applies_to` + `rule` + `verification` + `violation_action`

## Process

1. Open an issue first if it's a non-trivial change. Saves both of us time.
2. Fork + branch off `main`. Branch name: `fix/short-description` or `feat/short-description` or `mandate/M-id-short-name`.
3. Write tests if you're changing behavior. Run `pytest` locally.
4. Run `ruff check . && ruff format --check .` and fix any issues.
5. Open a PR with: what changed, why, how to test.
6. Sign the [DCO](https://developercertificate.org/) on each commit (`git commit -s`).

## DCO

Every commit must be signed off (`git commit -s`). This adds a `Signed-off-by:` line indicating you certify the commit per the [Developer Certificate of Origin](https://developercertificate.org/).

We don't require CLAs.

## Mandate-file format

New mandate YAML files must follow this schema:

```yaml
id: M-<sequential-or-domain-prefix>
name: <short human-readable name>
version: 1.0
status: active | draft | deprecated
authors:
  - github: <handle>
domain: communications | governance | security | data | code | thermal | other
applies_to:
  - <agent-action-class-1>
  - <agent-action-class-2>
rule: |
  <natural-language description of the rule, 2-4 sentences>
verification: |
  <how a verifier programmatically determines whether the rule is being followed>
violation_action: alert_owner_and_log | block | escalate_to_human | refuse_and_log
references:
  - <URL or repo-relative path of supporting evidence>
example_compliant: |
  <a short scenario where the rule is followed>
example_violation: |
  <a short scenario where the rule is broken>
```

See `mandates/dual_channel_delivery.yaml` for a reference implementation.

## Code style

- Python 3.10+
- Type hints required on all public APIs
- Docstrings on all public functions in Google style
- Maximum line length: 100 chars (configured in ruff)

## Tests

- `pytest` for the test suite
- Each public API function needs at least one happy-path + one failure-mode test
- Use `pytest.fixture` to share setup between tests
- Audit chain tests: never modify the hash format without bumping major version

## Questions

- General questions → [GitHub Discussions](https://github.com/upper-limit/titan-mandates/discussions)
- Security issues → [brad@cruxapex.com](mailto:brad@cruxapex.com) (do NOT open public issues for security)
- Commercial inquiries → [brad@cruxapex.com](mailto:brad@cruxapex.com)
