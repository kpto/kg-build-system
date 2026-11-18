"""The guide command prints the framework philosophy."""
from __future__ import annotations

from kg_build_system.cli import main


def test_guide_prints_the_philosophy(capsys) -> None:
    assert main(["guide"]) == 0
    out = capsys.readouterr().out
    assert "philosophy of kg-build-system" in out
    assert "One component, one responsibility, one name" in out
    assert "side-car scripts" in out
