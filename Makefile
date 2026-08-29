.PHONY: check-node setup dev-api dev-web test-api test-e2e build-web

check-node:
	@node -e 'const major=Number(process.versions.node.split(".")[0]); if (major !== 22) { console.error("BioLoop Web exige Node.js 22. Exécutez: nvm use"); process.exit(1) }'

setup: check-node
	python3 -m venv .venv
	.venv/bin/pip install -r services/api/requirements-dev.txt
	npm --prefix apps/web ci

dev-api:
	.venv/bin/python -m uvicorn app.main:app --app-dir services/api --reload --port 8000

dev-web: check-node
	NEXT_PUBLIC_API_URL=http://localhost:8000 npm --prefix apps/web run dev

test-api:
	.venv/bin/python -m pytest

build-web: check-node
	npm --prefix apps/web run build

test-e2e: check-node
	npm --prefix apps/web run test:e2e
