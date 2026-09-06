"""The one problem shape every diagnostics tier produces.

``studio/docs/API.md`` §"Problem model" is the normative description of this
payload; this module is its only Python definition, so the types tier
(:mod:`studio_backend.diagnostics.service`), the blueprint tier
(:mod:`studio_backend.diagnostics.blueprint_errors`) and whatever the build tier
adopts later cannot drift apart in spelling.

Two deliberate choices worth stating:

``severity``
    The published enum is ``error | warning | info``. pyright's LSP severities
    are 1=error, 2=warning, 3=information and 4=hint; 4 is folded onto ``info``
    because the contract has no fourth value (the ``hint`` field carries the
    human guidance and must not be confused with that severity).

``ref_trusted``
    ``"anchor"`` means a real anchor range was hit, ``"name"`` means the ref came
    from a declaration-name lookup, and ``"file"`` means the whole-file owner
    entry was used (DESIGN.md §3: "a diagnostic with no anchor maps to its file's
    owner ref"). ``"file"`` therefore extends the enum sketched in API.md, which
    predates the fallback; ``null`` still means unmappable.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Iterator, Literal

Tier = Literal["types", "blueprint", "build", "document"]
Severity = Literal["error", "warning", "info"]
RefTrusted = Literal["anchor", "name", "file"]

#: Separator for the id digest: a byte that cannot appear in any component.
_ID_SEPARATOR = "\x1f"


def problem_id(tier: str, file: str | None, code: str | None, message: str) -> str:
    """The stable identity of a problem: sha1 over tier + file + code + message.

    Position is deliberately excluded, so re-running pyright after an edit that
    only moves a line keeps the same id and the UI can keep an open problem
    selected.
    """
    digest = hashlib.sha1()  # noqa: S324 - identity, not security
    for part in (tier, file or "", code or "", message):
        digest.update(part.encode("utf-8"))
        digest.update(_ID_SEPARATOR.encode("ascii"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class Problem(Mapping[str, Any]):
    """One diagnostic, already resolved onto the IR document.

    Attribute access is the interface inside Python; the class is also a
    ``Mapping`` over exactly the contract's keys, so a caller that treats problems as
    JSON objects (``dict(problem)``, ``problem["severity"]``,
    ``problem.get("ref")``) sees the API.md payload and nothing else. ``as_json()``
    is the same thing, spelled explicitly.
    """

    id: str
    tier: Tier
    severity: Severity
    message: str
    code: str | None
    file: str | None
    line: int | None
    column: int | None
    end_line: int | None
    end_column: int | None
    ref: str | None
    ref_trusted: RefTrusted | None
    hint: str | None

    def refilled(self, **changes: Any) -> Problem:
        """A copy with the given fields replaced; problems are otherwise frozen."""
        return replace(self, **changes)

    def as_json(self) -> dict[str, Any]:
        """The JSON object the frontend's ``Problem`` mirror is field-for-field."""
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def __iter__(self) -> Iterator[str]:
        return iter(PROBLEM_KEYS)

    def __len__(self) -> int:
        return len(PROBLEM_KEYS)


#: The contract's field order, derived from the class so it cannot drift from it.
PROBLEM_KEYS: tuple[str, ...] = tuple(field.name for field in fields(Problem))


def make_problem(
    *,
    tier: Tier,
    severity: Severity,
    message: str,
    code: str | None = None,
    file: str | None = None,
    line: int | None = None,
    column: int | None = None,
    end_line: int | None = None,
    end_column: int | None = None,
    ref: str | None = None,
    ref_trusted: RefTrusted | None = None,
    hint: str | None = None,
) -> Problem:
    """Build a problem, computing its id from the identity fields."""
    return Problem(
        id=problem_id(tier, file, code, message),
        tier=tier,
        severity=severity,
        message=message,
        code=code,
        file=file,
        line=line,
        column=column,
        end_line=end_line,
        end_column=end_column,
        ref=ref,
        ref_trusted=ref_trusted,
        hint=hint,
    )


#: LSP ``DiagnosticSeverity`` -> the contract's ``severity``. 4 (hint) is reported
#: as info because pyright uses it for "this is noise you can delete" and the UI
#: has no fourth band.
LSP_SEVERITIES: dict[int, Severity] = {
    1: "error",
    2: "warning",
    3: "info",
    4: "info",
}


def severity_from_lsp(value: int | None) -> Severity:
    """Map a published LSP severity number, defaulting to ``error``.

    Defaulting upward is correct: a server that omits the field is describing
    something the user has to deal with, not something they can ignore.
    """
    if value is None:
        return "error"
    return LSP_SEVERITIES.get(value, "error")
