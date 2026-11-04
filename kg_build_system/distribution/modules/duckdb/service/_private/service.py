"""The live DuckDB capability one workflow execution shares."""
from __future__ import annotations

from kg_build_system.distribution.service.internal.relations import (
    RelationService,
)

from .engine.session import EngineSession


class DuckDbService:
    """Own the engine session and the relation service over it.

    The relation service is a non-owning view: it is closed with the engine.

    Example:
    ```python
    from kg_build_system.distribution.modules.duckdb import DuckDbService

    service = DuckDbService(engine)
    service.close()
    ```
    """

    def __init__(self, engine: EngineSession) -> None:
        self._engine = engine

    @property
    def engine(self) -> EngineSession:
        """The opened engine session."""
        return self._engine

    @property
    def relations(self) -> RelationService:
        """The relation service backed by the engine."""
        return self._engine.relations

    def close(self) -> None:
        """Close the engine and its relation service.

        Example:
        ```python
        service.close()
        ```
        """
        self._engine.close()


__all__ = ["DuckDbService"]
