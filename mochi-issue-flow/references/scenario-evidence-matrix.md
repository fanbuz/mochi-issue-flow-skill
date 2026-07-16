# Scenario and evidence matrix

| Scenario | Trigger | Required evidence | Expected gate |
|---|---|---|---|
| S1 single carrier | Work is isolated | Current-state card and acceptance evidence | L1 can close |
| S2 linked support | One owner needs another | Backlinks, driver/support roles, handoff packet | Driver accepts support result |
| S3 staged multi-repo | Multiple Bridges or dependencies | Valid Flow Card, DAG, complete artifact sets, code/runtime evidence | Derived axes verified before done |
| S4 recovery/migration | Stale, drifted, duplicate, or version-migrated flow | Archived source, canonical target, alias/backlink, transfer/audit evidence | One writable authority after recovery |

For all scenarios, audit missing status, commit drift, registry deferral or revision mismatch, expired lease, and runtime blockers. Use `routine` during execution and `closeout` before completion; only closeout returns a boolean eligibility decision. Unit tests use offline fixture JSON. Network reads from GitHub, Gitea, Jira, Linear, or another carrier belong in an adapter integration test layer and are never prerequisites for deterministic core tests.
