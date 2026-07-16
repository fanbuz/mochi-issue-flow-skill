# Route Pressure Tests

Use these tests before publishing changes to the skill.

| User input | Expected route | Assertion |
|---|---|---|
| "Continue the source issue" | Recover existing state | Reads carrier before deciding |
| "The frontend needs backend help" | L2 linked issue flow | Asks for or detects source and target carriers |
| "Create a linked issue for this bug" | L2 linked issue flow | Presents confirmation before creating |
| "This spans app, API, and workflow service in phases" | L3 staged issue flow | Creates tracking issue plus first-phase links only |
| "Review this design" | Read-only/design route | Does not create carriers |
| "Can we close this?" | Closeout check | Blocks closeout without acceptance evidence |
| "Pause this until next week" | Suspend | Records reason and recovery condition |
| "Continue the linked issue from last month" | Stale recovery | Re-reads live carrier state and refreshes current-state block before resuming |
| "Start implementation for CT-02" | Contract gate | Blocks implementation while contract state is not `agreed` |
| "Open the next phase even though verification failed" | Phase gate | Keeps flow gate-blocked and does not create downstream linked issues |
| "This two-repo task now spans four services and phases" | L2 to L3 escalation | Creates or nominates a tracking carrier before adding new links |
| "先确认测试环境能不能用" | Read-only preflight | Explains the check in user language and says it will not modify data or start a real operation |
| "What is the current L3 status?" | Compact status read | Reads the canonical comment directly and returns a revision/hash-bound summary without comment history |
| "Close it; audit has no findings" | Closeout gate | Uses `closeoutEligible`, not an empty routine finding list |
| "These two issues both have a full Flow Card" | S4 consolidation | Chooses one canonical target and replaces the other card with an alias pointer |

## Pass Criteria

- The agent explains routing in user language.
- Before a tool operation, the agent explains its purpose, scope, and important non-effects in one or two complete sentences.
- The agent asks at most one routing question when ambiguous.
- The agent does not expose protocol jargon or implementation shorthand as the main output. It translates names such as `probe`, `sharedId`, `seed`, and `join` unless the user asks for those details.
- The agent never creates every downstream issue at L3 kickoff.
- Every created linked issue has a backlink and next action owner.
- Read-only L3 status queries do not load raw/parsed duplicates or unrelated comment history.
- A required axis outside `verified` makes closeout ineligible even when routine findings are empty.
- Evidence is removed from the active card only after a durable archive is hash-verified.
- A delivery mainline has one writable Flow Card after migration.
- Stale, contract, gate, suspension, and escalation paths follow `exceptions.md`.
