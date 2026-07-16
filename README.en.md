# Mochi Issue Flow

[中文](README.md) · [Install](#install) · [Quick start](#quick-start) · [Protocol 30](#l3-flow-card-protocol) · [Contributing](CONTRIBUTING.md)

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Protocol](https://img.shields.io/badge/protocol-3.0-7c3aed.svg)](mochi-issue-flow/references/flow-card-schema.md)
[![Skill](https://img.shields.io/badge/Agent%20Skill-carrier--neutral-0f766e.svg)](mochi-issue-flow/SKILL.md)
[![Tests](https://img.shields.io/badge/tests-offline%20fixtures-0ea5e9.svg)](mochi-issue-flow/tests)

Mochi Issue Flow is an open-source collaboration skill for AI agents. It turns issues, tickets, and task cards into durable workflow carriers that can be recovered, audited, handed off, and accepted. It handles both single-repository work and multi-repository work shared by several agents.

It is not a copy of any company-specific process or issue platform. GitHub Issues, Gitea, Linear, Jira, and any carrier that preserves a body, comments, links, and state can be adapted.

## What it solves

- A new agent can recover the next action without reconstructing chat history.
- Cross-repository work has traceable source, support, driver, acceptance owner, and next action instead of disconnected comments.
- Multi-repository completion is not mistaken for “one repository has a commit”: it requires a complete artifact commit set and independent code/runtime evidence.
- Retried or concurrent agents cannot casually overwrite current state: each card explicitly declares lease or revision-only concurrency control.
- The issue is authoritative and the registry/dashboard is a revision-bound cache; failed projection writes become explicit pending or out-of-sync state.
- Status queries can read a compact canonical-comment summary without loading complete comment history.
- Sentinels with or without attributes are parsed exactly; ambiguous input stops instead of falling back to arbitrary JSON.
- Canonical comment edits use revision/hash preconditions plus post-write rereads, with residual races declared when native CAS is unavailable.
- Read, mutation, migration, closeout, and diagnosis routes have bounded working sets; normal script execution does not load script source.
- User-facing progress keeps only recognizable results, actual impact, blockers, and next actions; internal revision, hash, lease, and registry transitions are not narrated one by one.

## Core model

| Route | Use when | Minimum artifact |
|---|---|---|
| L1 single carrier | One repository or owner can close the work | Current state, next action, acceptance evidence |
| L2 linked support | A source needs one support repository, team, or agent | Bidirectional link and delivery packet |
| L3 Flow Card | Multiple repositories, a dependency DAG, gates, concurrent agents, or formal acceptance | One canonical status comment in a tracking carrier |

Across all routes, **the carrier’s current state is authoritative; caches are projections.** L3 makes that state structured through a Flow Card.

## Install

Copy the complete `mochi-issue-flow/` directory into a runtime-discoverable skills directory. Do not copy only `SKILL.md`: templates, references, validators, and fixtures are one release unit.

```bash
cp -R mochi-issue-flow ~/.codex/skills/
cp -R mochi-issue-flow ~/.agents/skills/
cp -R mochi-issue-flow ~/.claude/skills/
```

If several agent runtimes share capabilities, install one version in `~/.agents/skills/` and maintain it through a sync or package process rather than hand-copying diverging versions.

## Quick start

### 1. Route before writing

```text
This work spans two repositories. Recover the current issue state first, then decide whether an L3 Flow Card is needed.
```

The skill reads carrier bodies, linked work, and recent decisive comments, then routes to L1, L2, L3, or read-only. Obtain user confirmation before creating linked work, moving ownership, suspending, or closing a flow.

### 2. L2: request support that can be accepted

```text
This issue needs support from the frontend repository. Create bidirectional links and a delivery packet that a support agent can use directly.
```

Use `templates/delivery-packet.json` to pass the target, authoritative carrier, expected evidence, complete artifact set, and idempotency key to another agent. A human-readable note may accompany it but does not replace it.

### 3. L3: create one Flow Card for multi-repository work

Create the comment from `templates/flow-card-comment.md` on the tracking issue. At first `canonicalStatusCommentUrl` is `null`; once the carrier returns the comment URL, **edit that same comment** to backfill it and increment `statusRevision`. Every later state update edits this one comment.

```bash
python3 mochi-issue-flow/scripts/validate_flow_card.py flow-card.json
python3 mochi-issue-flow/scripts/audit_flow.py flow-card.json
python3 mochi-issue-flow/scripts/audit_flow.py --mode closeout flow-card.json
```

The first command validates structure, the second performs routine audit, and the third returns explicit `closeoutEligible`. Errors or ineligible closeout exit with status `2`, which makes them usable as automation gates.

For an existing canonical comment, prepare revision/hash preconditions before the provider edit and verify the exact saved comment afterward:

```bash
python3 mochi-issue-flow/scripts/conditional_comment_edit.py prepare request.json live-snapshot.json --now 2026-07-16T10:00:00Z
python3 mochi-issue-flow/scripts/conditional_comment_edit.py verify request.json saved-snapshot.json
```

### 4. Filter internal task-chain chatter

Flow Card reads, conditional edits, revision/hash checks, lease heartbeats, registry synchronization, and repeated validations are internal execution records. By default, aggregate adjacent internal events into one understandable update that states the achieved result, data impact, concrete blocker, and next action. Show protocol fields or transitions only when the user asks for technical detail or when a concurrency conflict changes the outcome or decision.

For example, do not narrate “revision 18 saved, hash locked, code axis verified, runtime axis blocked.” Say: “The previous result has been recovered and checked for consistency. The code change is accepted, but the integration environment still prevents completion; next I’ll work on that environment issue.”

## L3 Flow Card protocol

A Flow Card is JSON in the authoritative comment, enclosed by HTML sentinels so people and scripts can read it together:

````md
<!-- flow-card:start v3 -->
```json
{ "protocolVersion": "3.0", "statusRevision": 7 }
```
<!-- flow-card:end -->
````

See the complete [schema](mochi-issue-flow/references/flow-card-schema.md) and [template](mochi-issue-flow/templates/flow-card-comment.md). The key constraints are:

| Concept | Constraint |
|---|---|
| One authority | `canonicalStatusCommentUrl` points to the only current-state comment; bootstrap and backfill it once. |
| Compact status read | A summary is derived from canonical JSON and bound to `sourceStatusRevision` plus its content hash. |
| Conditional revision | `statusRevision` increments on every successful edit; verify revision/hash and lease owner before writing, then reread the target revision/hash. |
| Bridge | Each cross-repository work unit has a stable `bridgeId`; a DAG records its dependencies. |
| Complete commit set | Both `currentCommit` and `acceptedCommit` cover all `relevantArtifactRepos` for the Bridge. |
| Dual-axis acceptance | `codeState` and `runtimeState` are verified independently; only required axes block completion. |
| Commit drift | On mismatch, active evidence moves to `supersededEvidence` and required axes become `needs-reverify`. |
| Historical archive | Write and verify an immutable archive before replacing bulky history with `archiveRefs`. |
| Concurrency protection | `lease` is the legacy V3 default; an explicit single-writer flow may use `revision-only`. |
| Registry | `synchronized` must bind the current `lastSyncedStatusRevision`; an approved waiver is the only closeout exception. |

A coordination state such as `ready-for-acceptance` never substitutes for `flowCodeState` and `flowRuntimeState`. Final completion requires closeout audit to confirm every required axis and synchronization gate.

Use `scripts/flow_status.py` for status reads, `scripts/conditional_comment_edit.py` for conditional edits, `scripts/archive_flow_evidence.py` for evidence archives, and `scripts/check_context_budget.py` for context budgets. A platform adapter filters to the canonical comment before model exposure and returns one normalized payload. Execute scripts directly during normal operation and load their source only when diagnosing a script failure.

## Token Cost and Optimizations

Mochi Issue Flow is designed to avoid loading complete issue history into the model. It compresses the authoritative current state into the smallest verifiable working set. A read-only status query should read the canonical comment and use `scripts/flow_status.py` to produce a compact summary bound to `sourceStatusRevision` and the content hash; the normal target is about 3,000 tokens or less. A routine L3 recovery should stay around 8,000 to 10,000 tokens before adding business code or repository context.

Main optimizations:

- Route first: choose Read-only, L1, L2, or L3 before loading route-specific references.
- Read precise carriers: adapters return only the canonical comment or target comment, not full comment history for the model to filter.
- Prefer scripts: status summaries, audits, conditional edits, archives, and budget checks execute directly; load script source only when diagnosing a script failure.
- Favor current state: Flow Cards keep active evidence and required gates while bulky older proof moves to archive references.
- Make budgets auditable: `scripts/check_context_budget.py` uses normalized JSON character count as the dependency-free hard metric; when `tiktoken` is installed, it also reports an `o200k_base` token estimate.

See [context budget](mochi-issue-flow/references/context-budget.md) for thresholds, fixtures, and CI policy.

## Use the correct workspace

Before cross-repository verification, record every relevant repository’s path, branch, worktree, and SHA. Use a direct branch only when it is clean, dedicated, and unowned by a concurrent agent; use a worktree for shared branches, isolation, or parallel work.

A new worktree does not automatically materialize Git-ignored local skills, configuration, or generated files. Treat the presence of every required file as a preflight gate. Missing material means verification cannot begin under a partial protocol. See [workspace preflight](mochi-issue-flow/references/workspace-preflight.md).

## Verification and tests

The core validator and auditor use only the Python standard library and read only offline JSON. Carrier APIs (GitHub, Gitea, Jira, and so on) belong to adapter layers, so core unit tests stay repeatable without a network or remote branches.

```bash
python3 -m unittest discover -s mochi-issue-flow/tests -p 'test_*.py' -v
```

When this command runs at the release repository root, it also checks the READMEs, license, version, and bytecode ignore rules. In an installed skills directory those repository-level checks are explicitly skipped, while Flow Card, template, and auditor core tests still run independently.

The [S1–S4 matrix](mochi-issue-flow/references/scenario-evidence-matrix.md) defines scenario evidence. Before closing an L3 Flow, use closeout mode to audit missing status, commit drift, registry revision, stalled leases, and every required axis.

## Repository layout

```text
mochi-issue-flow-skill/
├── LICENSE                         # Apache-2.0
├── NOTICE
├── README.md / README.en.md
├── CONTRIBUTING.md
├── VERSION
└── mochi-issue-flow/
    ├── SKILL.md                    # concise agent entry point
    ├── agents/openai.yaml
    ├── templates/                  # Flow Card, issue, evidence, delivery packet
    ├── references/                 # schema, states, leases, preflight, scenarios
    ├── scripts/                    # offline status, validation, audit, archive, and budgets
    └── tests/                      # repeatable fixture tests
```

## Security and privacy boundary

The public release contains generic protocol and templates only. Never add local paths, internal domains, private repositories, issue IDs, tokens, accounts, customer data, or business-sensitive data. Project-specific adapters, labels, repository mappings, and approval rules belong in private configuration or a project adapter layer.

## License

This project is licensed under the [Apache License 2.0](LICENSE) (SPDX: `Apache-2.0`). It permits commercial use, modification, and redistribution and provides an explicit contributor patent grant. Preserve the license, NOTICE, and required modification notices. The license does not grant trademark rights.

## Contributing

Issues and pull requests are welcome for protocol, template, and adapter-boundary improvements. Run the offline tests before submitting, keep `SKILL.md` concise, and ensure new material contains no private context. See [CONTRIBUTING.md](CONTRIBUTING.md).
