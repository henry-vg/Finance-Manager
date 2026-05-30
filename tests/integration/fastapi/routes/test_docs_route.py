import pytest


@pytest.mark.anyio
async def test_get_docs_returns_html_with_dark_mode_enabled(
    fastapi_app,
    fastapi_client_factory,
) -> None:
    async with fastapi_client_factory(fastapi_app) as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/openapi.json" in response.text
    assert 'document.documentElement.classList.add("dark-mode")' in response.text


@pytest.mark.anyio
async def test_get_openapi_returns_metadata_and_documented_feature_paths(
    fastapi_app,
    fastapi_client_factory,
) -> None:
    async with fastapi_client_factory(fastapi_app) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    openapi_schema = response.json()

    assert openapi_schema["info"]["title"] == fastapi_app.title
    assert openapi_schema["info"]["version"] == fastapi_app.version
    assert {tag["name"] for tag in openapi_schema["tags"]} >= {
        "Currency",
        "HealthZ",
        "LedgerAccount",
        "Tag",
        "Transaction",
        "User",
    }
    assert set(openapi_schema["paths"]) >= {
        "/currency",
        "/currency/list",
        "/healthz/readiness",
        "/ledger-account",
        "/tag",
        "/transaction",
        "/transaction/post",
        "/transaction/void",
        "/user/list",
    }
