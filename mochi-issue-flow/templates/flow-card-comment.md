## Flow status

This comment is the single current-state record for the flow. Edit it in place only after satisfying the declared concurrency control. Put generated human context above the JSON and keep the sentinel block machine-readable. Optional sentinel attributes are allowed only when their `flowId` stays synchronized with the JSON.

<!-- flow-card:start v3 -->
```json
{
  "protocolVersion": "3.0",
  "flowId": "flow-example",
  "statusRevision": 1,
  "canonicalStatusCommentUrl": null,
  "concurrencyControl": { "mode": "lease" },
  "flowExecutionLease": {
    "owner": "agent/session identity",
    "threadId": "optional-codex-thread-id",
    "sessionId": "optional-runtime-session-id",
    "acquiredAt": "2026-07-11T09:00:00Z",
    "lastHeartbeatAt": "2026-07-11T09:00:00Z",
    "expiresAt": "2026-07-11T09:15:00Z",
    "transfer": null
  },
  "registry": {
    "status": "not-configured",
    "requiredForDone": false,
    "waiver": null
  },
  "bridges": [
    {
      "bridgeId": "api-web-example",
      "relevantArtifactRepos": ["service-api", "web-client"],
      "currentCommit": {
        "artifactSetId": "current-001",
        "repos": {
          "service-api": { "branch": "main", "sha": "0123456789abcdef" },
          "web-client": { "branch": "main", "sha": "fedcba9876543210" }
        }
      },
      "acceptedCommit": {
        "artifactSetId": "accepted-001",
        "repos": {
          "service-api": { "branch": "main", "sha": "0123456789abcdef" },
          "web-client": { "branch": "main", "sha": "fedcba9876543210" }
        }
      },
      "codeRequired": true,
      "runtimeRequired": true,
      "codeState": {
        "value": "verified",
        "activeEvidence": [],
        "supersededEvidence": [],
        "archiveRefs": []
      },
      "runtimeState": {
        "value": "verified",
        "activeEvidence": [],
        "supersededEvidence": [],
        "archiveRefs": []
      },
      "nextOwner": "acceptance owner",
      "nextAction": "describe the next decisive gate",
      "coordinationState": "ready-for-acceptance"
    }
  ],
  "dependencies": [],
  "flowCodeState": { "value": "verified" },
  "flowRuntimeState": { "value": "verified" }
}
```
<!-- flow-card:end -->

Bootstrap procedure: create this comment with `canonicalStatusCommentUrl: null`; after the carrier returns its URL, edit this same comment, set that URL, increment `statusRevision`, and retain the sentinel delimiters. Later edits follow `references/conditional-comment-edit.md` and verify the saved revision/hash before registry projection. Keep registry status `not-configured` unless the project uses one. A registry adapter binds its successful projection to the target revision and marks any partial failure `out-of-sync`; a failed canonical edit leaves the previous revision authoritative.
