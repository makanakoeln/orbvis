## Summary

<!-- 1-3 bullets describing what this PR does and why. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (no behaviour change)
- [ ] Documentation
- [ ] CI / tooling
- [ ] Security fix

## Test plan

<!-- How did you verify the change? Include manual steps for UI changes. -->

- [ ] Backend tests pass: `cd backend && pytest`
- [ ] Frontend tests pass: `cd frontend && npm test`
- [ ] Linters pass: `make precommit` and `cd frontend && npm run lint && npm run typecheck`
- [ ] Manual UI smoke test (if frontend touched)
- [ ] MKP build verified on a fresh OMD site (if MKP/install touched)

## Screenshots / video

<!-- For UI changes. Drag-and-drop into the GitHub editor. -->

## Breaking changes

- [ ] None
- [ ] Yes — described in CHANGELOG and below:

<!-- Describe the breaking change and migration path. -->

## Checklist

- [ ] Commit subject follows `<scope>: <what changed>` (lowercase, imperative)
- [ ] No `Co-Authored-By` lines in commits
- [ ] CHANGELOG.md updated for user-visible changes
- [ ] Docs updated if behaviour or config changed
- [ ] No new `any` / `eslint-disable` / `# type: ignore` without justification
