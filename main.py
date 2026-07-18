"""Run the first MVP topology demonstration."""

import runpy
from pathlib import Path

def main():
    sample_path = Path("demo-pipeline/topology/sample.py")
    topology = runpy.run_path(sample_path)["TOPOLOGY"]
    print(topology.to_json())


if __name__ == "__main__":
    main()
