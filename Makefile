run-database:
	docker compose -f docker/dev/docker-compose.yml up -d postgres

run-api:
	CFG_POSTGRES_HOST=localhost uvicorn src.infra.main:create_app --host 0.0.0.0 --factory --reload --reload-dir=src

run-api-docker:
	CFG_POSTGRES_HOST=postgres uvicorn src.infra.main:create_app --host 0.0.0.0 --factory --reload --reload-dir=src

run-migrations:
	CFG_POSTGRES_HOST=localhost alembic upgrade head