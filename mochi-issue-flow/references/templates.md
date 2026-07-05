# Mochi Issue Flow Templates

These templates are intentionally carrier-neutral. Replace "issue" with ticket, task, request, card, or another durable workflow carrier when needed.

## Recognition Card

```md
## Detected workflow action
- Action:
- Reason:
- Route: single-repo / linked issue / staged multi-repo flow / read-only
- This will create:
- Needs confirmation:
```

## Current-State Card

```md
## Current work state
- Task:
- Type:
- Current state:
- Current owner:
- Next action:
- Blocker:
- Source:
```

## Linked Issue Confirmation

```md
## Confirm linked issue creation
- Source issue:
- Target repository/team:
- Collaboration type:
- Current goal:
- Support scope:
- Acceptance criteria:
- Will update:
  - create target issue
  - add backlink to source issue
  - record registry/index entry if used
  - generate handoff package
```

## Tracking Issue Current-State Block

```md
## Flow state
- flowId:
- flow owner:
- flow state: planned / active / gate-blocked / done / suspended
- current phase:
- active contracts:
- next action owner:
- next action:
- active linked issues:
- blockers:
- last state update:
```

## Contract Entry

```md
## Contract {contractId}
- state: draft / agreed / implemented / verified
- owner:
- participants:
- scope:
- acceptance:
- affected linked issues:
- last state update:
```

Rule: not agreed, no implementation. Contract changes update the tracking issue first, then affected linked issues.

## Phase Gate Block

```md
## Phase {phase}
- state: planned / active / gate-blocked / done / suspended
- entryCriteria:
- exitCriteria:
- rollback:
- required linked issues:
- gate result:
- next phase:
- last state update:
```

Exit must pass before downstream linked issues are opened. At phase close, required linked issues must be terminal or explicitly suspended.

## Linked Issue Current-State Block

```md
## Linked work state
- linkId:
- source issue:
- target issue:
- role: driver / support
- state: needs-support / support-in-progress / support-ready / driver-verifying / driver-feedback / done / suspended
- current owner:
- next action owner:
- next action:
- acceptance criteria:
- upstream comment:
- suspended reason:
- recovery condition:
- last state update:
```

`suspended reason` and `recovery condition` are required when state is `suspended`.

## Handoff Package

```md
## Handoff package
- To:
- Role:
- Goal:
- Source issue:
- Current state:
- Expected output:
- Acceptance criteria:
- Important links:
- Please do not:

Prompt:
You are joining an issue-driven workflow as the {role}. Read the source and target carriers, trust their current-state blocks, complete the next action, and write a concise current-state update with evidence and owner.
```

## Closeout Card

```md
## Closeout check
- Delivery committed/published:
- Verification completed:
- Linked issues updated:
- Driver/acceptance owner approved:
- Registry/cache consistent:
- Remaining risks:
- Can close:
```
