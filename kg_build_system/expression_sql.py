"""DuckDB SQL lowering for portable expression models."""
from typing import Any

from .expressions import Expression, FieldPath

def render_sql(value: Any, aliases: dict[type, str]) -> str:
    if isinstance(value, FieldPath):
        alias = aliases.get(value.table, value.table.__name__.lower())
        return alias + "." + ".".join('"' + part + '"' for part in value.path)
    if isinstance(value, Expression):
        if value.op == "literal": return render_sql(value.args[0], aliases)
        if value.op == "concat": return "concat(" + ", ".join(render_sql(arg, aliases) for arg in value.args) + ")"
        if value.op == "coalesce": return "coalesce(" + ", ".join(render_sql(arg, aliases) for arg in value.args) + ")"
        if value.op == "cast": return "CAST(" + render_sql(value.args[0], aliases) + " AS " + str(value.args[1]) + ")"
        if value.op == "uuid": return "md5(" + render_sql(value.args[0], aliases) + ")"
        if value.op == "expand": return "item"
        raise ValueError(f"Unsupported expression operation: {value.op}")
    if value is None: return "NULL"
    if isinstance(value, str): return "'" + value.replace("'", "''") + "'"
    if isinstance(value, bool): return "TRUE" if value else "FALSE"
    return str(value)
