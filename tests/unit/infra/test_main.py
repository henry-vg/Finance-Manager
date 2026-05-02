import pytest

from src.infra.bootstrap import build_application_container
from src.infra.main import create_app


@pytest.mark.anyio
async def test_create_app_disposes_postgres_engine_on_shutdown(monkeypatch):
    import src.infra.main as main_module

    container = build_application_container()
    disposed_engine = None

    async def fake_dispose_postgres_engine(engine):
        nonlocal disposed_engine
        disposed_engine = engine

    monkeypatch.setattr(main_module, "build_application_container", lambda: container)
    monkeypatch.setattr(
        main_module,
        "dispose_postgres_engine",
        fake_dispose_postgres_engine,
    )

    app = create_app()

    async with app.router.lifespan_context(app):
        pass

    assert disposed_engine is container.postgres_engine
