# Exception Handling

Use one handling path per exception. Do not keep working from ambiguous state.

| Exception | Detection | Required handling |
|---|---|---|
| Cache conflicts with carrier | Registry/index disagrees with carrier body or decisive comments | Trust the carrier authority order, update the cache, and record the correction |
| Cache is missing | Carrier exists but registry/index has no entry | Reconstruct the entry from carrier links and current-state blocks before continuing |
| Stale linked carrier | `last state update` is older than the configured threshold, default 14 days | Re-read live carrier state, refresh the current-state block, then resume |
| Incompatible protocol version | Carrier declares an unsupported `mochi-issue-flow` version | Stop, report the version mismatch, and ask whether to migrate or continue manually |
| Phase gate failed | Exit criteria are unmet or rollback is selected | Keep the flow gate-blocked and do not open downstream linked work |
| Valid suspension | Work is intentionally paused | Set state to `suspended` with reason, recovery condition, owner, and next review point |
| L2 escalates to L3 | One linked issue pair becomes multi-repo, multi-phase, or contract-governed | Create or nominate a tracking carrier, preserve existing links, and move new coordination there |
