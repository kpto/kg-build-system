"""The project's hello operation: a minimal expression extension.

The spec states the operator's identity, arity, argument and result types. The
handle is the typed authoring form, so both calls are valid:

    hello(row.item_label.default_to("Untitled item"))
    row.item_label.default_to("Untitled item").custom_op(hello)
"""

from kg_build_system import STR, Selection
from kg_build_system.distribution.languages.expressions import (
    ArgumentSpec,
    Operation,
    OperationSpec,
)

HELLO = OperationSpec(
    name="hello",
    arity=1,
    arguments=(ArgumentSpec(expected=STR),),
    result_type=STR,
)

hello: Operation[[Selection[str]], str] = Operation(HELLO)

__all__ = ["HELLO", "hello"]
