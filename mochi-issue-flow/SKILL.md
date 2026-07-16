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

## Keep protocol chatter out of user updates

Treat Flow Card operations as internal bookkeeping, not user-visible milestones. Give a short plain-language progress update only when starting a meaningful phase, reaching an observable result, encountering a blocker or risk, needing a user decision, or completing the work. During long-running work, use a plain-language heartbeat when required, but describe the recognizable work rather than the bookkeeping underneath it.

Use this user-facing update contract:

1. **Outcome first:** say what business result will be checked or changed.
2. **Data impact:** say whether the step is read-only, may write, succeeded, failed, or rolled back.
3. **Stop/next point:** name the real blocker or the next action; when approval is needed, state exactly what the approved step will do.

Apply this visibility filter before sending commentary or the final answer:

- Suppress individual carrier reads, Flow Card writes, revision/hash checks, lease heartbeats, registry projection, evidence-format synchronization, and validation passes. Aggregate the whole internal sequence into one update after it produces a result the user can recognize.
- Do not repeat the same result merely because its evidence, cache, or carrier record was updated. Do not narrate files, commands, tool calls, or protocol state transitions unless the user asked for an execution trace.
- Keep identifiers and protocol labels such as `Flow Card`, `Bridge`, `canonical`, `revision`, `hash`, `lease`, `registry`, scenario IDs, and code/runtime axes in the carrier, evidence, or logs by default. Mention them only when the user requests protocol detail or when an integrity conflict changes the outcome or requires a decision; even then, explain the practical effect first.
- Keep each progress update to one or two complete sentences. The final answer summarizes outcomes, unresolved risks, and next actions, not the internal event chain.

The opening paragraph must stand on its own without protocol vocabulary. Do not replace a real result such as “the schedule transaction failed and later writes stopped” with “the flow is blocked.” Read `references/user-facing-messages.md` only when authoring or reviewing message examples; it is not part of the normal execution working set.

- Translate internal names into their user-visible meaning. For example, call a health probe “confirming the test environment is available”, a shared ID “the shared test data needed for this run”, and a seed or join request “starting a real business operation”.
- Do not lead a progress update with labels or shorthand such as `L3`, `Bridge`, `Flow Card`, `lease`, `S1`, `probe`, `sharedId`, `seed`, or `join`.
- Explain a technical term only when it affects the user's decision or when the user has asked for technical detail.
- Say “this step only checks status; it will not change data or start a real operation” when the action is read-only. Do not list low-level requests that will not be sent unless that distinction matters to the user.

For example, write:

> 我先确认测试环境是否已经准备好：相关服务能否正常响应、大家是否使用同一套测试配置，以及本次测试所需的共享测试数据是否齐全。这一步只读取状态，不会修改数据或启动实际业务操作。

Do not write a string of internal checks such as “三后端与模拟器健康、统一配置 probe、以及 S1 必需的 sharedId”。

After a multi-step recovery, do not write “lease recovered, revision 18 saved, canonical hash locked, code axis verified, runtime axis blocked.” Write “The previous result has been recovered and checked for consistency. The code change is accepted, but the integration environment still prevents completion; next I’ll work on that environment issue.”

## Load only what the route needs

Execute bundled scripts directly. Do not read their source during normal operation; load script source only after a script failure when implementation diagnosis is necessary, and record that escalation reason. Load one route-specific reference at a time instead of opening the whole reference set.

| Route | Minimal working set |
|---|---|
| Read-only status | Exact canonical comment, `scripts/flow_status.py` output, and `references/status-read-adapter.md`; stop when the revision/hash-bound summary answers the request |
| Conditional mutation | Full current card plus `references/conditional-comment-edit.md`; run routine audit, preflight the expected revision/hash, edit in place, then reread |
| Migration/archive | Full current card plus `references/evidence-archive-and-migration.md` |
| Closeout | Full current card and `scripts/audit_flow.py --mode closeout`; load a reference only to resolve a reported failure |
| Runtime diagnosis | Current compact summary plus the smallest decisive failure artifact; do not reload flow history or full cards unless mutation becomes necessary |

If exact sentinel parsing fails, stop and report its stable error code. Do not fall back to an arbitrary JSON fence. Load migration guidance only when the carrier actually needs an explicit compatibility migration. Use `scripts/check_context_budget.py` route-bundle checks to keep these working sets bounded.

## L3 Flow Card protocol

Keep one canonical current-state comment for each delivery mainline. Its JSON is delimited by `flow-card:start` and `flow-card:end`; `canonicalStatusCommentUrl` points to that comment and `statusRevision` increases on every successful edit. Bootstrap it with `templates/flow-card-comment.md` when the URL is unknown, then write the returned URL back into the same card. Replace duplicate former cards with `templates/flow-card-alias.md`; never leave two writable authorities.

For read-only status queries, fetch the exact canonical comment and generate the revision/hash-bound compact summary with `scripts/flow_status.py`. Do not expose raw and parsed transport copies or unrelated comment history to the model. Load the full card for mutation, migration, validation, archive, or audit. See `references/status-read-adapter.md`.

For every Bridge, list its entire `relevantArtifactRepos` set in both `currentCommit` and `acceptedCommit`. A commit set drift makes required code and runtime evidence `needs-reverify`; preserve prior proof in `supersededEvidence` rather than deleting it. Archive bulky superseded proof only through the verified two-phase flow in `references/evidence-archive-and-migration.md`. A Bridge is eligible for done only when every required axis is verified; explicitly justified `not-applicable` axes do not block it. Use the derived `flowCodeState` and `flowRuntimeState`, not coordination status alone, for flow acceptance.

Declare `concurrencyControl.mode`. Legacy cards default to `lease`; only the live lease holder may edit them. Explicit `revision-only` cards omit the lease and require an unchanged revision immediately before every write. Run routine audit before mutation and `scripts/audit_flow.py --mode closeout` before completion. Only closeout's `closeoutEligible` decides whether the flow may close. Carrier adapters perform network reads/writes outside this pure audit boundary.

Registries remain caches. `synchronized` is valid only when `registry.lastSyncedStatusRevision` matches the canonical revision. When project policy sets `registry.requiredForDone: true`, pending or stale registry work permits implementation but blocks final done unless a recorded waiver is approved.

## Templates and references

- `templates/flow-card-comment.md` — canonical L3 status comment
- `templates/flow-card-alias.md` — immutable pointer after single-card migration
- `templates/capability-issue.md`, `templates/migration-issue.md` — issue starters
- `templates/evidence-comment.md`, `templates/delivery-packet.json` — evidence and agent delivery
- `references/state-and-invalidation.md` — states and commit drift
- `references/lease-monitor-transfer.md` — ownership and stall handling
- `references/workspace-preflight.md` — branch, worktree, and materialization checks
- `references/issue-registry-delivery.md` — carrier, registry, and Codex-agent delivery
- `references/scenario-evidence-matrix.md` — S1–S4 acceptance matrix
- `references/status-read-adapter.md` — direct read and compact summary contract
- `references/conditional-comment-edit.md` — revision/hash-bound in-place edit and provider mapping
- `references/evidence-archive-and-migration.md` — two-phase archive and duplicate-card consolidation
- `references/context-budget.md` — deterministic character and optional token budgets
- `references/user-facing-messages.md` — bilingual examples for authoring/review, not normal execution

Public templates must stay carrier-neutral: do not include private repositories, paths, credentials, or internal URLs.
