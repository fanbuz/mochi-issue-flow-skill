# Carrier, registry, and agent delivery

The issue-like carrier and its canonical status comment are authoritative. A registry is a cache. When an adapter cannot update a registry due to project rules, set `registry.status` to `pending-user-approval`, record the blocked action, and continue only where policy permits.

`registry.requiredForDone: true` means the flow cannot become final `done` while registry status is pending, unless `registry.waiver.approved` is explicitly recorded. A false value lets registry work remain deferred without blocking acceptance.

Use `templates/delivery-packet.json` for agent-to-agent delivery, including Codex thread/session identity where available. A human-readable handoff may accompany it, but the packet is the stable machine contract. Adapters own carrier API calls; core validation and auditing consume offline JSON fixtures/snapshots so tests stay deterministic.

When no canonical comment exists, bootstrap it once, capture its returned URL, and immediately backfill `canonicalStatusCommentUrl`. Later updates edit that one comment rather than appending competing current-state comments.
