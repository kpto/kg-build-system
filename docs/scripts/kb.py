#!/usr/bin/env python3
"""Validate the field guide and regenerate its evidence blocks.

Usage:
    python3 scripts/kb.py check
    python3 scripts/kb.py generate
    python3 scripts/kb.py all
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml
from html import escape

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT.parent
CONTENT = ROOT / "content"
APPENDIX = CONTENT / "appendix"
CANDIDATES = ROOT / "research" / "decisions-candidates.md"

SECTIONS = {"book", "subjects", "spec", "start", "philosophy", "author", "pipeline", "operate", "review", "kernel", "framework", "developer", "reference", "meta"}
STATUSES = {"normative", "draft", "deprecated"}
PERSPECTIVES = {"book", "hub", "guide", "spec", "api", "philosophy", "review", "developer", "reference", "meta"}
HUB_REQUIRED = ["In one view", "Perspectives", "Contract", "Where it sits", "Next"]
SPEC_REQUIRED = ["Requirement", "Evidence", "API", "Limits", "Rationale", "Next"]
SUBJECTS_FILE = CONTENT / "subjects.yml"
SPEC_MAP_FILE = CONTENT / "spec-map.yml"
SPEC_ID = re.compile(r"^SPEC-\d{3}$")
SECTION_REQUIRED = {
    "start": ["What it is", "Rules", "Example", "Limits", "Next"],
    "philosophy": ["What it is", "Rules", "Example", "Limits", "Next"],
    "author": ["What it is", "Rules", "Example", "Limits", "Next"],
    "pipeline": ["What it is", "Rules", "Example", "Limits", "Next"],
    "operate": ["What it is", "Rules", "Example", "Limits", "Next"],
    "review": ["What it is", "Rules", "Evidence", "Limits", "Next"],
    "subjects": [],
    "spec": [],
    "book": ["Next"],
    "reference": ["Surface", "Details"],
    "meta": [],
}
INDEX_REQUIRED = ["In this section", "Pages", "Next"]
WORD_LIMITS = {"book": 4000, "subjects": 1000, "spec": 1000, "start": 750, "philosophy": 750, "author": 750, "pipeline": 750, "operate": 750, "review": 900, "kernel": 1200, "developer": 1800}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
MDLINK = re.compile(r"\[[^\]]*\]\(([^)#]+)(?:#[^)]+)?\)")
HREFLINK = re.compile(r'href="([^"]+)"')
DECISION_ROW = re.compile(
    r"^\|\s*(D-\d{3})\s*\|\s*(.+?)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$"
)
def parse_decision_row(line: str) -> tuple[str, str, str, str, str] | None:
    if not line.strip().startswith("|"):
        return None
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) < 6:
        return None
    did, decision, date, status = cells[:4]
    if not re.fullmatch(r"D-\d{3}", did):
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return None
    if status not in {"accepted", "proposed", "rejected", "superseded"}:
        return None
    return did, decision, date, status, cells[-1]


BLOCK = re.compile(
    r"<!-- BEGIN GENERATED:([a-z0-9-]+) -->\n?(.*?)\n?<!-- END GENERATED:\1 -->", re.S
)
KNOWN_BLOCKS = {"status", "status-strip", "api", "code-map", "decisions", "drift", "reference", "views"}
STALE_WORDS = ("currently", "recently", "TODO", "FIXME")


def split_front(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    try:
        meta = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as exc:
        meta = {"_yaml_error": str(exc)}
    return meta, text[end + 5 :]


def pages() -> list[tuple[Path, dict, str]]:
    out = []
    for path in sorted(CONTENT.rglob("*.md")):
        if "_assets" in path.parts:
            continue
        meta, body = split_front(path)
        out.append((path, meta, body))
    return out


def slug_of(path: Path) -> str:
    rel = path.relative_to(CONTENT).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "index":
        parts = parts[:-1]
    return "/".join(parts) or "index"


def is_index(path: Path) -> bool:
    return path.name == "index.md"


def known_decisions() -> set[str]:
    return set(re.findall(r"D-\d{3}", CANDIDATES.read_text(encoding="utf-8")))


def candidate_decisions() -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for line in CANDIDATES.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        did, decision, date, status = cells[:4]
        if not re.fullmatch(r"D-\d{3}", did):
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            continue
        found[did] = {
            "decision": decision,
            "date": date,
            "status": status,
            "evidence": cells[6],
        }
    return found


def resolve_link(page: Path, href: str) -> str | None:
    href = href.strip().split("#", 1)[0].split("?", 1)[0]
    if not href or href.startswith(("http://", "https://", "mailto:")):
        return None
    if href.startswith("/"):
        base = CONTENT / href.lstrip("/")
    else:
        base = page.parent / href
    candidates = [base]
    if base.suffix == "":
        candidates += [base.with_suffix(".md"), base / "index.md"]
    elif base.suffix == ".md":
        candidates += [base]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                return slug_of(candidate.resolve())
            except ValueError:
                return None
    return None


def resolve_wikilink(target: str) -> str | None:
    base = CONTENT / target.strip()
    candidates = [base]
    if base.suffix == "":
        candidates += [base.with_suffix(".md"), base / "index.md"]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                return slug_of(candidate.resolve())
            except ValueError:
                return None
    return None


def load_subjects() -> list[dict]:
    if not SUBJECTS_FILE.exists():
        return []
    return yaml.safe_load(SUBJECTS_FILE.read_text(encoding="utf-8")) or []


def subject_entry(subject: str | None) -> dict | None:
    for entry in load_subjects():
        if entry.get("slug") == subject:
            return entry
    return None


def title_of(slug: str) -> str:
    path = CONTENT / f"{slug}.md"
    if path.exists():
        meta, _ = split_front(path)
        return str(meta.get("title", slug))
    return slug


def views_html(entry: dict, current: str, perspective: str | None = None) -> str:
    subject = str(entry["slug"])
    guides = [str(p) for p in entry.get("guide", [])]
    philosophy = [str(p) for p in entry.get("philosophy", [])]
    review = [str(p) for p in entry.get("review", [])]
    api = str(entry.get("api", "appendix/reference/api"))
    guide = guides[0] if guides else None
    items = [
        ("Overview", f"/appendix/subjects/{subject}", perspective == "hub" or current == f"appendix/subjects/{subject}"),
        ("Guide", f"/{guide}" if guide else "", perspective == "guide"),
        ("Spec", f"/appendix/spec/{subject}", perspective == "spec"),
        ("API", f"/{api}", perspective == "api"),
        ("Philosophy", f"/{philosophy[0]}" if philosophy else "", perspective == "philosophy"),
        ("Review", f"/{review[0]}" if review else "", perspective == "review"),
    ]
    links = []
    for label, href, active in items:
        if not href:
            continue
        klass = ' class="active"' if active else ""
        links.append(f'<a href="{escape(href)}"{klass}>{escape(label)}</a>')
    return (
        '<div class="kb-views">'
        f'<span class="kb-views-subject">{escape(str(entry.get("title", subject)))}</span>'
        + "".join(links)
        + "</div>"
    )


def spec_count(body: str) -> int:
    return len(re.findall(r"\*\*R-?\d+", body))


def hub_body(entry: dict, spec_meta: dict) -> str:
    subject = str(entry["slug"])
    guides = [str(p) for p in entry.get("guide", [])]
    philosophy = [str(p) for p in entry.get("philosophy", [])]
    review = [str(p) for p in entry.get("review", [])]
    api = str(entry.get("api", "appendix/reference/api"))
    guide_links = ", ".join(f"[{title_of(p)}](/{p})" for p in guides) or "—"
    philosophy_links = ", ".join(f"[{title_of(p)}](/{p})" for p in philosophy) or "—"
    review_links = ", ".join(f"[{title_of(p)}](/{p})" for p in review) or "—"
    upstream = [str(p) for p in entry.get("upstream", [])]
    downstream = [str(p) for p in entry.get("downstream", [])]
    up = ", ".join(f"[{title_of(p)}](/appendix/subjects/{p})" for p in upstream) or "Top of the dependency story"
    down = ", ".join(f"[{title_of(p)}](/appendix/subjects/{p})" for p in downstream) or "End of the dependency story"
    next_slug = entry.get("next")
    if next_slug:
        nxt = f"[{title_of(str(next_slug))}](/subjects/{next_slug}) — the next subject in the chain."
    else:
        nxt = "[Specifications](/appendix/spec/index) — the normative index."
    contract = "\n".join(f"- {item}" for item in entry.get("contract", []))
    return f"""<!-- BEGIN GENERATED:views -->
{views_html(entry, f"appendix/subjects/{subject}", "hub")}
<!-- END GENERATED:views -->

