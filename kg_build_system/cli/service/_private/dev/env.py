"""Read the framework repository's developer-only .env."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

VIEWER_KEY = "KBS_DEV_VIEWER"
CONSOLE_KEY = "KBS_DEV_CONSOLE"
_KEYS = {VIEWER_KEY, CONSOLE_KEY}


@dataclass(frozen=True)
class DevConfig:
    """The two commands and the directory they run from."""

    path: Path
    cwd: Path
    commands: dict[str, str]

    def command(self, role: str) -> str:
        key = VIEWER_KEY if role == "viewer" else CONSOLE_KEY
        value = self.commands.get(key, "").strip()
        if not value:
            raise ValueError(
                f"{self.path} must define {key} to start the {role} dev server"
            )
        return value


def framework_root() -> Path:
    """The source checkout that contains the kg_build_system package."""

    return Path(__file__).resolve().parents[5]


def env_path() -> Path:
    return framework_root() / ".env"


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_dev_config(path: Path | None = None) -> DevConfig:
    """Load only KBS_DEV_VIEWER and KBS_DEV_CONSOLE from .env."""

    file = (path or env_path()).resolve()
    if not file.is_file():
        raise ValueError(
            f"dev mode requires {file}; it is the framework repo's untracked .env "
            "with KBS_DEV_VIEWER and KBS_DEV_CONSOLE"
        )
    commands: dict[str, str] = {}
    for number, raw in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{file}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in _KEYS:
            continue
        value = _unquote(value.strip())
        if not value:
            raise ValueError(f"{file}:{number}: {key} is empty")
        commands[key] = value
    return DevConfig(path=file, cwd=file.parent, commands=commands)
