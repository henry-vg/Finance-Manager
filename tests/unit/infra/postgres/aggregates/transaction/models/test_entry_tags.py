from src.infra.postgres.aggregates.transaction.models.entry_tags import EntryTagRecord


def test_entry_tag_record_declares_expected_table_name() -> None:
    assert EntryTagRecord.__tablename__ == "entry_tags"


def test_entry_tag_record_table_matches_expected_shape() -> None:
    entry_tags_table = EntryTagRecord.__table__
    entry_fk = next(iter(entry_tags_table.c.entry_id.foreign_keys))
    tag_fk = next(iter(entry_tags_table.c.tag_id.foreign_keys))

    assert list(entry_tags_table.columns.keys()) == ["entry_id", "tag_id"]
    assert list(entry_tags_table.primary_key.columns.keys()) == ["entry_id", "tag_id"]
    assert entry_fk.target_fullname == "entries.id"
    assert entry_fk.ondelete == "CASCADE"
    assert tag_fk.target_fullname == "tags.id"
