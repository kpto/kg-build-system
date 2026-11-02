"""Author-facing data declarations, fields, sources and row-source values.

This package is the only surface a graph author needs for logical data. It
re-exports the declarations from the public modules and the reviewed helper
functions from the framework-internal interface.

Example:
    ```python
    from kg_build_system import (
        Field, Projection, Table, TableGroup, TableGroupOptions, field,
        computed_field, bind_source, DataSourceConfig, InputFormat,
    )

    class Site(Table):
        site_id: Field[str] = field()
        name: Field[str] = field()

    class SiteLabels(Projection(Site.row_source())):
        label = computed_field(Site.name)

    class Estate(TableGroup):
        options = TableGroupOptions(name="estate")
        sites = Site

    sources = bind_source(
        target=Estate,
        config=DataSourceConfig(
            location="data", layout="{group_path}/{table_name}.json",
        ),
    )
    ```
"""
from __future__ import annotations


from .declarations import (
    ComputedStruct, Projection, ProjectionOptions, Struct, StructOptions,
    StructOptionsTemplate, StructTemplate, Table, TableGroup, TableGroupOptions,
    TableOptions,
)
from .fields import Field, computed_field, field, projection_field
from .row_sources import (
    DerivedRowSource, RelationRowSource, RowSource,
)
from .shapes import ShapeField
from .sources import (
    BoundSource, BoundTable, BoundTableGroup, DataSourceConfig, InputFormat,
    SourceBindingOptions, bind_source,
)

__all__ = [
    "BoundSource",
    "BoundTable",
    "BoundTableGroup",
    "ComputedStruct",
    "DataSourceConfig",
    "DerivedRowSource",
    "Field",
    "InputFormat",
    "Projection",
    "ProjectionOptions",
    "RelationRowSource",
    "RowSource",
    "ShapeField",
    "SourceBindingOptions",
    "Struct",
    "StructOptions",
    "StructOptionsTemplate",
    "StructTemplate",
    "Table",
    "TableGroup",
    "TableGroupOptions",
    "TableOptions",
    "bind_source",
    "computed_field",
    "field",
    "projection_field",
]
