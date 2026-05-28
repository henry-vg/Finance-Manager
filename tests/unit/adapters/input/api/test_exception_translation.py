import pytest
from fastapi import HTTPException

from src.adapters.input.api.exception_translation import (
    HTTPExceptionTranslation,
    _raise_translated_http_exception,
    translate_exceptions_to_http,
)


class _DomainNotFoundError(Exception):
    pass


def test_translate_exceptions_to_http_maps_domain_exception() -> None:
    with pytest.raises(HTTPException) as exc_info:
        with translate_exceptions_to_http(
            HTTPExceptionTranslation(
                exception_type=_DomainNotFoundError,
                status_code=404,
                detail="Resource not found.",
            ),
        ):
            raise _DomainNotFoundError()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Resource not found."


def test_translate_exceptions_to_http_re_raises_unmapped_exception() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with translate_exceptions_to_http(
            HTTPExceptionTranslation(
                exception_type=_DomainNotFoundError,
                status_code=404,
                detail="Resource not found.",
            ),
        ):
            raise RuntimeError("boom")


def test_raise_translated_http_exception_requires_matching_translation() -> None:
    with pytest.raises(AssertionError, match="matching HTTP exception translation"):
        _raise_translated_http_exception(
            RuntimeError("boom"),
            (
                HTTPExceptionTranslation(
                    exception_type=_DomainNotFoundError,
                    status_code=404,
                    detail="Resource not found.",
                ),
            ),
        )


def test_translate_exceptions_to_http_allows_empty_translation_list() -> None:
    with translate_exceptions_to_http():
        pass
