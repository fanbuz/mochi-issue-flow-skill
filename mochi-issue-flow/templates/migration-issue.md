# Migration: {from protocol/version} to {to protocol/version}

## Purpose

{What changes and the compatibility outcome}

## Migration scope

- Source carriers/artifacts: {list}
- Canonical target: {new carrier or Flow Card}
- Compatibility window: {dates or release versions}

## Safe sequence

1. Freeze the source current-state snapshot.
2. Create and validate the target state.
3. Add bidirectional links and migration evidence.
4. Move active ownership after acceptance.
5. Retain the source as an archived pointer; do not leave two authorities.

## Acceptance criteria

- [ ] One carrier/comment is authoritative after cutover.
- [ ] Registry state is bound to the canonical revision, or has an approved waiver.
- [ ] Existing links resolve to the new current-state record.
- [ ] Rollback owner and condition are recorded.
