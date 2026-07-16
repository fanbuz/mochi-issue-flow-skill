# Evidence archive and single-card migration

## Two-phase evidence archive

1. Reread the canonical card and record its `statusRevision`.
2. Run `scripts/archive_flow_evidence.py prepare` for one Bridge axis.
3. Write the returned immutable archive through the carrier adapter.
4. Read the archive back and verify its URL and SHA-256 content hash.
5. Run `apply --expected-hash <prepared hash>` against the unchanged card revision. Apply verifies the same `flowId`, Bridge axis, evidence count, artifact-set IDs, timestamp, and archive hash before producing an updated card.
6. Synchronize projections and bind the new revision.

Never clear `supersededEvidence` before the archive is durable and verified. A failed archive write leaves the card unchanged. A failed canonical edit leaves a reusable orphan archive; retry with the same archive only while its source revision and evidence still match.

`archiveRefs` preserve the archive URL, content hash, artifact set IDs, evidence count, and creation time. They are audit pointers, not active evidence.

## One active Flow Card

Split Bridges by independently acceptable business boundary, not simply by repository pair. A delivery mainline has one writable canonical card even when several issues carry evidence.

To consolidate duplicates:

1. Freeze every source snapshot and choose the canonical target.
2. Merge current artifact sets, active evidence, dependencies, blockers, and next actions.
3. Validate and closeout-audit the target without declaring it done.
4. Add backlinks and replace each former card with `templates/flow-card-alias.md`.
5. Update registry pointers and verify only one sentinel block remains writable.

Do not silently delete former evidence or leave two full cards that can diverge.
