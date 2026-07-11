# Lease, monitoring, and ownership transfer

Only the lease owner may mutate the canonical status comment. A lease contains `owner`, optional `threadId` and `sessionId`, `acquiredAt`, `lastHeartbeatAt`, `expiresAt`, and `transfer`.

1. Read the canonical card and its `statusRevision`.
2. Acquire only when absent, expired, or explicitly transferred; edit the same comment and increment the revision.
3. Heartbeat before half the lease duration elapses; each heartbeat increments the revision.
4. A monitor reports `lease-stalled` after expiry and must not silently seize an unexpired lease.
5. Transfer records prior owner, new owner, reason, timestamp, and the revision observed. The recipient acknowledges by an in-place edit.

Use a carrier adapter's conditional edit/version feature when available. Otherwise reread immediately before writing and abort on revision or owner change. The idempotency key in each delivery packet prevents duplicate issue writes across retries.
