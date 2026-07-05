---
name: mochi-issue-flow
description: Use when work needs issue-driven workflow coordination, linked issue creation, cross-repository handoff, multi-agent task recovery, staged delivery gates, contract/state recovery, or status synchronization through an issue-like carrier such as Gitea, GitHub Issues, Linear, Jira, or a workflow ticket.
---

# Mochi Issue Flow

## Overview

Mochi Issue Flow is an issue-action workflow SOP for coordinating single-carrier work, linked-issue handoffs, and multi-carrier staged flows. Treat an "issue" as any durable workflow carrier that can hold current state, comments, links, and checklists. Users speak in work intent; agents translate that intent into issue actions, current-state cards, linked carriers, contracts, gates, and handoff prompts.

## S0 Routing

Always run S0 before acting:

1. Extract anchors: issue ID, comment URL, repository, carrier link, project name, error surface, requested action.
2. Read carrier body, linked carriers, registry/index if present, and latest decisive comments.
3. Apply the route table:

| Evidence | Route | Create |
|---|---|---|
| Current repository/task can finish alone | L1 single-carrier work | No linked issue unless requested |
| One source carrier needs one support carrier | L2 linked issue flow | One linked issue pair |
| Multiple repositories, linked lines, phase gates, or contracts | L3 staged issue flow | Tracking issue + first-phase links only |
| User asks for review/design only | Read-only/design route | No workflow state |
| Evidence conflicts or route is unclear | Hold | Ask one minimal routing question |

4. Present a user-facing card before writing state; require confirmation before linked creation, sync, suspend, or closeout.

## User-Friendly Output

Use business language first; put protocol details in a "Details" block only when useful.

Required cards: recognition, current state, confirmation, handoff package, and closeout. Keep protocol details out of the main reading path.

See `references/templates.md` for reusable cards and carrier blocks.

## L2 Linked Issue Flow

Use this when one carrier asks another repository/team/agent to support one topic.

Default flow:

1. Confirm source carrier, target repository/team, acceptance owner, support owner, goal, blocker, next action owner, and acceptance criteria.
2. Create support carrier with current state, source link, scope, expected output, and acceptance criteria.
3. Add a backlink to the source carrier.
4. Record the linked flow in the registry/index if used.
5. Generate a support-agent handoff package.

## L3 Staged Issue Flow

Use this when work needs multiple linked lines, phased delivery, or formal contracts. Do not create every downstream issue at kickoff.

Default flow:

1. Create a tracking carrier as the flow home.
2. Record participants, phases, contracts, active links, current phase, current owner, and next action.
3. Create only the first phase's necessary linked carriers.
4. Gate each phase before creating downstream links.
5. Close with delivery evidence, contract list, accepted linked work, and remaining risks.

Contract states are `draft -> agreed -> implemented -> verified`. Not agreed, no implementation. Contract changes update the tracking carrier first, then sync affected linked carriers.
Each phase needs `entryCriteria`, `exitCriteria`, and `rollback`. If exit criteria fail, do not open downstream work; at phase close, linked carriers must be terminal or explicitly suspended.

## State Authority

The issue-like carrier is the authority. Registries, local notes, dashboards, and visualizations are caches or projections.

Authority order:

1. Carrier body current-state block.
2. Decisive comments linked from that block.
3. Labels/status/checklists.
4. Registry/index cache.
5. Local notes or dashboards.

If lower levels disagree with higher levels, update the lower level or stop and report the mismatch. If a linked carrier's last state update is older than the configured stale threshold, default 14 days, verify the live carrier state and refresh its current-state block before resuming work.

## Comment Discipline

Classify every comment before writing it:

| Type | Write where |
|---|---|
| Process check | Current carrier only |
| Conclusion | Affected linked carriers |
| Collaboration request | Target carrier and source backlink |
| Flow event | Tracking carrier, with links from affected carriers |

Do not synchronize noisy intermediate debugging unless it changes state, owner, acceptance criteria, contract, gate result, or next action.

## Exceptions

Use `references/exceptions.md` for cache mismatch, missing cache, stale state, incompatible protocol version, failed gate, valid suspension, and L2-to-L3 escalation.

Suspending work requires a reason and recovery condition in the carrier. A suspended state without both fields is invalid.

## Optional Gitea Setup

The author commonly uses Gitea issues as the carrier and pairs this skill with `gitea-cli`. This is recommended, not required. Use any carrier that can preserve current state, links, comments, and checklists.

See `references/gitea-cli.md` for generic Gitea carrier notes.

## Validation

Before claiming a flow is ready, verify:

- the current-state card is understandable without protocol knowledge
- every next action has an owner
- every linked carrier has a backlink
- support and driver roles are explicit
- stale linked carriers were refreshed before resume
- contract and gate rules were enforced
- suspended work has a reason and recovery condition
- closeout is blocked until acceptance evidence exists
- reusable templates contain no private repositories, local paths, credentials, or internal URLs

For route pressure tests, see `references/testing.md`.
