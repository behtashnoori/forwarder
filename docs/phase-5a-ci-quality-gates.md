# Phase 5A: CI/CD Quality Gates

## 1. Scope

Phase 5A adds GitHub Actions quality gates only.

No runtime code, API behavior, migration, schema/model, frontend behavior,
lint rule, test skip/xfail, or dependency manifest was changed.

## 2. Current Local Quality Baseline

Before adding CI:

- `python -m pytest -q`: 69 passed
- `npm.cmd run lint`: passed with existing warnings, 0 errors
- `npm.cmd run build`: passed
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed

Dependency decision:

- `requirements.txt` at the repository root is used by CI for backend tests.
- `backend/requirements.txt` is a production/deployment superset that adds
  `gunicorn` and `psycopg2-binary`; it is not required for the current unit
  test quality gate.
- `pytest` is installed in CI as the test runner because it is not currently
  pinned in either requirements file. No dependency file was changed.

## 3. Workflow Design

Workflow: `.github/workflows/quality-gates.yml`

Triggers:

- `push`
- `pull_request`

Jobs:

| job | purpose | commands |
| --- | --- | --- |
| `backend-tests` | Protect backend unit/contract behavior. | `python -m pip install -r requirements.txt pytest`; `python -m pytest -q` |
| `frontend-lint-build` | Protect frontend lint and production build health. | `npm ci`; `npm run lint`; `npm run build` |
| `structure-check` | Protect repository structure and whitespace hygiene. | `npm ci`; `npm run check:structure`; `git diff --check` |

Caching:

- `actions/setup-python` pip cache keyed by `requirements.txt`
- `actions/setup-node` npm cache keyed by `package-lock.json`

## 4. Files Changed

| file | change summary | reason | runtime impact |
| --- | --- | --- | --- |
| `.github/workflows/quality-gates.yml` | Added GitHub Actions workflow for backend tests, frontend lint/build, structure check, and whitespace check. | Automate current local quality gates on push and pull request. | None |
| `docs/phase-5a-ci-quality-gates.md` | Added Phase 5A implementation notes, workflow design, branch protection recommendation, and verification record. | Document CI quality gate scope and decisions. | None |

## 5. Branch Protection Recommendation

After this workflow runs successfully on GitHub, configure branch protection to
require these status checks:

- `backend-tests`
- `frontend-lint-build`
- `structure-check`

Do not require branch protection changes from this phase automatically; apply
them manually in GitHub repository settings.

## 6. After

Post-change local verification:

- `python -m pytest -q`: 69 passed
- `npm.cmd run lint`: passed with existing warnings, 0 errors
- `npm.cmd run build`: passed
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed

CI result is pending until the workflow runs on GitHub after push or pull
request creation.

## 7. Deferred Items

- deployment automation
- production release pipeline
- Docker image publishing
- repository layer
- user management refactor
- frontend warning cleanup
- OpenAPI documentation
