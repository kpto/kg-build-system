"""Render the standalone Neo4j bulk-import runner."""
from __future__ import annotations

from collections.abc import Sequence
from textwrap import dedent


def render_import_script(
    *,
    node_paths: Sequence[str],
    relationship_paths: Sequence[str],
    default_database: str,
) -> str:
    """Return a deterministic, standard-library-only import script."""
    nodes = repr(tuple(node_paths))
    relationships = repr(tuple(relationship_paths))
    database = repr(default_database)
    return dedent(f'''\
        #!/usr/bin/env python3
        """Import this bundle with a locally installed Neo4j admin tool."""
        from __future__ import annotations

        import argparse
        import os
        import shlex
        import shutil
        import subprocess
        from pathlib import Path


        NODE_FILES = {nodes}
        RELATIONSHIP_FILES = {relationships}
        DEFAULT_DATABASE = {database}


        def _admin_names() -> tuple[str, ...]:
            if os.name == "nt":
                return ("neo4j-admin.bat", "neo4j-admin.cmd", "neo4j-admin.exe")
            return ("neo4j-admin",)


        def _from_home(home: Path) -> list[Path]:
            return [home / "bin" / name for name in _admin_names()]


        def _known_locations() -> list[Path]:
            candidates: list[Path] = []
            if os.name == "nt":
                for variable in ("ProgramFiles", "ProgramFiles(x86)"):
                    root = os.environ.get(variable)
                    if not root:
                        continue
                    base = Path(root)
                    for pattern in (
                        "Neo4j*/bin/neo4j-admin*",
                        "Neo4j/Neo4j Server*/bin/neo4j-admin*",
                    ):
                        candidates.extend(base.glob(pattern))
                desktop_roots = (
                    Path.home() / ".Neo4jDesktop" / "relate-data" / "dbmss",
                    Path(os.environ.get("LOCALAPPDATA", ""))
                    / "Neo4j" / "Relate" / "Data" / "dbmss",
                )
                for root in desktop_roots:
                    if str(root):
                        candidates.extend(root.glob("dbms-*/bin/neo4j-admin*"))
            else:
                candidates.extend(
                    Path(value)
                    for value in (
                        "/opt/neo4j/bin/neo4j-admin",
                        "/usr/local/bin/neo4j-admin",
                        "/usr/bin/neo4j-admin",
                        "/opt/homebrew/bin/neo4j-admin",
                    )
                )
                desktop = (
                    Path.home() / "Library" / "Application Support"
                    / "Neo4j Desktop" / "Application" / "relate-data" / "dbmss"
                )
                candidates.extend(desktop.glob("dbms-*/bin/neo4j-admin"))
            return candidates


        def _usable(path: Path) -> bool:
            return path.is_file() and (os.name == "nt" or os.access(path, os.X_OK))


        def find_neo4j_admin(explicit: str | None, home: str | None) -> Path:
            checked: list[Path] = []
            if explicit:
                candidate = Path(explicit).expanduser()
                if _usable(candidate):
                    return candidate.resolve()
                raise FileNotFoundError(f"Neo4j admin executable is not usable: {{candidate}}")

            env_admin = os.environ.get("NEO4J_ADMIN")
            if env_admin:
                candidate = Path(env_admin).expanduser()
                checked.append(candidate)
                if _usable(candidate):
                    return candidate.resolve()

            selected_home = home or os.environ.get("NEO4J_HOME")
            if selected_home:
                for candidate in _from_home(Path(selected_home).expanduser()):
                    checked.append(candidate)
                    if _usable(candidate):
                        return candidate.resolve()

            located = shutil.which("neo4j-admin")
            if located:
                return Path(located).resolve()

            for candidate in _known_locations():
                checked.append(candidate)
                if _usable(candidate):
                    return candidate.resolve()

            locations = "\\n".join(f"  - {{item}}" for item in checked)
            raise FileNotFoundError(
                "Could not find neo4j-admin. Set NEO4J_HOME, NEO4J_ADMIN, "
                "or pass --neo4j-admin. Checked:\\n" + (locations or "  - PATH")
            )


        def _display(command: list[str]) -> str:
            return subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)


        def main(argv: list[str] | None = None) -> int:
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument("database", nargs="?", default=DEFAULT_DATABASE)
            parser.add_argument("--neo4j-admin")
            parser.add_argument("--neo4j-home")
            parser.add_argument("--dry-run", action="store_true")
            parser.add_argument("--print-command", action="store_true")
            parser.add_argument("--verbose", action="store_true")
            parser.add_argument(
                "--admin-arg", action="append", default=[],
                help="Additional argument passed verbatim to neo4j-admin; repeat as needed.",
            )
            args = parser.parse_args(argv)

            bundle = Path(__file__).resolve().parent
            node_files = [bundle / value for value in NODE_FILES]
            relationship_files = [bundle / value for value in RELATIONSHIP_FILES]
            missing = [path for path in (*node_files, *relationship_files) if not path.is_file()]
            if missing:
                parser.error("missing import files: " + ", ".join(str(path) for path in missing))
            if not node_files:
                parser.error("the import bundle contains no node files")

            admin = find_neo4j_admin(args.neo4j_admin, args.neo4j_home)
            command = [
                str(admin), "database", "import", "full", args.database,
                "--input-type=parquet", "--id-type=string",
            ]
            if args.dry_run:
                command.append("--dry-run=true")
            if args.verbose:
                command.append("--verbose")
            command.extend(f"--nodes={{path}}" for path in node_files)
            command.extend(f"--relationships={{path}}" for path in relationship_files)
            command.extend(args.admin_arg)

            print(_display(command))
            if args.print_command:
                return 0
            return subprocess.run(command, check=False).returncode


        if __name__ == "__main__":
            raise SystemExit(main())
        ''')


__all__ = ["render_import_script"]
