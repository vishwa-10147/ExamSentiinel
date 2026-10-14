## Summary

<!-- What does this change do, and why? Link the related issue if there is one. -->

## Changes

-

## Testing

<!-- What did you run, and what were the results? State plainly if real-engine tests were skipped. -->

- [ ] Backend: `pytest -q -p no:cacheprovider`
- [ ] Frontend: `npx tsc --noEmit` and `npx next lint`
- [ ] Browser tests (for user-facing changes): `npx playwright test`

## Checklist

- [ ] Student-facing responses still exclude hidden tests, reference solutions and checkers
- [ ] AI output remains advisory — nothing penalises a candidate automatically
- [ ] Database changes include an Alembic migration
- [ ] Documentation updated where behaviour or configuration changed
- [ ] No secrets, local databases or build output committed
