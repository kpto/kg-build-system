"""The project's composition: its blueprint and workflow.

The values are declarations. `kbs blueprint`, `kbs workflow` and `kbs run` read
them and perform the requested step; importing this module builds nothing.

Python remains available as an option:

```python
from kg_build_system import compile, create_blueprint, execute

from project.manifest import blueprint, workflow

plan = compile(
    blueprint=create_blueprint(
        namespace_path=blueprint.namespace_path,
        languages=blueprint.languages,
    ),
    toolchain=workflow.toolchain,
)
execute(plan, output_directory=workflow.output_directory)
```
"""

from pathlib import Path

from kg_build_system import (
    DEFAULT_OPERATIONS,
    Blueprint,
    Workflow,
    default_languages,
    default_toolchain,
)
from kg_build_system.distribution import (
    DeduplicationPlanner,
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
    ExpressionsLanguage,
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
)

# The fixture's optional extension example. Remove this import and the matching
# composition below when the project removes expression/hello.py.
from project.expression.hello import HELLO
from project.modules.hello_emitter import HelloEmitter

ROOT = Path(__file__).parent

expressions = ExpressionsLanguage((*DEFAULT_OPERATIONS, HELLO))
languages = default_languages(expressions=expressions)

blueprint = Blueprint(namespace_path=ROOT, languages=languages)

engine = DuckDbSqlEmitter(
    instruction_emitter=DuckDbInstructionEmitter().with_operators(
        HelloEmitter(),
    ),
)

toolchain = default_toolchain(
    languages=languages,
    planners=(
        DeduplicationPlanner(),
        FilePlanner(FileConfiguration("graph.jsonl")),
        MetaGraphPlanner(),
    ),
    engine=engine,
)

workflow = Workflow(
    blueprint=blueprint,
    toolchain=toolchain,
    output_directory=ROOT.parent / "build",
)
