from sqlalchemy.orm import registry

mapper_registry = registry()
postgres_metadata = mapper_registry.metadata
