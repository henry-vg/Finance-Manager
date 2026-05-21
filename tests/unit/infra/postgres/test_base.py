from src.infra.postgres.base import (
    PostgresPersistedRecordMixin,
    mapper_registry,
    postgres_metadata,
)


def test_postgres_metadata_reuses_mapper_registry_metadata() -> None:
    assert postgres_metadata is mapper_registry.metadata


def test_persisted_record_mixin_declares_standard_audit_fields() -> None:
    assert set(PostgresPersistedRecordMixin.__annotations__) == {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
    }
