---
name: mochi-issue-flow
description: Use when work needs issue-driven coordination, linked issue creation, cross-repository handoff, multi-agent recovery, staged delivery gates, commit-aware multi-repo acceptance, or current-state synchronization through an issue-like carrier.
---

# Mochi Issue Flow

Coordinate work through a durable carrier such as an issue, ticket, task, or card. The carrier is authoritative; registries and local dashboards are caches.

## Route first

Read the carrier body, linked work, and latest decisive comments. Choose one route:

| Route | Use when | Create |
|---|---|---|
| L1 | One repository can finish the work | No linked carrier by default |
| L2 | One source needs one support owner | A linked pair and backlink |
| L3 | Multiple repositories, dependencies, gates, or acceptance sets | A tracking carrier and a Flow Card |
| Read-only | Review or design only | No state mutation |

Ask for confirmation before creating linked work, moving ownership, suspending, or closing a flow. Use `references/carrier-model.md` for L1/L2 and `references/flow-card-schema.md` for L3.

## L3 Flow Card protocol

Keep one canonical current-state comment on the tracking carrier. Its JSON is delimited by `flow-card:start` and `flow-card:end`; `canonicalStatusCommentUrl` points to that comment and `statusRevision` increases on every successful edit. Bootstrap it with `templates/flow-card-comment.md` when the URL is unknown, then write the returned URL back into the same card.

For every Bridge, list its entire `relevantArtifactRepos` set in both `currentCommit` and `acceptedCommit`. A commit set drift makes required code and runtime evidence `needs-reverify`; preserve prior proof in `supersededEvidence` rather than deleting it. A Bridge is eligible for done only when every required axis is verified; explicitly justified `not-applicable` axes do not block it. Use the derived `flowCodeState` and `flowRuntimeState`, not coordination status alone, for flow acceptance.

Only the live lease holder may edit the canonical status. Use `flowExecutionLease`, `threadId`/`sessionId`, `lastHeartbeatAt`, expiry, and an explicit transfer record. Audit before mutation and before closeout with `scripts/audit_flow.py`; it works from offline JSON snapshots only. Carrier adapters perform network reads/writes outside this pure audit boundary.

Registries remain caches. When project policy sets `registry.requiredForDone: true`, `pending-user-approval` permits implementation but blocks final done unless a recorded waiver is approved.

## Templates and references

- `templates/flow-card-comment.md` — canonical L3 status comment
- `templates/capability-issue.md`, `templates/migration-issue.md` — issue starters
- `templates/evidence-comment.md`, `templates/delivery-packet.json` — evidence and agent delivery
- `references/state-and-invalidation.md` — states and commit drift
- `references/lease-monitor-transfer.md` — ownership and stall handling
- `references/workspace-preflight.md` — branch, worktree, and materialization checks
- `references/issue-registry-delivery.md` — carrier, registry, and Codex-agent delivery
- `references/scenario-evidence-matrix.md` — S1–S4 acceptance matrix

Public templates must stay carrier-neutral: do not include private repositories, paths, credentials, or internal URLs.
