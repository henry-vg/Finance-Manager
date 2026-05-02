import pytest


@pytest.fixture()
def app():
    from src.infra.fastapi.app import create_app

    return create_app()