## In one view

{entry["summary"]}

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/{subject}) | The subject in one place. |
| Guide | {guide_links} | How to use it. |
| Spec | [{entry["spec"]}](/appendix/spec/{subject}) | Binding requirements, API and evidence. |
| API | [API surface](/{api}) | Exact public names and document shapes. |
| Philosophy | {philosophy_links} | Why it is designed this way. |
| Review | {review_links} | Invariants, limits and measured evidence. |

## Contract

{contract}

## Where it sits

Upstream: {up}. Downstream: {down}.

## Next

{nxt}
"""


def write_generated(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n" + body.strip() + "\n"
    path.write_text(text, encoding="utf-8")


def generate_subject_pages() -> int:
    written = 0
    for entry in load_subjects():
        subject = str(entry["slug"])
        spec_path = APPENDIX / "spec" / f"{subject}.md"
        if not spec_path.exists():
            print(f"warn: no spec page for subject '{subject}'")
            continue
        spec_meta, _ = split_front(spec_path)
        meta = {
            "title": entry["title"],
            "summary": entry["summary"],
            "section": "subjects",
            "perspective": "hub",
            "subject": subject,
            "spec": entry["spec"],
            "order": int(entry["order"]),
            "status": "normative",
            "verified": str(spec_meta.get("verified", dt.date.today().isoformat())),
            "sources": list(spec_meta.get("sources", ["README.md"])),
            "generated": True,
        }
        write_generated(APPENDIX / "subjects" / f"{subject}.md", meta, hub_body(entry, spec_meta))
        written += 1
    return written


def generate_subject_index() -> None:
    entries = load_subjects()
    rows = []
    for entry in entries:
        subject = str(entry["slug"])
        guides = ", ".join(f"[{title_of(str(p))}](/{p})" for p in entry.get("guide", [])) or "—"
        review = ", ".join(f"[{title_of(str(p))}](/{p})" for p in entry.get("review", [])) or "—"
        rows.append(
            f"- **[{entry['title']}](/appendix/subjects/{subject})** — [{entry['spec']}](/appendix/spec/{subject}) · {guides} · [API](/{entry.get('api', 'appendix/reference/api')}) · {review}"
        )
    meta = {
        "title": "Index of subjects",
        "summary": "Every subject, with links to the book chapter and the appendix pages where it appears.",
        "section": "subjects",
        "perspective": "meta",
        "order": 0,
        "status": "normative",
        "verified": dt.date.today().isoformat(),
        "sources": ["README.md"],
        "generated": True,
    }
    body = "\n".join([
        "## In this section",
        "",
        "A subject is an index entry, not the primary reading unit. Each entry links to the book chapter that explains it and the appendix pages that state it exactly.",
        "",
        *rows,
        "",
        "## Pages",
        "",
        "Use this index after reading the book, or when a name in an appendix needs its narrative context.",
        "",
        "## Next",
        "",
        "[Specifications](/appendix/spec/index) — the normative index, by requirement family.",
    ])
    write_generated(APPENDIX / "subjects" / "index.md", meta, body)


def generate_spec_index() -> None:
    rows = []
    items = []
    for path, meta, body in pages():
        if meta.get("perspective") != "spec":
            continue
        items.append((int(meta.get("order", 999)), path, meta, body))
    for _, path, meta, body in sorted(items):
        subject = str(meta.get("subject", ""))
        rows.append(
            f"- **[{meta.get('spec')}](/appendix/spec/{subject})** — [{title_of('appendix/subjects/' + subject)}](/appendix/subjects/{subject}) · {spec_count(body)} requirements · {len(meta.get('evidence', []))} evidence paths · {meta.get('status')}"
        )
    meta = {
        "title": "Appendix A · Specifications",
        "summary": "The normative appendix: one requirement family per subject, with evidence and limits.",
        "section": "spec",
        "perspective": "meta",
        "order": 0,
        "status": "normative",
        "verified": dt.date.today().isoformat(),
        "sources": ["README.md"],
        "generated": True,
    }
    body = "\n".join([
        "## In this section",
        "",
        "The book carries the argument; this appendix carries the binding requirements. Each entry names the book chapter that explains it and the evidence that proves it.",
        "",
        *rows,
        "",
        "## Pages",
        "",
        "Read a specification when you need the requirement and its evidence. Read the book when you need to understand why the requirement exists.",
        "",
        "## Next",
        "",
        "[Index of subjects](/appendix/subjects/index) — the subject index.",
    ])
    write_generated(APPENDIX / "spec" / "index.md", meta, body)


def outside_code(body: str) -> str:
    return re.sub(r"```.*?```", " ", body, flags=re.S)


def word_count(body: str) -> int:
    text = re.sub(r"```.*?```", " ", body, flags=re.S)
    text = re.sub(r"<!-- BEGIN GENERATED:.*?<!-- END GENERATED:[a-z0-9-]+ -->", " ", text, flags=re.S)
    text = re.sub(r"<!-- BEGIN FIGURE:.*?<!-- END FIGURE:[a-z0-9-]+ -->", " ", text, flags=re.S)
    text = re.sub(r"^\|.*\|$", " ", text, flags=re.M)
    text = re.sub(r"## Decisions\n.*?(?=\n## |\Z)", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return len(text.split())


def check() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    items = pages()
    if not items:
        print("no pages")
        return 1

    slugs: dict[str, Path] = {}
    titles: dict[str, str] = {}
    known = known_decisions()
    decisions: dict[str, str] = {}
    spec_ids: dict[str, str] = {}
    inbound: Counter[str] = Counter()
    all_slugs = {slug_of(p) for p, _, _ in items}

    for path, meta, body in items:
        name = path.relative_to(CONTENT).as_posix()
        slug = slug_of(path)
        if slug != "index" and not all(SLUG.match(p) for p in slug.split("/")):
            errors.append(f"{name}: path is not kebab-case")
        if slug in slugs:
            errors.append(f"{name}: duplicate slug '{slug}'")
        slugs[slug] = path
        if not meta:
            errors.append(f"{name}: missing front matter")
            continue
        if "_yaml_error" in meta:
            errors.append(f"{name}: invalid YAML front matter: {meta['_yaml_error'].splitlines()[0]}")
            continue

        perspective = meta.get("perspective")
        for key in ("title", "summary", "section", "order", "status", "verified", "sources"):
            if key not in meta:
                errors.append(f"{name}: missing front matter key '{key}'")
        if perspective is not None:
            if perspective not in PERSPECTIVES:
                errors.append(f"{name}: bad perspective '{perspective}'")
            if perspective in ("hub", "spec"):
                for key in ("subject", "spec"):
                    if key not in meta:
                        errors.append(f"{name}: missing front matter key '{key}'")
            if perspective == "spec" and "evidence" not in meta:
                errors.append(f"{name}: missing front matter key 'evidence'")
        title = str(meta.get("title", ""))
        if title in titles:
            errors.append(f"{name}: duplicate title '{title}' (also {titles[title]})")
        titles[title] = name
        if meta.get("section") not in SECTIONS:
            errors.append(f"{name}: bad section '{meta.get('section')}'")
        if meta.get("status") not in STATUSES:
            errors.append(f"{name}: bad status '{meta.get('status')}'")
        if not isinstance(meta.get("order"), int):
            errors.append(f"{name}: order must be an integer")
        summary = str(meta.get("summary", ""))
        if not (20 <= len(summary) <= 160):
            warnings.append(f"{name}: summary length {len(summary)} (want 20-160)")
        try:
            verified = dt.date.fromisoformat(str(meta.get("verified")))
            if verified > dt.date.today():
                errors.append(f"{name}: verified is in the future")
        except ValueError:
            errors.append(f"{name}: verified is not YYYY-MM-DD")

        sources = meta.get("sources") or []
        if not isinstance(sources, list) or not 1 <= len(sources) <= 5:
            errors.append(f"{name}: sources must be a list of 1-5 paths")
        for src in sources:
            if not (SOURCE / str(src)).exists():
                errors.append(f"{name}: source does not exist: {src}")

        if re.search(r"^# ", outside_code(body), re.M):
            errors.append(f"{name}: body must not contain an H1")
        if is_index(path):
            if slug == "book":
                required_index = ["In this book", "Parts", "Next"]
            elif slug.startswith("book/part-"):
                required_index = ["In this part", "Chapters", "Next"]
            elif slug != "index":
                required_index = INDEX_REQUIRED
            else:
                required_index = []
            for section in required_index:
                if f"## {section}" not in body:
                    errors.append(f"{name}: missing section '## {section}'")
        else:
            section = str(meta.get("section", "meta"))
            required = (
                HUB_REQUIRED if perspective == "hub"
                else SPEC_REQUIRED if perspective == "spec"
                else SECTION_REQUIRED.get(section, [])
            )
            for heading in required:
                if f"## {heading}" not in body:
                    errors.append(f"{name}: missing section '## {heading}'")
            limit = WORD_LIMITS.get(section)
            if limit and word_count(body) > limit:
                warnings.append(f"{name}: {word_count(body)} words (limit {limit})")

        if perspective == "spec":
            spec_id = str(meta.get("spec", ""))
            if not SPEC_ID.match(spec_id):
                errors.append(f"{name}: spec ID must be SPEC-###")
            elif spec_id in spec_ids:
                errors.append(f"{name}: duplicate spec ID {spec_id} (also {spec_ids[spec_id]})")
            else:
                spec_ids[spec_id] = name
            evidence = meta.get("evidence") or []
            if not isinstance(evidence, list) or not 1 <= len(evidence) <= 5:
                errors.append(f"{name}: evidence must be a list of 1-5 paths")
            for evidence_path in evidence:
                if not (SOURCE / str(evidence_path)).exists():
                    errors.append(f"{name}: evidence does not exist: {evidence_path}")
            if not re.search(r"\b(MUST|SHOULD)\b", body):
                errors.append(f"{name}: spec has no MUST or SHOULD requirement")
            if spec_count(body) < 1:
                errors.append(f"{name}: spec has no R-numbered requirement")
        if perspective == "hub":
            entry = subject_entry(str(meta.get("subject", "")))
            if entry is None:
                errors.append(f"{name}: hub subject is not in subjects.yml")
            elif entry.get("spec") != meta.get("spec"):
                errors.append(f"{name}: hub spec does not match subjects.yml")

        for word in STALE_WORDS:
            if re.search(rf"\b{word}\b", body, re.I):
                warnings.append(f"{name}: contains '{word}'")

        next_match = re.search(r"## Next\n(.*?)(?=\n## |\Z)", body, re.S)
        if next_match and not (
            MDLINK.search(next_match.group(1)) or WIKILINK.search(next_match.group(1))
        ):
            errors.append(f"{name}: ## Next has no link")

        for line in body.splitlines():
            if line.lstrip().startswith("|") and re.search(r"\[\[[^\]|]*\|", line):
                errors.append(f"{name}: wikilink with a label inside a table row")

        for target, _ in ((m.group(1).strip(), m.group(2)) for m in WIKILINK.finditer(body)):
            resolved = resolve_wikilink(target)
            if resolved is None:
                errors.append(f"{name}: broken wikilink [[{target}]]")
            else:
                inbound[resolved] += 1
        for m in MDLINK.finditer(body):
            href = m.group(1).strip()
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = resolve_link(path, href)
            if resolved is None:
                errors.append(f"{name}: broken link {href}")
            else:
                inbound[resolved] += 1
        for m in HREFLINK.finditer(body):
            href = m.group(1).strip()
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = resolve_link(path, href)
            if resolved is None:
                errors.append(f"{name}: broken link {href}")
            else:
                inbound[resolved] += 1

        found_blocks = BLOCK.findall(body)
        seen: set[str] = set()
        for block_name, content in found_blocks:
            if block_name not in KNOWN_BLOCKS:
                errors.append(f"{name}: unknown generated block '{block_name}'")
            if block_name in seen:
                errors.append(f"{name}: duplicate generated block '{block_name}'")
            seen.add(block_name)
        if body.count("<!-- BEGIN GENERATED:") != len(found_blocks):
            errors.append(f"{name}: malformed generated block markers")
        if meta.get("subject") and perspective and "views" not in seen:
            errors.append(f"{name}: page with a subject needs a generated views block")

        for line in body.splitlines():
            parsed = parse_decision_row(line)
            if parsed is None:
                continue
            did, decision, _, _, _ = parsed
            if did not in known:
                errors.append(f"{name}: unknown decision {did}")
            prev = decisions.get(did)
            if prev and prev != decision:
                errors.append(f"{name}: decision {did} text differs from another page")
            decisions[did] = decision

    for slug in sorted(all_slugs):
        if slug in ("index",) or slug.endswith("/index") or slug in SECTIONS:
            continue
        if inbound[slug] < 2:
            warnings.append(f"{slug}: only {inbound[slug]} inbound link(s)")

    try:
        subject_entries = load_subjects()
    except yaml.YAMLError as exc:
        errors.append(f"subjects.yml: invalid YAML: {exc}")
        subject_entries = []
    seen_subjects = set()
    seen_orders = set()
    for entry in subject_entries:
        slug = str(entry.get("slug", ""))
        if not slug or not SLUG.match(slug):
            errors.append(f"subjects.yml: bad slug '{slug}'")
        if slug in seen_subjects:
            errors.append(f"subjects.yml: duplicate slug '{slug}'")
        seen_subjects.add(slug)
        order = entry.get("order")
        if not isinstance(order, int):
            errors.append(f"subjects.yml: {slug}: order must be an integer")
        elif order in seen_orders:
            errors.append(f"subjects.yml: duplicate order {order}")
        else:
            seen_orders.add(order)
        if not SPEC_ID.match(str(entry.get("spec", ""))):
            errors.append(f"subjects.yml: {slug}: bad spec ID")
        spec_path = APPENDIX / "spec" / f"{slug}.md"
        if not spec_path.exists():
            errors.append(f"subjects.yml: {slug}: missing spec page spec/{slug}.md")
        else:
            spec_meta, spec_body = split_front(spec_path)
            if spec_meta.get("spec") != entry.get("spec"):
                errors.append(f"subjects.yml: {slug}: spec ID does not match spec/{slug}.md")
        for key in ("guide", "philosophy", "review"):
            for page in entry.get(key, []):
                if not (CONTENT / f"{page}.md").exists():
                    errors.append(f"subjects.yml: {slug}: missing {key} page {page}.md")
        api = entry.get("api")
        if api and not (CONTENT / f"{api}.md").exists():
            errors.append(f"subjects.yml: {slug}: missing api page {api}.md")
        if not (APPENDIX / "subjects" / f"{slug}.md").exists():
            warnings.append(f"subjects.yml: {slug}: hub not generated yet")
    try:
        spec_map = yaml.safe_load(SPEC_MAP_FILE.read_text(encoding="utf-8")) or []
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"spec-map.yml: cannot read: {exc}")
        spec_map = []
    mapped_specs = set()
    for entry in spec_map:
        page = str(entry.get("page", ""))
        spec_id = str(entry.get("spec", ""))
        mapped_specs.add(spec_id)
        page_path = CONTENT / f"{page}.md"
        if not page_path.exists():
            errors.append(f"spec-map.yml: missing spec page {page}.md")
        else:
            meta, _ = split_front(page_path)
            if meta.get("spec") != spec_id:
                errors.append(f"spec-map.yml: {page} does not carry {spec_id}")
        for source in entry.get("sources", []):
            if not (SOURCE / str(source)).exists():
                errors.append(f"spec-map.yml: source does not exist: {source}")
    for path, meta, _ in items:
        if meta.get("perspective") == "spec" and meta.get("spec") not in mapped_specs:
            warnings.append(f"{path.name}: spec has no ownership entry in spec-map.yml")

    for w in warnings:
        print(f"warn: {w}")
    for e in errors:
        print(f"error: {e}")
    print(
        f"\n{len(items)} pages, {len(known)} decisions, {len(errors)} errors, "
        f"{len(warnings)} warnings"
    )
    return 1 if errors else 0


def run(command: str, cwd: Path, timeout: int = 300) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            command, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, str(exc)


DOC_SOURCE_PREFIXES = ("docs/", "specs/")
DOC_SOURCE_NAMES = {
    "README.md", "AGENTS.md", "ARCHITECTURE.md", "FRAMEWORK_STATE.md",
    "DESIGN_ISSUES.md", "STYLE.md",
}


def is_documentation_source(path: str) -> bool:
    return (
        path.startswith(DOC_SOURCE_PREFIXES)
        or path in DOC_SOURCE_NAMES
        or path.endswith(".md")
    )


def git_date(path: str) -> str:
    code, out = run(f"git log -1 --format=%ad --date=short -- {json.dumps(path)}", SOURCE)
    return out.splitlines()[0].strip() if code == 0 and out.strip() else "untracked"


_STATUS: dict[str, str] | None = None


def measure_status() -> dict[str, str]:
    global _STATUS
    if _STATUS is not None:
        return _STATUS
    code, out = run("uv run pytest -q", SOURCE)
    tests = subtests = seconds = "not measured"
    if code == 0:
        m = re.search(r"(\d+) passed(?:, (\d+) subtests passed)?(?: in ([\d.]+)s)?", out)
        if m:
            tests = m.group(1)
            subtests = m.group(2) or "0"
            seconds = m.group(3) or "?"
    py_code, py_out = run("uv run pyright", SOURCE)
    py = "not measured"
    m = re.search(r"(\d+) errors?, (\d+) warnings?, (\d+) informations?", py_out)
    if m:
        count = int(m.group(1))
        py = f"{count} error" + ("" if count == 1 else "s")
    head_code, head_out = run("git log -1 --format='%h|%ad' --date=short", SOURCE)
    head = head_out.strip() if head_code == 0 and head_out.strip() else "unknown"
    if "|" in head:
        commit, date = head.split("|", 1)
    else:
        commit, date = head, "unknown"
    _STATUS = {
        "tests": tests,
        "subtests": subtests,
        "seconds": seconds,
        "pyright": py,
        "commit": commit,
        "date": date,
        "state": "passes" if code == 0 else "fails",
    }
    return _STATUS


def status_block() -> str:
    data = measure_status()
    return (
        "| Measure | Value |\n"
        "| --- | --- |\n"
        f"| Test suite | {data['tests']} tests, {data['subtests']} subtests, {data['seconds']}s — {data['state']} |\n"
        f"| Static types | {data['pyright']} |\n"
        f"| Source | `{data['commit']}` ({data['date']}) |\n"
        "| Docs build | `./docs/build.sh` from the repository root |"
    )


def status_strip() -> str:
    data = measure_status()
    return (
        '<div class="kb-stats">'
        f'<span><b>{data["tests"]}</b> tests</span>'
        f'<span><b>{data["subtests"]}</b> subtests</span>'
        f'<span><b>{data["pyright"]}</b> pyright</span>'
        f'<span><b>{data["commit"]}</b> source</span>'
        f'<span><b>{data["date"]}</b> checked</span>'
        "</div>"
    )


def api_block() -> str:
    path = SOURCE / "kg_build_system" / "__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    groups = None
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "_GROUPS":
            groups = ast.literal_eval(node.value)
    if not groups:
        return "No export table found."
    rows = ["| Defining module | Public names |", "| --- | --- |"]
    for group, names in groups.items():
        label = f"kg_build_system.{group}"
        joined = ", ".join(f"`{n}`" for n in names)
        rows.append(f"| `{label}` | {joined} |")
    return "\n".join(rows)


def code_map_block() -> str:
    root = SOURCE / "kg_build_system"
    zones = (
        "model/public",
        "model/internal",
        "model/_private",
        "service/public",
        "service/internal",
        "service/_private",
    )
    leaves: dict[str, list[str]] = {}
    for init_file in sorted(root.rglob("__init__.py")):
        rel = init_file.parent.relative_to(root)
        parts = rel.parts
        if len(parts) >= 3 and parts[0] == "distribution" and parts[1] in ("languages", "modules"):
            leaf = "/".join(parts[:3])
        elif len(parts) >= 2 and parts[0] == "distribution":
            leaf = "/".join(parts[:2])
        else:
            leaf = parts[0] if parts else "root"
        leaves[leaf] = [z for z in zones if (init_file.parent / z).is_dir()]

    edges: Counter[tuple[str, str]] = Counter()

    def leaf_of(parts: tuple[str, ...]) -> str:
        if parts and parts[0] == "distribution" and len(parts) >= 3 and parts[1] in (
            "languages",
            "modules",
        ):
            return f"distribution/{parts[1]}/{parts[2]}"
        if len(parts) >= 2 and parts[0] == "distribution":
            return f"distribution/{parts[1]}"
        return parts[0] if parts else "root"

    for py in root.rglob("*.py"):
        rel = py.relative_to(root)
        if rel.parent == Path("."):
            src = "root" if rel.stem == "__init__" else rel.stem
        else:
            src = leaf_of(rel.parent.parts)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods.append(node.module)
            elif isinstance(node, ast.Import):
                mods.extend(alias.name for alias in node.names)
            for mod in mods:
                if not mod.startswith("kg_build_system"):
                    continue
                dst = leaf_of(tuple(mod.split(".")[1:]))
                if dst != src:
                    edges[(src, dst)] += 1

    rows = [f"{len(leaves)} leaves; empty zones are deleted. Strongest import edges:", "", "| Import edge | Files |", "| --- | ---: |"]
    top = sorted(edges.items(), key=lambda item: (-item[1], item[0]))[:14]
    for (src, dst), count in top:
        rows.append(f"| `{src}` → `{dst}` | {count} |")
    violations = [
        f"`{src}` → `{dst}`"
        for src, dst in edges
        if src == "kernel" and dst.startswith("distribution")
    ]
    rows += ["", f"Kernel boundary violations: {', '.join(violations) or 'none'}."]
    return "\n".join(rows)


def decisions_block() -> str:
    found: dict[str, dict] = {}
    for path, meta, body in pages():
        if meta.get("generated"):
            continue
        for line in body.splitlines():
            parsed = parse_decision_row(line)
            if parsed is None:
                continue
            did, decision, date, status, evidence = parsed
            entry = found.setdefault(
                did,
                {"decision": decision, "date": date, "status": status, "evidence": evidence, "pages": set()},
            )
            entry["pages"].add(slug_of(path))
    for did, candidate in candidate_decisions().items():
        found.setdefault(
            did,
            {
                "decision": candidate["decision"],
                "date": candidate["date"],
                "status": candidate["status"],
                "evidence": candidate["evidence"],
                "pages": set(),
            },
        )
    rows = ["| ID | Decision | Date | Status | Page | Evidence |", "| --- | --- | --- | --- | --- | --- |"]
    for did in sorted(found):
        e = found[did]
        def page_link(page: str) -> str:
            if page == "index":
                return "/"
            if page in SECTIONS or (CONTENT / page / "index.md").exists():
                return f"/{page}/"
            return f"/{page}"

        links = ", ".join(
            f"[{p}]({page_link(p)})"
            for p in sorted(e["pages"])
        )
        rows.append(f"| {did} | {e['decision']} | {e['date']} | {e['status']} | {links} | {e['evidence']} |")
    return "\n".join(rows)


def drift_block() -> str:
    dates: dict[str, str] = {}
    rows = []
    clean = 0
    for path, meta, _ in pages():
        if is_index(path):
            continue
        verified = str(meta.get("verified", ""))
        latest = ""
        for src in meta.get("sources") or []:
            source = str(src)
            if is_documentation_source(source):
                continue
            if source not in dates:
                dates[source] = git_date(source)
            value = dates[source]
            if value != "untracked" and value > latest:
                latest = value
        if latest and verified and latest > verified:
            rows.append(f"| `{slug_of(path)}` | {verified} | {latest} | {latest} > {verified} |")
        else:
            clean += 1
    head_code, head_out = run("git log -1 --format='%h|%ad' --date=short", SOURCE)
    head = head_out.strip().replace("|", " · ") if head_code == 0 else "unknown"
    out = [
        f"Source HEAD: {head}. Pages checked: {clean + len(rows)}; clean: {clean}; drifted: {len(rows)}.",
        "",
    ]
    if rows:
        out += ["| Page | Verified | Latest source change | Action |", "| --- | --- | --- | --- |"]
        out += rows
    else:
        out.append("No page has a source commit after its `verified` date.")
    return "\n".join(out)


REFERENCE_SCRIPT = r"""
import json, tempfile
from pathlib import Path
from kg_build_system import compile, execute
from reference_project.build import create_reference_blueprint, compile_reference_build

