# pyright: reportUnnecessaryTypeIgnoreComment=error
"""Project-local operation handles keep the authoring types precise."""
from __future__ import annotations

from typing import assert_type

from kg_build_system import Omitted
from kg_build_system.distribution.languages.data.model.public import (
    Field,
    SourceRelation,
)
from kg_build_system.distribution.languages.data.service.public import field
from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.distribution.languages.expressions.service.public import (
    ArgumentSpec,
    Operation,
    OperationSpec,
)
from kg_build_system.kernel import INT, STR, Nullable
from tests.distribution.support import TestEstate


class OperationRow(SourceRelation[TestEstate]):
    severity: Field[str] = field(name="severity", meaning=Omitted)


SEVERITY_RANK = OperationSpec(
    name="severity_rank",
    arity=1,
    arguments=(ArgumentSpec(expected=STR),),
    result_type=INT,
)
severity_rank: Operation[[Selection[str]], int] = Operation(SEVERITY_RANK)

present: Selection[str] = OperationRow.severity.alter_rows().drop_null()
nullable: Selection[Nullable[str]] = OperationRow.severity

assert_type(severity_rank(present), Selection[int])
assert_type(present.custom_op(severity_rank), Selection[int])
assert_type(present.apply(severity_rank), Selection[int])

# A nullable receiver cannot satisfy the handle's present-string parameter.
nullable.custom_op(severity_rank)  # pyright: ignore[reportArgumentType]
severity_rank(nullable)  # pyright: ignore[reportArgumentType]
