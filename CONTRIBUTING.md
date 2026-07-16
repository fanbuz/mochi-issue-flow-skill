# Contributing to Mochi Issue Flow

## Scope

Contributions should improve a carrier-neutral protocol, its templates, offline validators, or clearly separated platform adapters. Do not add organization-specific issue flows, private repository mappings, credentials, internal URLs, local paths, or sensitive business context to this public repository.

## Development loop

1. Start from the current Flow Card schema and scenario/evidence matrix.
2. Add a failing offline fixture test for a behavioural change.
3. Make the smallest implementation or documentation change that makes it pass.
4. Run the complete suite:

   ```bash
   python3 -m unittest discover -s mochi-issue-flow/tests -p 'test_*.py' -v
   ```

5. Run `git diff --check` and review the public-safety boundary before opening a pull request.
6. Run context-budget checks for changed summaries, adapter snapshots, or Flow Card fixtures.

## Documentation rules

- `SKILL.md` has frontmatter with only `name` and `description`; write protocol versions in the body or references.
- Keep `SKILL.md` concise; put schemas, templates, and detailed scenarios in their dedicated directories.
- Use lowercase hyphenated state values consistently.
- Network-dependent carrier tests belong in adapters. Core Flow Card tests must run from offline fixtures.
- Adapter outputs must contain one normalized canonical payload, not raw and parsed duplicates.
- Character budgets are deterministic CI gates; optional tokenizer counts are reference measurements.

## License

By contributing, you agree that your contribution is licensed under Apache-2.0, unless you have an explicit written agreement that states otherwise.
