# Flow Card schema (protocol 3.0)

The Flow Card is JSON inside the canonical status comment sentinel block. `statusRevision` is a monotonically increasing integer used for optimistic ownership checks. The first posted card has `canonicalStatusCommentUrl: null`; the creator immediately edits the returned comment URL into that same card as revision 2.

| Field | Required | Meaning |
|---|---:|---|
| `protocolVersion` | yes | `3.0` |
| `flowId` | yes | Stable flow identifier |
| `statusRevision` | yes | Canonical-comment edit revision |
| `canonicalStatusCommentUrl` | yes after bootstrap | Pointer to the one current-state comment |
| `flowExecutionLease` | yes while active | Owner, thread/session IDs, heartbeat, expiry, transfer |
| `registry` | yes | Cache synchronization policy and waiver |
| `bridges` | yes | Work units, artifact sets, axes, and evidence |
| `dependencies` | yes | Directed acyclic Bridge dependencies |
| `flowCodeState` / `flowRuntimeState` | derived | Aggregate required-axis status |

Each Bridge's `relevantArtifactRepos` is its complete acceptance surface. Both `currentCommit.repos` and `acceptedCommit.repos` must contain exactly that set, and every entry has `branch` and immutable `sha`. A monorepo, deploy manifest, or configuration repository belongs in the set whenever it affects the Bridge's acceptance result.

`codeState` and `runtimeState` contain a `value`, `activeEvidence`, and `supersededEvidence`. `codeRequired` and `runtimeRequired` say whether their axes apply. A false required flag demands `not-applicable` plus `notApplicableReason`.

Use `scripts/validate_flow_card.py` for structural validation. It is deliberately carrier-neutral and performs no network access.
