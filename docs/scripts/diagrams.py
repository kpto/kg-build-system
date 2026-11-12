#!/usr/bin/env python3
"""Render the field-guide plates as static SVG.

The plates are deliberately light-only: in the site they read as printed
figures on a paper page, in both light and dark themes.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT.parent
OUT = ROOT / "content" / "_assets"

PAPER = "#fbf8f1"
INK = "#1d232a"
MUTED = "#5f6b76"
RULE = "#ded6c7"
GRID = "#eee7d8"

C = {
    "asset": "#4d7c4a",
    "table": "#2f67a8",
    "projection": "#a64d6b",
    "node": "#a47813",
    "edge": "#b36716",
    "property": "#6d4b9b",
    "binding": "#b4532a",
    "semantics": "#0f6f68",
    "step": "#7a5a3a",
    "plan": "#2454a6",
    "report": "#5c5c66",
    "accent": "#b4431f",
    "quality": "#8a5a00",
}
def tint(color: str) -> str:
    return color + "14"


class Plate:
    def __init__(self, width: int, height: int, title: str, desc: str):
        self.width = width
        self.height = height
        self.title = title
        self.desc = desc
        self.parts: list[str] = []

    def add(self, value: str) -> None:
        self.parts.append(value)

    def rect(self, x, y, w, h, fill="none", stroke=RULE, rx=8, width=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"{d}/>'
        )

    def text(self, x, y, value, size=14, fill=INK, anchor="start", weight=400, mono=False):
        family = "ui-monospace, SFMono-Regular, Menlo, monospace" if mono else "Inter, Segoe UI, sans-serif"
        self.add(
            f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{escape(value)}</text>'
        )

    def lines(self, x, y, values, size=13, fill=INK, gap=18, anchor="start", weight=400):
        for index, value in enumerate(values):
            self.text(x, y + index * gap, value, size=size, fill=fill, anchor=anchor, weight=weight)

    def arrow(self, x1, y1, x2, y2, color=C["accent"], dash=None, width=1.6, curve=0):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        if curve:
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2 + curve
            path = f"M {x1} {y1} Q {mx} {my} {x2} {y2}"
        else:
            path = f"M {x1} {y1} L {x2} {y2}"
        self.add(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}"{d} '
            f'marker-end="url(#arrow-{color.lstrip("#")})"/>'
        )

    def pill(self, x, y, label, color, width=None, size=12):
        w = width or (len(label) * size * 0.62 + 18)
        self.rect(x, y, w, 24, fill=tint(color), stroke=color + "55", rx=12)
        self.text(x + w / 2, y + 16, label, size=size, fill=color, anchor="middle", weight=600)
        return w

    def card(self, x, y, w, h, title, body, color, kicker=None):
        self.rect(x, y, w, h, fill="#ffffff", stroke=RULE, rx=10)
        self.rect(x, y, w, 4, fill=color, stroke=color, rx=2)
        if kicker:
            self.text(x + 14, y + 24, kicker.upper(), size=10, fill=color, weight=700)
        self.text(x + 14, y + (42 if kicker else 32), title, size=15, fill=INK, weight=700)
        self.lines(x + 14, y + (66 if kicker else 56), body, size=11.5, fill=MUTED, gap=16)

    def render(self) -> str:
        defs = "".join(
            f'<marker id="arrow-{color.lstrip("#")}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
            for color in set(C.values())
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}" '
            f'role="img" aria-labelledby="title desc">\n'
            f"<title id=\"title\">{escape(self.title)}</title>\n"
            f"<desc id=\"desc\">{escape(self.desc)}</desc>\n"
            f"<defs>{defs}</defs>\n"
            f'<rect width="{self.width}" height="{self.height}" fill="{PAPER}"/>\n'
            + "\n".join(self.parts)
            + "\n</svg>\n"
        )


def frame(plate: Plate, kicker: str) -> None:
    plate.text(38, 44, kicker.upper(), size=11, fill=C["accent"], weight=700)
    plate.text(38, 72, plate.title, size=24, fill=INK, weight=700)
    plate.rect(38, 88, plate.width - 76, 1, fill=RULE, stroke=RULE, rx=0)


def system() -> Plate:
    p = Plate(1200, 660, "One build, end to end", "Declarations become a blueprint, a plan and published records.")
    frame(p, "system map")

    # edit-time lane
    p.rect(38, 108, 1124, 78, fill="#f4f0e6", stroke=RULE, dash="5 4")
    p.text(54, 132, "EDIT TIME", size=10, fill=MUTED, weight=700)
    p.text(54, 156, "asset contract", size=13, fill=INK, weight=700)
    p.text(170, 156, "→  provider observes source  →  generated package", size=13, fill=MUTED)
    p.pill(940, 128, "never imported by build", C["semantics"], width=180, size=11)

    stages = [
        (38, "DECLARE", C["asset"], ["assets · data · topology", "binding · graph · semantics"]),
        (244, "LINK", C["table"], ["namespace → declarations", "→ symbols → model"]),
        (450, "BLUEPRINT", C["property"], ["graph · data · assets", "bindings · graph declaration"]),
        (656, "PLAN", C["plan"], ["components · steps", "openings · connections"]),
        (862, "EXECUTE", C["binding"], ["runtime · resources", "exact-kind executors"]),
    ]
    for x, title, color, body in stages:
        p.card(x, 214, 160, 120, title, body, color, kicker="stage")
    x = 1046
    p.rect(x, 214, 116, 120, fill="#ffffff", stroke=RULE, rx=10)
    p.rect(x, 214, 116, 4, fill=C["report"], stroke=C["report"], rx=2)
    p.text(x + 12, 238, "PUBLISH", size=11, fill=C["report"], weight=700)
    p.lines(x + 12, 262, ["graph.jsonl", "meta-graph", "Neo4j", "report"], size=11, gap=16)

    for x in (198, 404, 610, 816, 1022):
        p.arrow(x, 274, x + 44, 274, color=C["accent"])

    # boundaries
    p.rect(38, 360, 760, 54, fill="#ffffff", stroke=C["table"] + "66", rx=8)
    p.text(54, 382, "KERNEL", size=10, fill=C["table"], weight=700)
    p.text(54, 401, "build · compile · execute mechanics; no graph vocabulary", size=12, fill=MUTED)
    p.rect(814, 360, 348, 54, fill="#ffffff", stroke=C["asset"] + "66", rx=8)
    p.text(830, 382, "DISTRIBUTION", size=10, fill=C["asset"], weight=700)
    p.text(830, 401, "languages · blueprint · modules · targets", size=12, fill=MUTED)

    # artifacts strip
    p.text(38, 454, "THREE VERBS", size=10, fill=MUTED, weight=700)
    verbs = [
        (38, "build", "namespace → linked model", C["table"]),
        (390, "compile", "model → WorkflowPlan", C["plan"]),
        (742, "execute", "plan → WorkflowReport", C["binding"]),
    ]
    for x, name, body, color in verbs:
        p.rect(x, 468, 330, 54, fill="#ffffff", stroke=RULE, rx=8)
        p.text(x + 14, 490, name, size=15, fill=color, weight=700, mono=True)
        p.text(x + 92, 490, body, size=12, fill=MUTED)
    p.arrow(368, 495, 388, 495)
    p.arrow(720, 495, 740, 495)

    p.text(38, 566, "A plan records the source blueprint under provenance; a report records publications and failures.", size=12, fill=MUTED)
    p.text(38, 590, "The same declarations produce the same plan. Source bytes are not part of the plan.", size=12, fill=MUTED)
    p.pill(38, 606, "build → link", C["table"], width=126)
    p.pill(172, 606, "compile → plan", C["plan"], width=126)
    p.pill(306, 606, "execute → records", C["binding"], width=150)
    return p


def authoring() -> Plate:
    p = Plate(1200, 640, "The authoring model", "Seven objects, one direction: source, value, grain, meaning, mapping.")
    frame(p, "authoring map")

    p.card(38, 116, 200, 128, "Asset", ["one logical source unit", "profile · layout · governance"], C["asset"], "source")
    p.card(278, 116, 220, 128, "Table[Asset] · Struct", ["row shape", "Field[T] · canonical types"], C["table"], "rows")
    p.card(538, 116, 200, 128, "Selection[T]", ["one typed value", "owner decides absence"], C["table"], "value")
    p.card(778, 116, 180, 128, "RowSource", ["shape + plan", "where · join · group"], C["projection"], "grain")
    p.card(998, 116, 164, 128, "Projection", ["pinned named grain", "computed_field outputs"], C["projection"], "grain")
    p.arrow(238, 180, 274, 180)
    p.arrow(498, 180, 534, 180)
    p.arrow(738, 180, 774, 180)
    p.arrow(958, 180, 994, 180)

    p.card(538, 288, 200, 118, "Topology", ["Node · Edge · Property", "templates · categories"], C["node"], "meaning")
    p.card(778, 288, 180, 118, "Binding", ["rows + build key", "one record per row"], C["binding"], "mapping")
    p.card(998, 288, 164, 118, "Graph", ["≤ 1 declaration", "one purpose"], C["semantics"], "meaning")
    p.arrow(638, 244, 638, 284)
    p.arrow(738, 347, 774, 347)
    p.arrow(958, 347, 994, 347)

    p.rect(38, 288, 460, 118, fill="#ffffff", stroke=RULE, rx=10)
    p.text(52, 312, "SEMANTICS", size=10, fill=C["semantics"], weight=700)
    p.text(52, 336, "claims · frames · limitations · purpose", size=13, fill=INK, weight=600)
    p.lines(52, 360, ["attaches to any declaration as a fragment", "the Graph declaration owns the project purpose"], size=11.5, fill=MUTED)
    p.arrow(498, 347, 534, 347, color=C["semantics"], dash="4 3")
    p.arrow(498, 330, 998, 330, color=C["semantics"], dash="4 3", curve=-30)
    p.text(620, 322, "attaches", size=10, fill=C["semantics"])

    p.text(38, 452, "HOW THE PIECES READ", size=10, fill=MUTED, weight=700)
    rows = [
        ("Table[Asset]", "names the asset; the relation carries an AssetRef", C["table"]),
        ("Selection", "reads a field, computes a value, or navigates a record", C["table"]),
        ("RowSource", "decides what one row means; a projection pins one grain", C["projection"]),
        ("Topology", "states the node and edge types without importing a table", C["node"]),
        ("Binding", "imports both sides; supplies key, properties and endpoints", C["binding"]),
    ]
    for i, (name, body, color) in enumerate(rows):
        y = 468 + i * 28
        p.text(38, y, name, size=12, fill=color, weight=700, mono=True)
        p.text(180, y, body, size=12, fill=MUTED)

    p.rect(748, 452, 414, 130, fill="#ffffff", stroke=RULE, rx=10)
    p.text(762, 476, "THE GUARD", size=10, fill=C["accent"], weight=700)
    p.lines(762, 500, [
        "A field declares a value type, never absence.",
        "A binding takes a row-source value, never a class.",
        "A row effect is one shot; a second needs a second handle.",
        "A projection is pinned; its outputs share one row plan.",
    ], size=11.5, fill=MUTED, gap=19)
    return p


def nullability() -> Plate:
    p = Plate(1120, 640, "Where absence comes from", "The owner decides; the field annotation never writes it.")
    frame(p, "nullability")

    p.rect(360, 110, 400, 52, fill="#ffffff", stroke=RULE, rx=26)
    p.text(560, 142, "Where is the value supplied?", size=15, fill=INK, anchor="middle", weight=700)
    p.arrow(470, 162, 300, 210)
    p.arrow(650, 162, 820, 210)

    p.card(120, 210, 340, 118, "Source read", ["Table or source Struct", "Field[T] → Selection[Nullable[T]]"], C["table"], "owner: source")
    p.card(660, 210, 340, 118, "Computed read", ["Projection or ComputedStruct", "follows the computed_field selection"], C["projection"], "owner: computed")

    p.text(560, 300, "Absence is a fact about the owner, not the declared type.", size=12, fill=MUTED, anchor="middle")
    p.arrow(560, 316, 560, 356)

    p.rect(360, 356, 400, 44, fill=tint(C["accent"]), stroke=C["accent"] + "55", rx=8)
    p.text(560, 384, "What must happen to the row?", size=14, fill=C["accent"], anchor="middle", weight=700)
    options = [
        (38, 432, "keep the row", "default_to(value)", C["table"]),
        (300, 432, "drop the row", "alter_rows().drop_null()", C["binding"]),
        (562, 432, "one row per item", "alter_rows().expand()", C["projection"]),
        (824, 432, "conditional row", "drop_if(predicate)", C["quality"]),
    ]
    for x, y, title, code, color in options:
        p.rect(x, y, 244, 106, fill="#ffffff", stroke=RULE, rx=10)
        p.rect(x, y, 244, 4, fill=color, stroke=color, rx=2)
        p.text(x + 14, y + 32, title, size=13, fill=INK, weight=700)
        p.text(x + 14, y + 58, code, size=10.5, fill=color, mono=True)
        p.lines(x + 14, y + 82, ["a present value" if color == C["table"] else "an explicit row decision"], size=11, fill=MUTED)
    for x in (282, 544, 806):
        p.arrow(x, 485, x + 16, 485)

    p.rect(38, 566, 1044, 50, fill="#ffffff", stroke=RULE, rx=8)
    p.text(52, 590, "Field[T] never declares T | None.", size=12, fill=INK, weight=700)
    p.text(52, 608, "Item absence stays in the value: Array[Nullable[T]]. Nested owner absence is refused.", size=11.5, fill=MUTED)
    p.pill(850, 578, "one-shot handle", C["binding"], width=150, size=11)
    return p


def grain() -> Plate:
    p = Plate(1200, 540, "One row, then one record", "A row source is a value; a projection pins the grain a binding reads.")
    frame(p, "grain")

    steps = [
        (38, "scan", "Table.row_source()", "one row per source row", C["table"]),
        (228, "where", "Filter", "removes rows", C["table"]),
        (418, "join", "Join", "combines two grains", C["projection"]),
        (608, "group_by", "GroupBy", "one row per key", C["projection"]),
        (798, "distinct", "Distinct", "removes duplicates", C["quality"]),
        (988, "order_by", "OrderBy", "order only", C["quality"]),
    ]
    for x, name, dto, effect, color in steps:
        p.rect(x, 120, 160, 112, fill="#ffffff", stroke=RULE, rx=10)
        p.text(x + 14, 146, name, size=14, fill=color, weight=700, mono=True)
        p.text(x + 14, 170, dto, size=11, fill=INK, mono=True)
        p.text(x + 14, 198, effect, size=11, fill=MUTED)
    for x in (198, 388, 578, 768, 958):
        p.arrow(x, 176, x + 24, 176)

    p.rect(228, 270, 540, 58, fill=tint(C["projection"]), stroke=C["projection"] + "66", rx=8)
    p.text(244, 294, "union", size=13, fill=C["projection"], weight=700, mono=True)
    p.text(300, 294, "stacks rows; shapes must match", size=12, fill=MUTED)
    p.rect(798, 270, 350, 58, fill=tint(C["projection"]), stroke=C["projection"] + "66", rx=8)
    p.text(814, 294, "unnest", size=13, fill=C["projection"], weight=700, mono=True)
    p.text(884, 294, "one row per array item", size=12, fill=MUTED)

    p.card(38, 360, 300, 112, "Projection", ["pin exactly one row source", "computed_field names each output"], C["projection"], "name the grain")
    p.card(378, 360, 300, 112, "Binding", ["reads a row-source value", "one record per row"], C["binding"], "use the grain")
    p.card(718, 360, 430, 112, "Rule of thumb", ["If a record needs a different grain,", "make a projection; do not fan out inside a binding."], C["accent"], "decide once")
    p.arrow(338, 416, 374, 416)
    p.arrow(678, 416, 714, 416)

    p.text(38, 508, "lookup returns a nullable array and does not change the grain; compose the grain with drop_null() or expand().", size=11.5, fill=MUTED)
    return p


def lifecycle() -> Plate:
    p = Plate(1200, 600, "One run", "The runtime opens resources, dispatches exact kinds and closes the run.")
    frame(p, "execution")

    lanes = [("RUNTIME", 38), ("PROVIDERS", 260), ("EXECUTOR", 520), ("EVENT BUS", 800)]
    for label, x in lanes:
        p.text(x, 120, label, size=10, fill=MUTED, weight=700)
        p.rect(x, 130, 1, 360, fill=GRID, stroke=GRID, rx=0)

    events = [
        (154, "PipelineStarted", "fresh EventBus + ResourceRegistry", C["plan"]),
        (208, "open resources", "output · working · temp · DuckDB", C["asset"]),
        (262, "StepStarted", "dependency wave", C["step"]),
        (316, "execute(instruction)", "exact (operation, engine) kind", C["binding"]),
        (370, "StepFinished", "succeeded · warning · failed · skipped", C["quality"]),
        (424, "PipelineFinished", "publish report; dispose resources", C["report"]),
    ]
    for y, name, body, color in events:
        p.rect(38, y - 18, 1124, 38, fill="#ffffff", stroke=RULE, rx=6)
        p.text(54, y + 5, name, size=12, fill=color, weight=700, mono=True)
        p.text(240, y + 5, body, size=11.5, fill=MUTED)
    p.rect(38, 424 - 18, 1124, 38, fill=tint(C["report"]), stroke=C["report"] + "55", rx=6)
    p.text(54, 429, "PipelineFinished", size=12, fill=C["report"], weight=700, mono=True)
    p.text(240, 429, "publish report; dispose resources", size=11.5, fill=MUTED)

    p.rect(38, 466, 548, 100, fill="#ffffff", stroke=RULE, rx=10)
    p.text(52, 490, "FAILURE", size=10, fill=C["accent"], weight=700)
    p.lines(52, 512, [
        "A failed step becomes a FAILED outcome, not an exception.",
        "A disrupting input skips the step; a listener error halts the run.",
    ], size=11.5, fill=MUTED, gap=17)
    p.rect(614, 466, 548, 100, fill="#ffffff", stroke=RULE, rx=10)
    p.text(628, 490, "RESOURCES", size=10, fill=C["semantics"], weight=700)
    p.lines(628, 512, [
        "A provider publishes on PipelineStarted and disposes on finish or halt.",
        "An executor sees only the exact resources it declared.",
    ], size=11.5, fill=MUTED, gap=17)
    return p


def architecture() -> Plate:
    p = Plate(1200, 640, "The dependency spine", "The kernel knows no graph; the distribution points inward.")
    frame(p, "architecture")

    # kernel
    p.rect(38, 116, 250, 330, fill="#ffffff", stroke=C["table"] + "66", rx=12)
    p.text(54, 142, "KERNEL", size=10, fill=C["table"], weight=700)
    p.text(54, 164, "domain-agnostic toolchain", size=12, fill=MUTED)
    for i, (name, body) in enumerate([
        ("types", "canonical ontology"),
        ("language", "discover · key · transcribe"),
        ("linker", "roots · closure · model"),
        ("workflow", "plan · step · kind"),
        ("runtime", "events · resources · report"),
    ]):
        y = 188 + i * 48
        p.text(54, y, name, size=12.5, fill=INK, weight=700, mono=True)
        p.text(132, y, body, size=10.5, fill=MUTED)

    # languages
    p.rect(330, 116, 300, 196, fill="#ffffff", stroke=C["asset"] + "66", rx=12)
    p.text(346, 142, "LANGUAGES", size=10, fill=C["asset"], weight=700)
    p.text(346, 164, "authoring frontends", size=12, fill=MUTED)
    p.lines(346, 190, [
        "annotations · expressions",
        "asset · data · topology",
        "binding · graph · semantics",
        "each: discover → transcribe",
        "one declaration → one symbol",
    ], size=11, fill=MUTED, gap=18)

    # interpreter
    p.rect(672, 116, 220, 130, fill="#ffffff", stroke=C["property"] + "66", rx=12)
    p.text(688, 142, "INTERPRETER", size=10, fill=C["property"], weight=700)
    p.lines(688, 168, ["link the six languages", "assemble the blueprint", "validate; render source"], size=11, fill=MUTED, gap=18)

    # modules
    p.rect(672, 270, 220, 176, fill="#ffffff", stroke=C["binding"] + "66", rx=12)
    p.text(688, 296, "MODULES", size=10, fill=C["binding"], weight=700)
    p.lines(688, 322, ["core · duckdb", "dedup · merge · conflict", "file · meta-graph · neo4j", "python · runtime", "planner + executor + resources"], size=11, fill=MUTED, gap=18)

    # composition
    p.rect(934, 116, 228, 130, fill="#ffffff", stroke=C["accent"] + "66", rx=12)
    p.text(950, 142, "COMPOSITION", size=10, fill=C["accent"], weight=700)
    p.lines(950, 168, ["api.py", "default_toolchain", "create · compile · execute"], size=11, fill=MUTED, gap=18)
    p.rect(934, 270, 228, 90, fill="#ffffff", stroke=C["semantics"] + "66", rx=12)
    p.text(950, 296, "GENERATION", size=10, fill=C["semantics"], weight=700)
    p.lines(950, 322, ["edit-time frontend", "never imported by build"], size=11, fill=MUTED, gap=18)
    p.rect(934, 384, 228, 62, fill="#ffffff", stroke=C["report"] + "66", rx=12)
    p.text(950, 410, "CLI", size=10, fill=C["report"], weight=700)
    p.text(950, 432, "kbs generate --check", size=11, fill=MUTED, mono=True)

    # arrows
    p.arrow(288, 200, 326, 200, color=C["table"])
    p.arrow(630, 200, 668, 180, color=C["table"])
    p.arrow(630, 250, 668, 300, color=C["table"])
    p.arrow(892, 180, 930, 180, color=C["property"])
    p.arrow(892, 330, 930, 330, color=C["binding"])
    p.arrow(892, 350, 930, 350, color=C["binding"])
    p.arrow(288, 310, 668, 310, color=C["table"], dash="4 3", curve=40)
    p.arrow(934, 350, 892, 350, color=C["semantics"], dash="4 3")

    p.text(54, 486, "The kernel has no edge into the distribution.", size=12, fill=INK, weight=700)
    p.text(54, 508, "A new edge is a model change, proposed with its reason.", size=11.5, fill=MUTED)
    p.rect(38, 530, 1124, 78, fill="#ffffff", stroke=RULE, rx=10)
    p.text(52, 554, "ZONES", size=10, fill=C["accent"], weight=700)
    p.lines(52, 576, [
        "model/public · model/internal · model/_private    service/public · service/internal · service/_private",
        "A leaf keeps only the zones it uses. No package imports another package's _private zone.",
    ], size=11.5, fill=MUTED, gap=18)
    return p


def artifacts() -> Plate:
    p = Plate(1200, 520, "Three artifacts", "The blueprint is semantic, the plan is executable, the report is evidence.")
    frame(p, "artifacts")

    p.card(38, 116, 330, 210, "GraphBlueprint", [
        "semantic model of the graph",
        "graph · data · assets · bindings",
        "graph_declaration (0 or 1)",
        "typed refs: [language, role, *key]",
        "public handle; DTOs are internal",
    ], C["property"], "compile input")
    p.card(414, 116, 330, 210, "WorkflowPlan", [
        "components · steps · connections",
        "each step owns one instruction",
        "exact kind: (operation, engine)",
        "provenance carries the blueprint",
        "stored as workflow_plan.json",
    ], C["plan"], "compile output")
    p.card(790, 116, 372, 210, "WorkflowReport", [
        "published artifacts by opening",
        "recovered and unresolved failures",
        "provenance from the run",
        "stored as build_report.json",
        "succeeded is not 'all steps ok'",
    ], C["report"], "execute output")
    p.arrow(368, 220, 410, 220, color=C["accent"])
    p.arrow(744, 220, 786, 220, color=C["accent"])

    p.rect(38, 366, 1124, 72, fill="#ffffff", stroke=RULE, rx=10)
    p.text(52, 390, "THE CHAIN", size=10, fill=C["accent"], weight=700)
    chain = [
        ("declarations", C["asset"]),
        ("symbol graph (linker IR)", C["table"]),
        ("blueprint", C["property"]),
        ("plan", C["plan"]),
        ("report", C["report"]),
    ]
    x = 52
    for i, (label, color) in enumerate(chain):
        w = len(label) * 7 + 22
        p.pill(x, 400, label, color, width=w, size=10.5)
        x += w + 12
        if i < len(chain) - 1:
            p.arrow(x - 10, 412, x + 4, 412, color=C["accent"], width=1.2)
            x += 10

    p.lines(38, 474, [
        "Round trip: blueprint → rendered source → create_blueprint → equivalent blueprint (canonical document equality).",
        "Not promised: original text, module layout, callable bodies, or validity after a raw decode.",
    ], size=11.5, fill=MUTED, gap=18)
    return p


def modules() -> Plate:
    p = Plate(1200, 560, "Modules and exact kinds", "Each planner emits steps; each executor owns one exact instruction kind.")
    frame(p, "modules")

    stages = [
        (38, "SOURCE", C["asset"], ["duckdb planner", "source_relation/duckdb"]),
        (208, "ROWS", C["table"], ["core row_source", "sql/duckdb"]),
        (378, "PROJECT", C["projection"], ["core projection", "sql/duckdb"]),
        (548, "BIND", C["binding"], ["core binding", "sql/duckdb"]),
        (718, "RECORDS", C["quality"], ["core records", "aggregate/duckdb"]),
        (888, "QUALITY", C["quality"], ["dedup · merge", "conflict/duckdb"]),
        (1058, "TARGETS", C["report"], ["file · meta-graph", "neo4j/default"]),
    ]
    for x, name, color, body in stages:
        p.rect(x, 122, 150, 110, fill="#ffffff", stroke=RULE, rx=10)
        p.text(x + 12, 146, name, size=11, fill=color, weight=700)
        p.lines(x + 12, 170, body, size=10.5, fill=MUTED, gap=17)
    for x in (188, 358, 528, 698, 868, 1038):
        p.arrow(x, 176, x + 20, 176)

    p.rect(38, 270, 1124, 120, fill="#ffffff", stroke=RULE, rx=10)
    p.text(52, 294, "THE CONTRACT", size=10, fill=C["accent"], weight=700)
    p.lines(52, 318, [
        "A planner declares component_id, version and runtime_fields. Planners that share a component must agree on all three.",
        "A planner emits steps and connections by opening; compile assembles and refuses an unfed input, an unread output or a cycle.",
        "An executor declares kinds and resources. Execute refuses a duplicate kind and a plan kind no executor claims.",
        "A component that needs both planning and a side effect is two objects: one planner, one executor.",
    ], size=11.5, fill=MUTED, gap=20)

    p.rect(38, 414, 548, 106, fill="#ffffff", stroke=RULE, rx=10)
    p.text(52, 438, "DEFAULT COMPONENTS", size=10, fill=C["plan"], weight=700)
    p.lines(52, 462, ["duckdb · core · deduplication", "merging · conflict_validation", "file · meta_graph · neo4j"], size=11.5, fill=MUTED, gap=18)
    p.rect(614, 414, 548, 106, fill="#ffffff", stroke=RULE, rx=10)
    p.text(628, 438, "WHAT A TARGET OWNS", size=10, fill=C["report"], weight=700)
    p.lines(628, 462, ["the file it writes, not the plan shape", "its executor, its resources, its configuration", "a runtime field is replaceable at execute time"], size=11.5, fill=MUTED, gap=18)
    return p


def semantics() -> Plate:
    p = Plate(1200, 640, "One purpose, read downward", "The graph purpose is the root; topology, data and binding are read under it.")
    frame(p, "semantics")

    p.rect(350, 112, 500, 78, fill=tint(C["semantics"]), stroke=C["semantics"] + "66", rx=12)
    p.text(600, 138, "GRAPH PURPOSE", size=10, fill=C["semantics"], anchor="middle", weight=700)
    p.text(600, 160, "one per project · claims + purpose", size=13, fill=INK, anchor="middle", weight=600)
    p.text(600, 178, "the root every declaration fragment is read under", size=10.5, fill=MUTED, anchor="middle")

    cols = [
        (38, "TOPOLOGY", C["node"], "what the record is", ["category / template", "concrete node or edge", "property · direction"], "the design"),
        (430, "DATA", C["table"], "which rows supply it", ["asset", "table / projection", "field · selection · grain"], "implementation"),
        (822, "BINDING", C["binding"], "which row becomes which record", ["row source", "build key + properties", "endpoint tokens"], "the seam"),
    ]
    for x, title, color, question, levels, note in cols:
        p.rect(x, 246, 340, 252, fill="#ffffff", stroke=RULE, rx=12)
        p.rect(x, 246, 340, 5, fill=color, stroke=color, rx=2)
        p.text(x + 16, 272, title, size=11, fill=color, weight=700)
        p.text(x + 16, 294, question, size=13, fill=INK, weight=600)
        for i, level in enumerate(levels):
            y = 328 + i * 34
            p.rect(x + 16, y - 14, 308, 26, fill=tint(color), stroke="none", rx=5)
            p.text(x + 28, y + 4, level, size=11, fill=MUTED, mono=(i == 2))
        p.text(x + 16, 466, note, size=10.5, fill=color, weight=600)
        p.arrow(600, 192, x + 170, 242, color=C["semantics"], width=1.4)

    p.arrow(380, 372, 426, 372, color=C["accent"], dash="4 3", width=1.3)
    p.arrow(772, 372, 818, 372, color=C["accent"], dash="4 3", width=1.3)
    p.text(386, 362, "constrains", size=10, fill=C["accent"])
    p.text(778, 362, "meets", size=10, fill=C["accent"])

    p.rect(38, 526, 1124, 78, fill="#ffffff", stroke=RULE, rx=10)
    p.text(52, 550, "THE MECHANISM", size=10, fill=C["accent"], weight=700)
    p.lines(52, 572, [
        "The framework stores each attachment; it does not copy the parent text down.",
        "The author makes the lower statement consistent; the reviewer reads from purpose to plan.",
        "A limitation sits in the frame where it is true, not at the top as a disclaimer.",
    ], size=11, fill=MUTED, gap=17)
    p.pill(980, 544, "read down, not copy", C["semantics"], width=166, size=10.5)
    return p


def review_loop() -> Plate:
    p = Plate(1000, 430, "How a claim stays true", "A page is a dated claim with sources and generated evidence.")
    frame(p, "review")

    nodes = [
        (58, "Claim", "one page, one idea", C["accent"]),
        (258, "Sources", "1-5 paths at HEAD", C["table"]),
        (458, "Verify", "read the code, run the build", C["property"]),
        (658, "Date", "verified: YYYY-MM-DD", C["semantics"]),
        (818, "Drift", "source commit after date", C["quality"]),
    ]
    for x, title, body, color in nodes:
        p.rect(x, 128, 150, 96, fill="#ffffff", stroke=RULE, rx=10)
        p.text(x + 14, 154, title, size=13, fill=color, weight=700)
        p.lines(x + 14, 178, body.split("\n"), size=10.5, fill=MUTED, gap=15)
    p.arrow(208, 176, 254, 176)
    p.arrow(408, 176, 454, 176)
    p.arrow(608, 176, 654, 176)
    p.arrow(808, 176, 814, 176)
    p.arrow(888, 228, 888, 292, color=C["accent"])
    p.arrow(888, 292, 128, 292, color=C["accent"])
    p.arrow(128, 292, 128, 228, color=C["accent"])
    p.text(508, 310, "a drifted page returns to the queue", size=11, fill=MUTED, anchor="middle")

    p.lines(58, 356, [
        "Generation rewrites only the evidence block; the claim and its sources stay authored.",
        "A generated block that no marker owns is an error; an empty block is an error.",
    ], size=11.5, fill=MUTED, gap=18)
    return p


PLATES = {
    "system.svg": system,
    "authoring.svg": authoring,
    "nullability.svg": nullability,
    "grain.svg": grain,
    "lifecycle.svg": lifecycle,
    "architecture.svg": architecture,
    "artifacts.svg": artifacts,
    "modules.svg": modules,
    "review-loop.svg": review_loop,
    "semantics.svg": semantics,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, factory in PLATES.items():
        (OUT / name).write_text(factory().render(), encoding="utf-8")
    print(f"rendered {len(PLATES)} plates to {OUT.relative_to(SOURCE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
