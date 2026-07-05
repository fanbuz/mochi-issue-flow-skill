# Mochi Issue Flow Skill

[中文](README.md)

Mochi Issue Flow is an **issue-action workflow SOP skill** for AI agents. It organizes requirement clarification, cross-repository collaboration, state recovery, handoff, and closeout around a durable issue-like carrier so that workflow state can be read, restored, synchronized, and audited.

In this project, **issue** is a generic concept, not only a GitHub Issue. Any object that can store body text, comments, links, status, and checklists can act as a workflow carrier:

- Gitea issue
- GitHub issue
- Linear issue
- Jira ticket
- workflow task
- project management card
- any other durable system object with body, comments, and state

## Use Cases

Mochi Issue Flow is designed for work that needs issue-like carriers as the collaboration surface:

- Single-repository work needs a stable current state, next action, and acceptance criteria.
- One issue needs support from another repository, team, or agent.
- Multi-repository work needs phased execution with entry, exit, and rollback criteria.
- Existing collaboration needs to be recovered from issue body, comments, and links.
- A task needs a self-contained handoff package for another agent.
- Closeout needs checks for commits, verification, linked issues, acceptance, and state consistency.

## Core Model

Mochi Issue Flow routes collaboration into three levels:

| Level | Scenario | Carrier Strategy |
|---|---|---|
| L1 single-carrier work | The current repository or task can finish independently | Store state in the current issue-like carrier without creating linked issues |
| L2 linked issue flow | One source carrier needs support from one target repository, team, or agent | Create one bidirectional linked issue pair and keep source and target linked |
| L3 staged flow | Multi-repository, multi-phase, multiple linked lines, or contract / phase gate work | Create a tracking issue and create only the linked issues required for the current phase |

In L2 and L3 workflows, the issue-like carrier is the authority for workflow state. Registries, dashboards, local notes, and visualizations are caches or projections.

## User Interaction Principles

Mochi Issue Flow asks agents to present work state in user-readable language before exposing protocol fields.

The user's main reading path should answer:

- What is the current task?
- What state is it in?
- Who owns the current action?
- What is the next action?
- Is anything blocked?
- Where are the linked carriers?
- What conditions allow acceptance or closeout?

Protocol fields such as `flowId`, `linkId`, `contractId`, and `phase` may be stored in issue bodies or extended sections, but they should not replace a readable current-state statement.

## Installation

Copy `mochi-issue-flow/` into a directory that supports Agent Skills:

```bash
cp -R mochi-issue-flow ~/.codex/skills/
cp -R mochi-issue-flow ~/.claude/skills/
cp -R mochi-issue-flow ~/.agents/skills/
```

If multiple runtimes share the same skill set, `~/.agents/skills/` is recommended.

## Repository Layout

```text
mochi-issue-flow-skill/
|-- README.md
|-- README.en.md
|-- VERSION
`-- mochi-issue-flow/
    |-- SKILL.md
    |-- agents/
    |   `-- openai.yaml
    `-- references/
        |-- carrier-model.md
        |-- exceptions.md
        |-- gitea-cli.md
        |-- templates.md
        `-- testing.md
```

## Capabilities

- **Intent routing**: Classify user input, issue links, repository signals, and existing state into L1 / L2 / L3 / read-only routes.
- **State recovery**: Recover workflow state from carrier body, decisive comments, labels, checklists, and registry caches.
- **Linked issue creation**: Create source / target backlinks for cross-repository or cross-team collaboration.
- **Staged execution**: Use a tracking issue to manage phases, contracts, gates, and current ownership.
- **Exception handling**: Handle cache mismatch, stale state, incompatible protocol version, failed gates, valid suspension, and L2-to-L3 escalation.
- **Handoff and closeout**: Produce a handoff package and verify evidence, linked carriers, and acceptance before closeout.

## Gitea and gitea-cli

Mochi Issue Flow is carrier-neutral and does not depend on a specific issue platform. One common implementation uses Gitea issues as carriers and `gitea-cli` to read issues, create linked issues, write comments, and update state.

Gitea guidance lives in `mochi-issue-flow/references/gitea-cli.md`. It contains generic command shapes and safe defaults only; it does not contain private hosts, organizations, repositories, or credentials.

## Examples

Create a linked issue:

```text
This issue needs support from another repository. Create a linked issue.
```

Recover existing work:

```text
Continue this issue and recover the current state first.
```

Create staged coordination:

```text
This change spans multiple repositories and needs staged delivery with acceptance gates.
```

## Security and Sanitization

This repository contains only generic skill files, templates, and references. Public content should not include:

- local repository paths
- private domains or internal service URLs
- access tokens, secrets, or account credentials
- internal issue numbers or private project names
- sensitive customer, employee, payroll, or attendance data

Platform configuration, private repository mappings, internal labels, and organization-specific workflows should live in a private distribution or local configuration.
