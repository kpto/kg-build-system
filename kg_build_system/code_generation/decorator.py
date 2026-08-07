"""Runtime identity decorator used as the static generation marker."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

from .models import GenerationRequest


T = TypeVar("T")


@overload
def generated(value: T, /) -> T: ...


@overload
def generated(
    *, provider: str, source: str, selector: str | None = None, **configuration: Any
) -> Callable[[T], T]: ...


def generated(
    value: T | None = None,
    /,
    *,
    provider: str | None = None,
    source: str | None = None,
    selector: str | None = None,
    **configuration: Any,
) -> T | Callable[[T], T]:
    """Mark a declaration for edit-time generation without mutating its shape."""

    def decorate(declaration: T) -> T:
        if provider is not None and source is not None:
            setattr(
                declaration,
                "__kbs_generation__",
                GenerationRequest(provider, source, selector, configuration),
            )
        return declaration

    if value is not None:
        if provider is not None or source is not None or selector is not None or configuration:
            raise TypeError("@generated cannot combine a positional declaration with configuration")
        return value
    if not provider or not source:
        raise TypeError("@generated requires non-empty provider and source arguments")
    return decorate

