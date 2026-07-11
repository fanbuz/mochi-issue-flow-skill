# Workspace preflight

Before code or runtime verification, record the repository, branch, worktree path, and artifact SHA for every relevant repository. Decide deliberately:

- Use the direct branch only when it is clean, dedicated, and no concurrent agent owns it.
- Use a worktree when work must be isolated, a branch is shared, or parallel agents need independent indexes.

Then confirm that every required skill, script, template, configuration file, and generated artifact is materialized inside the selected workspace. Git-ignored local directories are not present in a newly created worktree unless explicitly copied or tracked. A missing required item is a preflight failure, not an invitation to proceed with a partial protocol.

The public product avoids repository-specific assumptions; project adapters own their local allowlists and setup checks.
