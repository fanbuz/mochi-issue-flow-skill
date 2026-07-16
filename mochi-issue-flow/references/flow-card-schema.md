# Flow Card schema (protocol 3.0)

The Flow Card is JSON inside the canonical status comment sentinel block. Both `flow-card:start` and `flow-card:end` may carry optional attributes. If a delimiter declares `flowId`, it must match the JSON `flowId`; one comment must contain exactly one paired block. `statusRevision` is a monotonically increasing integer used for optimistic ownership checks. The first posted card has `canonicalStatusCommentUrl: null`; the creator immediately edits the returned comment URL into that same card as revision 2.

| Field | Required | Meaning |
|---|---:|---|
| `protocolVersion` | yes | `3.0` |
| `flowId` | yes | Stable flow identifier |
| `statusRevision` | yes | Canonical-comment edit revision |
| `canonicalStatusCommentUrl` | yes after bootstrap | Pointer to the one current-state comment |
| `concurrencyControl` | optional in legacy V3 | Explicit `lease` or `revision-only`; omitted legacy cards resolve to `lease` |
| `flowExecutionLease` | yes in `lease` mode | Owner, thread/session IDs, heartbeat, expiry, transfer |
| `registry` | yes | Cache synchronization policy, bound revision, and waiver |
| `bridges` | yes | Work units, artifact sets, axes, and evidence |
| `dependencies` | yes | Directed acyclic Bridge dependencies |
| `flowCodeState` / `flowRuntimeState` | derived | Aggregate required-axis status |

Each Bridge's `relevantArtifactRepos` is its complete acceptance surface. Both `currentCommit.repos` and `acceptedCommit.repos` must contain exactly that set, and every entry has `branch` and immutable `sha`. A monorepo, deploy manifest, or configuration repository belongs in the set whenever it affects the Bridge's acceptance result.

`codeState` and `runtimeState` contain a `value`, `activeEvidence`, `supersededEvidence`, and optional `archiveRefs`. An archive reference contains `url`, `contentHash`, `artifactSetIds`, `evidenceCount`, and `createdAt`. `codeRequired` and `runtimeRequired` say whether their axes apply. A false required flag demands `not-applicable` plus `notApplicableReason`.

`nextOwner` and `nextAction` are optional Bridge strings used by the compact status summary. The summary is generated from the card, includes `sourceStatusRevision` and `sourceCanonicalHash`, and is never a second authority.

One delivery mainline has one active Flow Card. After S4 migration, former cards are replaced by an immutable pointer based on `templates/flow-card-alias.md`; they must not retain a writable sentinel block.

`registry.status: synchronized` is trustworthy only when `registry.lastSyncedStatusRevision` equals the card's `statusRevision`. A failed projection update sets the registry status to `out-of-sync` and preserves the last successfully synchronized revision.

Use `scripts/validate_flow_card.py` for structural validation and `scripts/flow_status.py` for exact sentinel extraction. They are deliberately carrier-neutral and perform no network access.
