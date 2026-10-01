# Development practices

Use a small branch for one understandable change. Reproduce the problem, add a meaningful regression test, implement the fix, run relevant checks and review the diff before committing.

Suggested commit subjects:

- `fix: reject conflicting request IDs`
- `test: cover interrupted device checkpoints`
- `docs: distinguish mocked and live verification`

Commit bodies should explain why the change was needed, its limitations and test evidence. Do not invent old commits, backdate work, or manufacture a contribution streak. Start with an honest import commit describing an existing project.

Before a commit, inspect `git status --short`, `git diff` and `git diff --cached`. Stage explicit reviewed files; do not stage the original Penny workspace. `.gitignore` is a convenience, not a secret detector, and does not remove files already tracked.

For a pull request, record the problem, resulting behaviour, tests, screenshots where relevant and remaining limits. An issue should define observable acceptance criteria rather than “make AI smarter”.

Keep a short decision note for consequential choices: context, options, decision, trade-offs, evidence. Record failed experiments when they explain a decision. Close milestones only after their acceptance checks pass.

Use the included CI workflow after publication. Local test passes are not GitHub CI passes. Review dependency/action updates deliberately and add coverage or linting only when the metric supports a real quality objective.
