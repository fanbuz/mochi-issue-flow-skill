# Conditional canonical comment edit

Use this contract only to edit an existing canonical comment. Bootstrap/create is a separate operation: create one comment, capture its URL, then use conditional edit for every later revision. Never recover from an uncertain edit by appending another Flow Card.

## Request

```json
{
  "canonicalStatusCommentUrl": "https://carrier.example/issues/1#comment-2",
  "expectedStatusRevision": 7,
  "expectedCanonicalHash": "sha256:...",
  "safetyMode": "best-effort-conditional",
  "actor": {
    "agentId": "agent-1",
    "threadId": "thread-1",
    "sessionId": "session-1"
  },
  "targetCanonicalComment": {
    "url": "https://carrier.example/issues/1#comment-2",
    "body": "complete replacement comment containing revision 8"
  }
}
```

Use `atomic-cas` only when the carrier exposes a native conditional edit primitive. Otherwise declare `best-effort-conditional`; this means an exact read immediately precedes the in-place edit and a second exact read verifies it, but a residual race still exists between read and write.

## Required sequence

1. Read the exact comment identity.
2. Run `scripts/conditional_comment_edit.py prepare REQUEST SNAPSHOT --now TIMESTAMP` or call `prepare_conditional_edit`.
3. Stop on revision/hash drift, invalid target, expired lease, or ownership mismatch.
4. Edit that comment in place. Pass the revision/hash precondition to a native CAS API when supported.
5. Read the exact comment again and run the `verify` phase.
6. Continue registry projection only when `registryMaySync` is true.

The target revision must be exactly the expected revision plus one and must preserve `flowId` and `canonicalStatusCommentUrl`. A retry whose target is already saved returns `already-applied` and skips the edit.

## Stable outcomes

| Code/outcome | Meaning | Recovery |
|---|---|---|
| `success` | Target revision/hash was saved and reread | Registry projection may continue |
| `already-applied` | A prior attempt saved the same target | Do not edit again; registry projection may continue |
| `revision-drift` / `canonical-hash-drift` | Live authority changed | Rebuild the target from the new live card |
| `ownership-rejected` | Actor does not hold a live lease | Renew or transfer ownership before retrying |
| `edit-failed` | Provider rejected the edit | Fix the provider call, then reread |
| `edit-result-unknown` | Provider timed out after submission | Reread before any retry |
| `post-write-mismatch` | Provider success could not be verified | Stop; registry projection remains blocked |

## Provider method mapping

Resolve method names from the installed tool schema once, not by sending trial writes.

| Carrier family | Existing-comment operation | Required identity/body fields |
|---|---|---|
| GitHub connector | `github_update_issue_comment` | repository, comment ID, replacement comment body |
| Gitea MCP | `issue_write` with `method=edit_comment` | owner, repository, issue number, `commentID`, replacement body |

Provider packages may wrap these calls, but they must expose the request/result semantics above. Keep hostnames, credentials, organization names, and repository names out of the public package.
