from src.infra.fastapi.tags import openapi_tags


def test_openapi_tags_include_all_public_api_groups() -> None:
    assert [tag["name"] for tag in openapi_tags] == [
        "HealthZ",
        "Currency",
        "LedgerAccount",
        "Tag",
        "Transaction",
        "User",
    ]
