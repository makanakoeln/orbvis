.PHONY: help fmt lint type test precommit install-hooks

help:
	@echo "make fmt           - format code (ruff format + prettier)"
	@echo "make lint          - lint code (ruff check + eslint)"
	@echo "make type          - type-check (mypy + vue-tsc)"
	@echo "make test          - run tests (pytest + vitest)"
	@echo "make precommit     - run pre-commit hooks on all files"
	@echo "make install-hooks - install pre-commit and pre-push git hooks"

install-hooks:
	pre-commit install --hook-type pre-commit --hook-type pre-push

fmt:
	ruff format backend/app backend/tests cmk_plugins_23 tools
	cd frontend && npm run format

lint:
	ruff check backend/app backend/tests cmk_plugins_23 tools
	cd frontend && npm run lint

type:
	backend/.venv/bin/mypy backend/app
	cd frontend && npm run type-check

test:
	cd backend && pytest
	cd frontend && npm test

precommit:
	pre-commit run --all-files
