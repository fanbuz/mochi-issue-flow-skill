# Gitea Carrier Notes

The author often uses Gitea issues as the issue-like carrier and pairs this skill with `gitea-cli`. This reference is optional and intentionally generic.

## Suggested Flow

1. Read the source issue body, labels, and latest decisive comments.
2. If creating a support issue, use a current-state body from `templates.md`.
3. Add a backlink comment to the source issue.
4. Apply labels or milestones only if the repository already has a matching vocabulary.
5. Read back the saved issue and comment URL.
6. Record the URL in any registry/index cache.

## Safe Defaults

- Prefer existing labels over creating new labels.
- Do not assume label names are globally available across repositories.
- Do not close a support issue until the acceptance/driver side has verified.
- Use comment-level URLs for handoff and evidence links when the platform supports them.

## Example Command Shape

Commands vary by `gitea-cli` installation. Use the local help output before writing:

```bash
gitea-cli --help
gitea-cli issues --help
gitea-cli comments --help
```

Do not hard-code hostnames, tokens, organization names, or repository names in reusable templates.
