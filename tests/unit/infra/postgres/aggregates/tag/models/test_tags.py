from sqlalchemy import String

from src.infra.postgres.aggregates.tag.models.tags import TagRecord


def test_tag_record_declares_expected_table_name() -> None:
    assert TagRecord.__tablename__ == "tags"


def test_tag_record_table_matches_expected_shape() -> None:
    tags_table = TagRecord.__table__

    assert set(tags_table.columns.keys()) == {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "title",
    }
    assert list(tags_table.primary_key.columns.keys()) == ["id"]
    assert isinstance(tags_table.c.title.type, String)
