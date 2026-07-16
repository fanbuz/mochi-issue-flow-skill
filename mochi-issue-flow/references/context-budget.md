# Context budget regression

Use normalized JSON character count as the mandatory, dependency-free metric. Use `o200k_base` tokens as an optional reference when a pinned `tiktoken` runtime is available; the report records the installed package version and returns `null` when it is unavailable.

| Artifact | Warning | Hard limit |
|---|---:|---:|
| Core `SKILL.md` instructions | 12,000 chars | 24,000 chars |
| Compact summary | 4,000 chars | 12,000 chars |
| Normalized adapter output | 12,000 chars | 24,000 chars |
| Active Flow Card | 12,000 chars | 24,000 chars |
| Core instructions + compact summary recovery bundle | 32,000 chars | 40,000 chars |

The token target for a single status read is at most 3,000. A normal L3 recovery path before business/code context should target 8,000–10,000 tokens. Character hard limits are CI gates; warning thresholds identify growth without failing the run.

```bash
python3 scripts/check_context_budget.py SKILL.md --kind instruction
python3 scripts/check_context_budget.py summary.json --kind summary
python3 scripts/check_context_budget.py adapter.json --kind adapter
python3 scripts/check_context_budget.py flow-card.json --kind card
python3 scripts/check_context_budget.py recovery-bundle.json --kind recovery
```

Small, medium, and large scenario definitions live in `tests/fixtures/context-budget-scenarios.json`. Public fixtures must stay anonymous and carrier-neutral. Do not reduce required artifact or acceptance evidence merely to pass a budget; archive historical detail and remove duplicate transport payloads instead.
