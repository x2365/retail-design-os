.PHONY: install dev test lint typecheck format front front-install front-lint front-typecheck front-build docker up down logs

install:        ## install backend deps incl. dev tooling (local dev)
	cd backend && pip install -r requirements-dev.txt

dev:            ## run API locally on :8000 (SQLite, auto-reload)
	cd backend && uvicorn app.main:app --reload --port 8000

test:           ## run the backend test suite
	cd backend && pytest -q

lint:           ## ruff check (backend)
	ruff check backend

# mypy (unlike ruff) doesn't search upward for pyproject.toml, so it must run
# from the repo root — `cd backend && mypy app` would silently fall back to
# unconfigured defaults instead of erroring.
typecheck:      ## mypy (backend/app)
	mypy backend/app

format:         ## ruff format (backend)
	ruff format backend

front-install:  ## install frontend deps
	cd frontend && npm install

front:          ## run Vite dev server on :5500 (proxies /api to :8000)
	cd frontend && npm run dev

front-lint:     ## eslint (frontend)
	cd frontend && npm run lint

front-typecheck: ## tsc --noEmit (frontend)
	cd frontend && npm run typecheck

front-build:    ## production build (frontend)
	cd frontend && npm run build

up:             ## full stack via docker (postgres + api + nginx) on :8080
	docker compose up --build

scale:          ## run 3 API replicas behind the stack
	docker compose up --build --scale api=3

down:           ## stop and remove containers
	docker compose down

logs:
	docker compose logs -f api
