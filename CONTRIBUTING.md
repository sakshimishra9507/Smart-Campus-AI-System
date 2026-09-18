# Contributing to SmartCampus AI

## Development Rules

1. Create a separate branch for each feature.
2. Keep commits small and descriptive.
3. Never commit `.env`, passwords, API keys, real student records, or database dumps.
4. Add tests for important business logic.
5. Run formatting/linting before opening a pull request.
6. Update documentation when a feature changes.

## Branch Naming

```text
feature/login
feature/timetable
feature/attendance
feature/ml-prediction
fix/attendance-calculation
docs/readme
```

## Commit Examples

```text
feat: add role based login
feat: add timetable module
feat: add attendance calculation
feat: add student performance prediction
fix: correct attendance percentage
docs: update installation guide
```

## Pull Request Checklist

- [ ] Feature works locally
- [ ] Tests pass
- [ ] No secrets are included
- [ ] No real personal/student data is included
- [ ] Documentation is updated
