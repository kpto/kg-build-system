"""Framework-internal binding service interface.

The codec, source renderer, transcription, factory wrappers and kernel language
adapter are resolved through this package.
"""
from __future__ import annotations

from .adapters import BindingLanguage
from .codec import (
    binding_from_document,
    binding_to_document,
    bindings_from_document,
    bindings_to_document,
)
from .source import bind_reference, render_binding_source
from .transcription import (
    collect_bindings,
    transcribe_binding_part,
    transcribe_bindings,
    validate_bindings,
)

__all__ = [
    "BindingLanguage", "bind_reference", "binding_from_document",
    "binding_to_document", "bindings_from_document", "bindings_to_document",
    "collect_bindings", "render_binding_source", "transcribe_binding_part",
    "transcribe_bindings", "validate_bindings",
]
