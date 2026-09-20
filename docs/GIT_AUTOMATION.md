# Git automation

Lifecycle:

User approves patch -> create branch -> apply approved patch -> sandbox validation -> exact diff preview -> user acknowledges preview -> commit -> push -> GitHub Pull Request.

A pending or rejected patch cannot be applied, committed, pushed, or used to create a Pull Request.

Before commit, the UI must display the exact CommitPlan diff and files. Automation requires an acknowledgement fingerprint over patch id, branch, diff, and commit message. Any change makes the acknowledgement stale.

Audit entries record branch, patch application, validation, preview, acknowledgement, commit, push, and Pull Request outcomes.

Git commands are fixed argv operations; arbitrary shell strings are rejected.

The GitHub API uses GITHUB_TOKEN for Pull Request creation. Token values are never placed in the audit trail.
