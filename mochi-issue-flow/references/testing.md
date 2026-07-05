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

## Pass Criteria

- The agent explains routing in user language.
- The agent asks at most one routing question when ambiguous.
- The agent does not expose protocol jargon as the main output.
- The agent never creates every downstream issue at L3 kickoff.
- Every created linked issue has a backlink and next action owner.
- Stale, contract, gate, suspension, and escalation paths follow `exceptions.md`.
