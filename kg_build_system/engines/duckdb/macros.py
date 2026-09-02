"""Framework SQL macros this engine expects on a build connection.

Lowered SQL references these by name, so the name and the statement that creates
it are kept here as one fact: a guard that renders a macro nobody created is a
build failure at view-creation time, and this is the only place either is written.
"""

from __future__ import annotations

__all__ = ["NULL_GUARD_MACRO", "NULL_GUARD_MACRO_SQL"]

#: Aborts with ``msg`` when a value is null. Lowered bindings wrap every non-null
#: output in it, so a violated contract claim stops a build instead of emitting a
#: value the contract forbids.
NULL_GUARD_MACRO = "_kg_nn"

#: Idempotent and namespaced: macro names are database-scoped, and a disk build
#: opens a fresh database per run.
NULL_GUARD_MACRO_SQL = (
    f"CREATE OR REPLACE MACRO {NULL_GUARD_MACRO}(v, msg := 'unexpected NULL') AS "
    "CASE WHEN v IS NULL THEN error(msg) ELSE v END"
)
