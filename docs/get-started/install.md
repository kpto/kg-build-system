# Install kg-build-system

Install kg-build-system into a Python 3.12 or newer environment and verify that the library and the `kbs` command are ready.

## Before you begin

- Install Python 3.12 or newer. The package declares `requires-python = ">=3.12"`.
- Have a checkout of the kg-build-system repository. This guide describes the API in that checkout.
- Have `pip` available in the environment, or use `uv`.
- No database server is required for the first build. The file output module writes JSON Lines.

!!! note "Use one environment"
    Install kg-build-system into the environment that runs your project. Keep the framework and the project's own dependencies together so `kbs` and `python` refer to the same installation.

## Steps

### 1. Check Python

Run:

```bash
python --version
```

You should see Python 3.12 or newer. If `python` is not on your PATH, use `python3` in the commands below.

### 2. Create and activate a virtual environment

From the directory where you keep your projects, run:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install the package

Install the checkout into the active environment:

```bash
python -m pip install /path/to/kg-build-system
```

Replace `/path/to/kg-build-system` with the real path to the checkout.

If you use `uv` with a project that has a `pyproject.toml`, add the checkout as an editable dependency instead:

```bash
uv add --editable /path/to/kg-build-system
```

If you use `uv`, run project commands through `uv run`; for example, `uv run python -m people_graph.build`.

The framework is experimental. Install the checkout that matches the guide you are reading; a different version may have a different API.

## Verify

Check that the public names import:

```bash
python -c "from kg_build_system import Table, compile, build; print('kg-build-system ready')"
```

You should see:

```text
kg-build-system ready
```

Check that the command-line tool is on the same PATH:

```bash
kbs --help
```

The output lists the `generate` command. The CLI creates and maintains generated data contracts; compilation and builds are calls from your Python entry point, not CLI commands.

!!! tip "Command not found?"
    If `python` or `kbs` is not found, activate the virtual environment again and repeat the check. Do not install a second copy into another environment.

## What to remember

- Use Python 3.12 or newer.
- Install the framework and your project into one environment.
- `kbs` is for generated contracts. Use `compile()` and `build()` in Python for a build.
- Verify the import and the CLI before you create a project.

## Next steps

- [Build your first graph](first-graph.md) for a complete walkthrough from CSV files to JSON Lines.
- [Project layout](project-layout.md) for where declarations, sources, bindings, and outputs live.
- [Data contracts](../concepts/data-contracts.md) for the table declarations the walkthrough uses.
- [Authoring API reference](../reference/index.md) for the names you can import from `kg_build_system`.
