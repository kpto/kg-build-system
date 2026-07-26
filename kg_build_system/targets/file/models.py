from dataclasses import dataclass

@dataclass(frozen=True)
class FileTarget:
    location: str
