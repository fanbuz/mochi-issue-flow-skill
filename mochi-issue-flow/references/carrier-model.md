# Issue-Like Carrier Model

An issue-like carrier is any durable object that can preserve workflow state across people, agents, tools, and time.

## Required Carrier Capabilities

| Capability | Purpose |
|---|---|
| Stable URL or ID | lets agents recover context |
| Editable body/description | stores current-state block |
| Comments/activity | stores evidence and handoff events |
| Links/backlinks | connects source, support, and tracking carriers |
| Labels/status/checklists | helps filtering and gate tracking |

## Authority Order

For L1 and L2:

1. Carrier body current-state block
2. Decisive comments linked from the current-state block
3. Labels/status/checklists
4. Registry/index cache
5. Local notes or dashboards

For L3:

1. Canonical Flow Card comment
2. A summary derived from that same card and bound to its revision/hash
3. Carrier body summary and decisive evidence links
4. Registry/index cache
5. Local notes or dashboards

If lower levels disagree with higher levels, mark the projection out-of-sync, update it, or stop and report the mismatch. A hand-written summary never outranks the canonical L3 card.

## Staleness

Every current-state block should include `last state update`. If that timestamp is older than the configured stale threshold, default 14 days, treat the linked carrier as stale.

Before resuming stale work:

1. Re-read the live carrier body, status, labels/checklists, and latest decisive comments.
2. Compare the live carrier with any registry/index cache.
3. Refresh the current-state block with a new `last state update`.
4. Continue only after stale state is resolved or explicitly reported.

## Recommended IDs

- `flowId`: stable topic slug, e.g. `billing-export-rework`
- `linkId`: `driver__support__topic`
- `contractId`: `CT-01`, `CT-02`
- `phase`: `P0`, `P1`, `P2`

Use generic, non-secret identifiers. Never encode credentials, customer names, private hostnames, or local filesystem paths in IDs.
