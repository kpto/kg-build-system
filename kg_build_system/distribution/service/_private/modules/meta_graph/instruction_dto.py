"""Meta-graph instruction data and its codec.

The DTOs are model data under :mod:`kg_build_system.distribution.model.internal`;
this module re-exports them with the target's private codec for existing
in-package callers.
"""
from __future__ import annotations

from .....model.internal.dto.meta_graph_instruction_dto import *  # noqa: F403
from .instruction_codec import *  # noqa: F403

__all__ = [
    "MetaGraphBindingDTO",
    "MetaGraphComponentDTO",
    "MetaGraphDocumentDTO",
    "MetaGraphEndpointDTO",
    "MetaGraphPropertyDTO",
    "decode_meta_graph_instruction",
    "encode_meta_graph_instruction",
]