blueprint = create_reference_blueprint()
plan = compile_reference_build()
with tempfile.TemporaryDirectory() as directory:
    report = execute(plan, output_directory=Path(directory))
    graph = Path(directory) / "graph.jsonl"
    records = [json.loads(line) for line in graph.read_text().splitlines() if line.strip()]
    nodes = sum(1 for r in records if r.get("kind") == "node")
    edges = sum(1 for r in records if r.get("kind") == "edge")
    result = {
        "components": len(plan.components),
        "steps": len(plan.steps),
        "connections": len(plan.connections),
        "nodes": nodes,
        "edges": edges,
        "artifacts": sorted(a.type.name for a in report.published_artifacts),
        "succeeded": report.succeeded,
    }
print(json.dumps(result))
"""


def reference_block() -> str:
    script = ROOT / ".measure_reference.py"
    script.write_text(REFERENCE_SCRIPT, encoding="utf-8")
    try:
        code, out = run(f"uv run python {json.dumps(str(script))}", SOURCE)
    finally:
        script.unlink(missing_ok=True)
    if code != 0:
        return f"Reference build not measured.\n\n```text\n{out[-800:]}\n```"
    line = out.strip().splitlines()[-1]
    data = json.loads(line)
    return (
        "| Measure | Reference build |\n"
        "| --- | --- |\n"
        f"| Components | {data['components']} |\n"
        f"| Steps | {data['steps']} |\n"
        f"| Connections | {data['connections']} |\n"
        f"| Published records | {data['nodes']} nodes, {data['edges']} edges |\n"
        f"| Publications | {', '.join(data['artifacts'])} |\n"
        f"| Report | {'succeeded' if data['succeeded'] else 'failed'} |"
    )


BLOCKS = {
    "status": status_block,
    "status-strip": status_strip,
    "api": api_block,
    "code-map": code_map_block,
    "decisions": decisions_block,
    "drift": drift_block,
    "reference": reference_block,
}


def generate() -> int:
    hubs = generate_subject_pages()
    generate_subject_index()
    generate_spec_index()
    generated = {name: fn() for name, fn in BLOCKS.items()}
    changed = 0
    for path, meta, body in pages():
        new_body = body
        for name, content in generated.items():
            pattern = re.compile(
                rf"(<!-- BEGIN GENERATED:{name} -->).*?(<!-- END GENERATED:{name} -->)",
                re.S,
            )
            if pattern.search(new_body):
                new_body = pattern.sub(
                    lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", new_body
                )
        subject = meta.get("subject")
        entry = subject_entry(str(subject)) if subject else None
        if entry:
            views = views_html(entry, slug_of(path), meta.get("perspective"))
            pattern = re.compile(
                r"(<!-- BEGIN GENERATED:views -->).*?(<!-- END GENERATED:views -->)", re.S
            )
            if pattern.search(new_body):
                new_body = pattern.sub(
                    lambda m: f"{m.group(1)}\n{views}\n{m.group(2)}", new_body
                )
        if new_body != body:
            text = path.read_text(encoding="utf-8")
            original = body
            path.write_text(text.replace(original, new_body, 1), encoding="utf-8")
            changed += 1
    print(f"generated {len(generated)} blocks, {hubs} hubs, {changed} pages changed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["check", "generate", "all"])
    args = ap.parse_args()
    if args.command in ("generate", "all"):
        generate()
    if args.command in ("check", "all"):
        return check()
    return 0


if __name__ == "__main__":
    sys.exit(main())
