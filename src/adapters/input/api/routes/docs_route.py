from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse


def create_router(
    docs_url: str,
    docs_title: str,
    docs_dark_mode: bool,
    openapi_url: str,
) -> APIRouter:
    router = APIRouter()

    @router.get(
        path=docs_url,
    )
    def get_docs() -> HTMLResponse:
        body = get_swagger_ui_html(
            openapi_url=openapi_url,
            title=docs_title,
        ).body.decode("utf-8")

        if docs_dark_mode:
            body = body.replace(
                "</body>",
                (
                    "<script>"
                    'document.documentElement.classList.add("dark-mode");'
                    "</script>"
                    "</body>"
                ),
            )

        return HTMLResponse(content=body)

    return router
