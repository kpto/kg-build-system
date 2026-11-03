"""Meta-graph instruction data and its codec for this package."""
from __future__ import annotations

from ...model.internal.instruction_dto import (
    MetaGraphBindingDTO,
    MetaGraphComponentDTO,
    MetaGraphDocumentDTO,
    MetaGraphEndpointDTO,
    MetaGraphPropertyDTO,
)
from .instruction_codec import (
    decode_meta_graph_instruction,
    encode_meta_graph_instruction,
)

__all__ = [
    "MetaGraphBindingDTO",
    "MetaGraphComponentDTO",
    "MetaGraphDocumentDTO",
    "MetaGraphEndpointDTO",
    "MetaGraphPropertyDTO",
    "decode_meta_graph_instruction",
    "encode_meta_graph_instruction",
]
