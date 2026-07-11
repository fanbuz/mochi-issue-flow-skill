# State and commit invalidation

Use one spelling everywhere: lowercase hyphenated enum values.

| Axis | Values |
|---|---|
| Code | `not-started`, `evidence-pending`, `verified`, `needs-reverify`, `failed`, `not-applicable` |
| Runtime | Code values plus `verifying`, `blocked` |
| Coordination | `planned`, `active`, `ready-for-acceptance`, `needs-reverify`, `done`, `suspended` |

`flowCodeState` and `flowRuntimeState` are derived only from Bridges whose corresponding `*Required` field is true: no required Bridges means `not-applicable`; any `failed` wins; then `needs-reverify`; for runtime then `blocked`; all verified means `verified`; otherwise `pending`.

When `currentCommit` differs from `acceptedCommit`, preserve each axis's active evidence in `supersededEvidence` with old and replacement artifact-set IDs, clear only active evidence, and set required axes to `needs-reverify`. Keep the historical evidence for audit but do not count it toward the replacement set. The coordination state is a workflow signal, never a substitute for the two derived axes.
