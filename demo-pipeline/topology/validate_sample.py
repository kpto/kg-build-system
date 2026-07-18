"""Validate and inspect the demonstration topology."""

import sys
from pathlib import Path
from runpy import run_path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from topology import Topology


def main() -> None:
    sample_path = Path(__file__).with_name("sample.py")
    declared_topology = run_path(sample_path)["TOPOLOGY"]
    topology = Topology.from_json(declared_topology.to_json())
    print(f"{topology.name}: {len(topology.nodes)} node types, {len(topology.edges)} edge type(s)")


if __name__ == "__main__":
    main()
