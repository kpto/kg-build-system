# Knowledge Graph Build System

An MVP declarative knowledge-graph builder. See `demo/basic.py` for an importable end-to-end declaration. Install dependencies with `uv sync`, then run `uv run python -m demo.basic`.

The public declaration API is statically typed: contracts use `Declaration[T]`, fields and properties retain their resolved type as `FieldPath[T]`/`Expression[T]`, and the two authoring contract bases use `dataclass_transform`. The package includes `py.typed`. Check the demo with `uv run pyright`; it is configured as the MVP's strict static-check success gate.
