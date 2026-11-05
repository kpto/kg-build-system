"""Composition of the built-in operation specifications.

Each operation owns one module. This module composes them and rejects a
duplicate name, so two operations cannot silently shadow one another.
"""
from __future__ import annotations

from .add import ADD
from .after_separator import AFTER_SEPARATOR
from .and_ import AND
from .append import APPEND
from .array_at import ARRAY_AT
from .array_slice import ARRAY_SLICE
from .before_separator import BEFORE_SEPARATOR
from .coalesce import COALESCE
from .concat import CONCAT
from .distinct import DISTINCT
from .drop_if import DROP_IF
from .drop_null import DROP_NULL
from .drop_null_items import DROP_NULL_ITEMS
from .equals import EQUALS
from .expand import EXPAND
from .join import JOIN
from .not_ import NOT
from .or_ import OR
from .replace import REPLACE
from .sort import SORT
from .spec import OperationRegistry
from .struct_field import STRUCT_FIELD
from .subtract import SUBTRACT
from .to_string import TO_STRING
from .transform_items import TRANSFORM_ITEMS

DEFAULT_OPERATIONS = OperationRegistry((
    ADD,
    SUBTRACT,
    CONCAT,
    APPEND,
    EQUALS,
    REPLACE,
    TO_STRING,
    BEFORE_SEPARATOR,
    AFTER_SEPARATOR,
    ARRAY_AT,
    ARRAY_SLICE,
    TRANSFORM_ITEMS,
    DROP_NULL_ITEMS,
    SORT,
    DISTINCT,
    JOIN,
    COALESCE,
    NOT,
    AND,
    OR,
    STRUCT_FIELD,
    EXPAND,
    DROP_NULL,
    DROP_IF,
))

__all__ = ["DEFAULT_OPERATIONS"]
