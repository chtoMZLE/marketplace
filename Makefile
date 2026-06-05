.PHONY: up down test lint check-deps build logs

up:
	docker compose -f infra/docker-compose.yml up --build -d

down:
	docker compose -f infra/docker-compose.yml down -v

build:
	docker compose -f infra/docker-compose.yml build

logs:
	docker compose -f infra/docker-compose.yml logs -f

test:
	docker compose -f infra/docker-compose.yml run --rm backend pytest tests/ -v
	docker compose -f infra/docker-compose.yml run --rm payment go test ./...

lint:
	docker compose -f infra/docker-compose.yml run --rm backend ruff check app/
	docker compose -f infra/docker-compose.yml run --rm payment sh -c "gofmt -l ./... && golangci-lint run ./..."

check-deps:
	docker compose -f infra/docker-compose.yml run --rm backend pip-audit
	docker compose -f infra/docker-compose.yml run --rm payment govulncheck ./...
