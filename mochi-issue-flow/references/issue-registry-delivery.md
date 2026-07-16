# Carrier, registry, and agent delivery

The issue-like carrier and its canonical status comment are authoritative. A registry is a cache. `synchronized` is valid only when `registry.lastSyncedStatusRevision` equals the canonical `statusRevision`. The adapter plans the target revision, uses `references/conditional-comment-edit.md` to check revision/hash and ownership, edits the existing comment, then rereads the exact saved revision/hash. Only a verified save may proceed to registry projection. If the projection step fails, it conditionally marks the card `out-of-sync` and retains the last successful revision. When project rules block the update, use `pending-user-approval` and record the blocked action.

`registry.requiredForDone: true` means the flow cannot become final `done` while registry status is pending, unless `registry.waiver.approved` is explicitly recorded. A false value lets registry work remain deferred without blocking acceptance.

Use `templates/delivery-packet.json` for agent-to-agent delivery, including Codex thread/session identity where available. A human-readable handoff may accompany it, but the packet is the stable machine contract. Adapters own carrier API calls; core validation and auditing consume offline JSON fixtures/snapshots so tests stay deterministic.

Status reads follow `references/status-read-adapter.md`: return one normalized canonical comment or one derived summary, never a transport envelope plus parsed duplicate. Project dashboards may consume that projection but remain caches.

When no canonical comment exists, bootstrap it once, capture its returned URL, and immediately backfill `canonicalStatusCommentUrl`. Later updates edit that one comment rather than appending competing current-state comments. A timeout or unknown edit result requires an exact reread; a matching target is `already-applied`, while any other state is rebuilt from the live authority.
