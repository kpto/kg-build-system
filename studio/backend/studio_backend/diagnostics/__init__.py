"""Pyright LSP diagnostics and IR mapping.

The tiers of the problem model are produced here: :mod:`.service` runs the type tier
over a real pyright language server, :mod:`.blueprint_errors` the framework-validation
tier, and :mod:`.mapping` turns a position or a message into an IR ref for either.
"""

from .blueprint_errors import map_blueprint_error
from .lsp import (
    LanguageServerClient,
    LspError,
    LspServerCrash,
    LspStartupError,
    LspTimeout,
)
from .mapping import Anchors, annotate, load_anchors, resolve
from .problem import Problem, make_problem, problem_id
from .service import DiagnosticsError, DiagnosticsService, write_pyright_config

__all__ = [
    "Anchors",
    "DiagnosticsError",
    "DiagnosticsService",
    "LanguageServerClient",
    "LspError",
    "LspServerCrash",
    "LspStartupError",
    "LspTimeout",
    "Problem",
    "annotate",
    "load_anchors",
    "make_problem",
    "map_blueprint_error",
    "problem_id",
    "resolve",
    "write_pyright_config",
]
