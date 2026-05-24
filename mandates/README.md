# Mandate Library

Each mandate is a YAML file describing a behavioral rule for agents in production.

## What's in this directory

10 mandates ship in this open-core release:

| ID | Name | Domain |
|---|---|---|
| M12 | Prove completion (never claim done without positive evidence) | governance |
| M17 | Recon before build (mandatory pre-build checklist) | code |
| M18 | Receipt-then-act on operator action messages | communications |
| M27 | Never invent facts (find, create, or ask) | governance |
| M30 | Dual-channel delivery for critical outbound | communications |
| M32 | No ETA without mechanical commitment tracker | governance |
| M34 | Active software only (monitors must have action paths) | code |
| M35 | Full message verification (silent triple-check) | communications |
| M39 | Peer-flag duty (active teamwork on visible mistakes) | governance |
| M43 | Build-first problem-solving (never delete/clear/merge as default) | governance |
| M44 | Canonical state protection (never ruin spec without operator approval) | governance |
| M45 | Confirmation of receipt and start (full-loop follow-through) | governance |

The broader internal mandate library includes additional industry-specific patterns for healthcare, financial services, government contractors, EU AI Act preparation, SOC 2 evidence workflows, and pharma operations. The managed CruxApex product packages those patterns with implementation support.

## Schema

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for the full mandate-file schema. Short version:

```yaml
id: M-<id>
name: <human-readable name>
version: 1.0
status: active | draft | deprecated
domain: <domain>
applies_to: [<agent-action-class>, ...]
rule: |
  <2-4 sentence description>
verification: |
  <how a verifier programmatically determines compliance>
violation_action: alert_owner_and_log | block | escalate_to_human | refuse_and_log
references:
  - <URL or path to supporting evidence>
example_compliant: |
  <short scenario where rule is followed>
example_violation: |
  <short scenario where rule is broken>
```

## Using mandates programmatically

```python
import yaml
from pathlib import Path

mandates = {}
for path in Path(__file__).parent.glob("*.yaml"):
    with open(path) as f:
        m = yaml.safe_load(f)
        mandates[m["id"]] = m

# Check whether a given agent action is governed
def applies(mandate_id, action_class):
    return action_class in mandates[mandate_id]["applies_to"]

# Get the verification rule for runtime enforcement
def verification_rule(mandate_id):
    return mandates[mandate_id]["verification"]
```

A runtime-enforcement library is on the roadmap for 0.2.0. For now, the YAML files are read by the human compliance team and translated into enforcement code per-project.

## Contributing new mandates

PRs welcome on industry-specific mandates. See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for the file-format requirements and review process.
