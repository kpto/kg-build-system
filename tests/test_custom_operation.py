from __future__ import annotations

import unittest

from sqlglot import exp

from kg_build_system import (
    DataSourceConfig, Field, InputFormat, Node, NodeOptions, NodeValues,
    PropertySlot, Table, TableOptions, bind_source, compile, field,
    node_binding, property,
)
from kg_build_system._frozen_json import thaw_json
from kg_build_system.compile import create_blueprint
from kg_build_system.engines.duckdb.operators.base import require_arity
from kg_build_system.engines.interfaces import DuckDBEngine
from kg_build_system.expressions.interfaces import ArgumentSpec, OperationSpec
from kg_build_system.expressions.operations._predicates import is_unit
from kg_build_system.modules import FileModule, FileModuleConfiguration, register_module
from kg_build_system.types import INT


DOUBLE = OperationSpec(
    name="double",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_unit("int")),),
    result_type=INT,
)


class Row(Table):
    options = TableOptions(name="row")
    id: Field[int] = field(name="id")


class NumberNode(Node):
    options = NodeOptions(name="number")
    value: PropertySlot[int] = property()


class DoubleLowerer:
    operator = "double"

    def lower(self, expression, operands, context):
        require_arity(expression, operands, 1, "double requires one argument")
        return exp.Mul(
            this=operands[0].sql(), expression=exp.Literal.number(2),
        )


def _binding():
    return node_binding(
        target=NumberNode,
        rows=Row,
        bind=lambda row: NodeValues(
            build_key=row.id,
            properties=NumberNode(value=DOUBLE.apply(row.id)),
        ),
    )


def _blueprint():
    source = bind_source(
        target=Row,
        config=DataSourceConfig("rows.json", format=InputFormat.JSON),
    )
    return create_blueprint(bindings=(_binding(),), sources=(source,), modules=())


class CustomOperationTests(unittest.TestCase):
    def test_a_custom_operation_reaches_the_engine_without_a_dispatcher_edit(self) -> None:
        engine = DuckDBEngine().with_operators(DoubleLowerer())
        contract = compile(
            blueprint=_blueprint(),
            modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            engine=engine,
        )
        sql = ""
        for contribution in contract.workflow.contributions:
            if contribution.reference.module_id != "core":
                continue
            instructions = thaw_json(contribution.variables)["instructions"]
            sql = instructions["binding.0"]["sql"]
        self.assertIn('"id" * 2', sql)

    def test_an_unregistered_operation_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not support"):
            compile(
                blueprint=_blueprint(),
                modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            )


if __name__ == "__main__":
    unittest.main()
