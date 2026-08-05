"""Stable conventions for names inferred from Python declarations."""
from __future__ import annotations

import re


def snake_case(value: str) -> str:
    """Convert a Python identifier to the portable external-name convention."""
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Za-z])([0-9])", r"\1_\2", value)
    value = re.sub(r"([0-9])([A-Za-z])", r"\1_\2", value)
    return value.lower()


def declaration_name(class_name: str, *, suffixes: tuple[str, ...] = ()) -> str:
    """Infer a declaration name, removing one matching semantic suffix."""
    stem = class_name
    for suffix in suffixes:
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    if not stem:
        raise ValueError(f"{class_name!r} has no name after removing its declaration suffix")
    return snake_case(stem)
