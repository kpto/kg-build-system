"""The project's composition: its blueprint and workflow.

The values are declarations. `kbs blueprint`, `kbs workflow` and `kbs run` read
them and perform the requested step; importing this module builds nothing.

Python remains available as an option:

```python
from kg_build_system import compile, create_blueprint, execute

from project.manifest import blueprint, workflow

plan = compile(
    blueprint=create_blueprint(namespace_path=blueprint.namespace_path),
    planners=workflow.planners,
)
execute(plan, output_directory=workflow.output_directory)
```
"""

from pathlib import Path

from kg_build_system import Blueprint, Workflow
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
)

ROOT = Path(__file__).parent

blueprint = Blueprint(namespace_path=ROOT)

workflow = Workflow(
    blueprint=blueprint,
    planners=(
        DeduplicationPlanner(),
        FilePlanner(FileConfiguration("graph.jsonl")),
        MetaGraphPlanner(),
    ),
    output_directory=ROOT.parent / "build",
)
