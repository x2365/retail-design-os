.PHONY: install dev test docker up down logs

install:        ## install backend deps (local dev)
	cd backend && pip install -r requirements.txt

dev:            ## run API locally on :8000 (SQLite, auto-reload)
	cd backend && uvicorn app.main:app --reload --port 8000

test:           ## run the integration smoke tests
	cd backend && python test_smoke.py

front:          ## serve the static frontend on :5500 (talks to :8000)
	cd frontend && python -m http.server 5500

up:             ## full stack via docker (postgres + api + nginx) on :8080
	docker compose up --build

scale:          ## run 3 API replicas behind the stack
	docker compose up --build --scale api=3

down:           ## stop and remove containers
	docker compose down

logs:
	docker compose logs -f api
