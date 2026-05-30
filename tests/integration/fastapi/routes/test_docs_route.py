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
        "/transaction/list",
        "/transaction/post",
        "/transaction/void",
        "/user/list",
    }


@pytest.mark.anyio
async def test_get_openapi_documents_transaction_write_errors_as_markdown_lists(
    fastapi_app,
    fastapi_client_factory,
) -> None:
    async with fastapi_client_factory(fastapi_app) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    openapi_schema = response.json()

    assert openapi_schema["paths"]["/transaction"]["post"]["responses"]["422"][
        "description"
    ] == (
        "- The request body failed validation.\n"
        "- The transaction violated one or more business rules."
    )
    assert openapi_schema["paths"]["/transaction"]["put"]["responses"]["422"][
        "description"
    ] == (
        "- The request payload or query parameters failed validation.\n"
        "- The transaction violated one or more business rules."
    )


@pytest.mark.anyio
async def test_get_openapi_documents_multi_outcome_responses_as_markdown_lists(
    fastapi_app,
    fastapi_client_factory,
) -> None:
    async with fastapi_client_factory(fastapi_app) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    openapi_schema = response.json()

    assert openapi_schema["paths"]["/ledger-account"]["post"]["responses"]["422"][
        "description"
    ] == (
        "- The request body failed validation.\n"
        "- The selected instrument kind is not allowed for the provided ledger account type."
    )
    assert openapi_schema["paths"]["/user"]["delete"]["responses"]["204"][
        "description"
    ] == (
        "- The user was soft-deleted when `hard_delete=false`.\n"
        "- The user was permanently deleted when `hard_delete=true`."
    )
