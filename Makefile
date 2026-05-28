run-database:
	docker compose -f docker/dev/docker-compose.yml up -d postgres

run-api:
	CFG_POSTGRES_HOST=localhost uvicorn src.infra.main:create_app --factory --host=0.0.0.0 --port=8000 --reload --reload-dir=src --proxy-headers --forwarded-allow-ips='*' --no-server-header --timeout-keep-alive=5 --timeout-graceful-shutdown=20 --limit-concurrency=1000 --backlog=2048 --no-access-log

run-api-docker:
	CFG_POSTGRES_HOST=postgres uvicorn src.infra.main:create_app --factory --host=0.0.0.0 --port=8000 --reload --reload-dir=src --proxy-headers --forwarded-allow-ips='*' --no-server-header --timeout-keep-alive=5 --timeout-graceful-shutdown=20 --limit-concurrency=1000 --backlog=2048 --no-access-log

run-migrations:
	CFG_POSTGRES_HOST=localhost alembic upgrade head

run-tests:
	python3 -m pytest

run-tests-with-coverage:
	python3 -m pytest --cov=src --cov-report=term-missing