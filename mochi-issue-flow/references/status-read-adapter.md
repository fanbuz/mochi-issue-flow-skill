# Canonical status read adapter

## Read contract

1. Obtain `canonicalStatusCommentUrl` from the tracking carrier or registry pointer.
2. Read that exact comment when the carrier supports comment-by-ID.
3. Otherwise fetch comments inside the adapter and filter to the exact URL before any result enters model context.
4. Use one normalized internal payload:

```json
{
  "canonicalStatusCommentUrl": "https://carrier.example/issues/1#comment-2",
  "canonicalComment": {
    "url": "https://carrier.example/issues/1#comment-2",
    "updatedAt": "2026-07-16T10:00:00Z",
    "body": "<!-- flow-card:start v3 -->...<!-- flow-card:end -->"
  }
}
```

Do not expose raw and parsed copies, transport `content` plus `structuredContent`, or unrelated comments. Treat zero or multiple URL matches as an error.

The exact parser accepts optional attributes on both delimiters, including legacy or generated forms such as:

```text
<!-- flow-card:start flowId=flow-example protocol=3.0 -->
<!-- flow-card:end flowId=flow-example -->
```

If either delimiter declares `flowId`, it must match the canonical JSON. Unpaired, duplicate, malformed, or mismatched delimiters return stable `flow-card-*` errors. Stop on those errors. Never recover a normal status read by extracting an arbitrary fenced JSON object; use an explicit compatibility migration when the carrier is malformed.

## Compact summary

For a read-only status query, run `scripts/flow_status.py` inside the adapter/tool boundary and return only its summary to the model. The deterministic summary contains:

- `sourceStatusRevision` and `sourceCanonicalHash`
- derived code/runtime state
- current artifact set IDs
- blockers
- next owners and actions

The summary derives commit-set drift directly from `currentCommit` and `acceptedCommit`. A drifted required axis is reported as `needs-reverify` and includes a `commit-drift` blocker even if the stored axis value has not yet been repaired by a mutating audit.

Trust a cached summary only when both revision and hash match the live card. Read-only status queries stop at the summary. Mutation, migration, validation, archive, and audit operations may return the one normalized canonical payload because they require the full JSON.

Platform network tests belong in adapter packages. The public core tests only normalized offline snapshots and local filtering behavior.
