.PHONY: up down test test-py test-go lint check-deps build logs

up:
	docker compose -f infra/docker-compose.yml up --build -d

down:
	docker compose -f infra/docker-compose.yml down -v

build:
	docker compose -f infra/docker-compose.yml build

logs:
	docker compose -f infra/docker-compose.yml logs -f

test: test-py test-go

test-py:
	docker compose -f infra/docker-compose.yml run --rm backend pytest tests/ -v

test-go:
	docker compose -f infra/docker-compose.yml --profile test run --rm payment-test

lint:
	docker compose -f infra/docker-compose.yml run --rm backend ruff check app/
	docker compose -f infra/docker-compose.yml run --rm --entrypoint sh payment-test -c "gofmt -l ./..."

check-deps:
	docker compose -f infra/docker-compose.yml run --rm backend pip-audit
	docker compose -f infra/docker-compose.yml --profile test run --rm --entrypoint sh payment-test -c "govulncheck ./..."
