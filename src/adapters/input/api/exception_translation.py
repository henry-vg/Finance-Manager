from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import NoReturn

from fastapi import HTTPException


@dataclass(frozen=True)
class HTTPExceptionTranslation:
    exception_type: type[Exception]
    status_code: int
    detail: str


def _raise_translated_http_exception(
    exc: Exception,
    translations: tuple[HTTPExceptionTranslation, ...],
) -> NoReturn:
    for translation in translations:
        if isinstance(exc, translation.exception_type):
            raise HTTPException(
                status_code=translation.status_code,
                detail=translation.detail,
            ) from exc

    raise AssertionError("Expected a matching HTTP exception translation")


@contextmanager
def translate_exceptions_to_http(
    *translations: HTTPExceptionTranslation,
) -> Iterator[None]:
    if not translations:
        yield
        return

    try:
        yield
    except tuple(translation.exception_type for translation in translations) as exc:
        _raise_translated_http_exception(exc, translations)
