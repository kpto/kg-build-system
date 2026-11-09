/**
 * The meaning ViewModel.
 *
 * A meaning surface reads two things and nothing else: the graph declaration
 * (name, description, purpose, claims and purpose frames) and the semantics
 * attached to a subject. It does not read the review sidecar, a ledger or a
 * decision.
 *
 * The ViewModel is framework agnostic. It builds immutable display values from
 * `ViewerIndex`; the view only decides which list is open.
 */

import type {
  AssetProfileDTO,
  SemanticSubject,
  SemanticSubjectKind,
  SemanticsDTO,
  SemanticsFrameDTO,
  SemanticText,
  ViewerIndex,
} from "@/lib/types";

export type MeaningUnitKind = "claim" | "frame" | "limitation";

export interface MeaningClaim {
  kind: "claim";
  text: string;
}

export interface MeaningLimitation {
  kind: "limitation";
  text: string;
}

export interface MeaningFrame {
  kind: "frame";
  /** Stable within its owner; used as a local expansion key. */
  key: string;
  text: string;
  limitations: MeaningLimitation[];
}

export interface MeaningUnitCount {
  claims: number;
  frames: number;
  limitations: number;
  units: number;
}

export interface MeaningSubjectView {
  kind: SemanticSubjectKind;
  key: string;
  name: string;
  /** Display path, for example `surveys.title` or `topology/defect`. */
  path: string;
  ownerName?: string;
  entityKind?: "node" | "edge";
  ref?: string[];
  profile?: AssetProfileDTO;
  claims: MeaningClaim[];
  frames: MeaningFrame[];
  counts: MeaningUnitCount;
}

export interface MeaningSubjectGroup {
  kind: SemanticSubjectKind;
  label: string;
  subjects: MeaningSubjectView[];
}

export interface MeaningGraphView {
  name: string;
  description?: string;
  purpose?: string;
  claims: MeaningClaim[];
  frames: MeaningFrame[];
  counts: MeaningUnitCount;
}

export interface MeaningModel {
  graph: MeaningGraphView;
  /** Subjects that carry attached semantics or an asset profile; excludes the graph. */
  subjects: MeaningSubjectView[];
  subjectsByKey: Map<string, MeaningSubjectView>;
  /** Non-empty groups in presentation order. */
  groups: MeaningSubjectGroup[];
  /** Attached units only. */
  attached: MeaningUnitCount;
  /** Graph units plus attached units. */
  counts: MeaningUnitCount;
  /** Subjects with attached semantics or a profile; excludes the graph. */
  subjectCount: number;
  /** Subject count per kind. Kinds without subjects are absent. */
  kindCounts: Map<SemanticSubjectKind, number>;
}

export const MEANING_KIND_ORDER: SemanticSubjectKind[] = [
  "asset",
  "relation",
  "projection",
  "struct",
  "field",
  "node",
  "edge",
  "property",
  "binding",
  "graph",
];

export const MEANING_KIND_LABELS: Record<SemanticSubjectKind, string> = {
  graph: "Graph",
  asset: "Assets",
  relation: "Relations",
  projection: "Projections",
  struct: "Structs",
  field: "Fields",
  node: "Nodes",
  edge: "Edges",
  property: "Properties",
  binding: "Bindings",
};

const KIND_LABEL_SINGULAR: Record<SemanticSubjectKind, string> = {
  graph: "graph",
  asset: "asset",
  relation: "relation",
  projection: "projection",
  struct: "struct",
  field: "field",
  node: "node",
  edge: "edge",
  property: "property",
  binding: "binding",
};

function textOf(unit: SemanticText | undefined): string | undefined {
  const text = unit?.text?.trim();
  return text ? text : undefined;
}

function claimsOf(units: SemanticText[] | undefined): MeaningClaim[] {
  return (units ?? [])
    .map(textOf)
    .filter((text): text is string => Boolean(text))
    .map((text) => ({ kind: "claim", text }));
}

function framesOf(
  keyPrefix: string,
  frames: SemanticsFrameDTO[] | undefined,
): MeaningFrame[] {
  return (frames ?? []).flatMap((frame, index) => {
    const text = textOf(frame);
    if (!text) return [];
    const limitations = (frame.limitations ?? [])
      .map(textOf)
      .filter((value): value is string => Boolean(value))
      .map(
        (value): MeaningLimitation => ({ kind: "limitation", text: value }),
      );
    return [
      {
        kind: "frame",
        key: `${keyPrefix}:frame:${index}`,
        text,
        limitations,
      },
    ];
  });
}

function countsOf(
  claims: MeaningClaim[],
  frames: MeaningFrame[],
): MeaningUnitCount {
  const limitations = frames.reduce(
    (total, frame) => total + frame.limitations.length,
    0,
  );
  return {
    claims: claims.length,
    frames: frames.length,
    limitations,
    units: claims.length + frames.length + limitations,
  };
}

function addCounts(left: MeaningUnitCount, right: MeaningUnitCount): MeaningUnitCount {
  return {
    claims: left.claims + right.claims,
    frames: left.frames + right.frames,
    limitations: left.limitations + right.limitations,
    units: left.units + right.units,
  };
}

export function emptyMeaningCount(): MeaningUnitCount {
  return { claims: 0, frames: 0, limitations: 0, units: 0 };
}

function subjectPath(subject: SemanticSubject): string {
  switch (subject.kind) {
    case "field":
    case "property":
      return subject.ownerName
        ? `${subject.ownerName}.${subject.name}`
        : subject.name;
    case "node":
      return `node/${subject.name}`;
    case "edge":
      return `edge/${subject.name}`;
    case "asset":
      return `asset/${subject.name}`;
    case "binding":
      return `binding/${subject.name}`;
    case "relation":
      return `relation/${subject.name}`;
    case "projection":
      return `projection/${subject.name}`;
    case "struct":
      return `struct/${subject.name}`;
    default:
      return subject.name;
  }
}

function subjectView(
  subject: SemanticSubject,
  profile: AssetProfileDTO | undefined,
): MeaningSubjectView {
  const semantics: SemanticsDTO | undefined = subject.semantics;
  const claims = claimsOf(semantics?.claims);
  const frames = framesOf(subject.key, semantics?.frames);
  return {
    kind: subject.kind,
    key: subject.key,
    name: subject.name,
    path: subjectPath(subject),
    ...(subject.ownerName ? { ownerName: subject.ownerName } : {}),
    ...(subject.entityKind ? { entityKind: subject.entityKind } : {}),
    ...(subject.ref ? { ref: subject.ref } : {}),
    ...(profile ? { profile } : {}),
    claims,
    frames,
    counts: countsOf(claims, frames),
  };
}

function hasContent(subject: MeaningSubjectView): boolean {
  return subject.counts.units > 0 || Boolean(subject.profile);
}

function graphView(
  index: ViewerIndex,
  graphSubject: MeaningSubjectView | undefined,
): MeaningGraphView {
  const declaration = index.graphDeclaration;
  const semantics = index.graphSemantics;
  const claims = claimsOf(semantics?.claims);
  const frames = framesOf(
    graphSubject?.key ?? "graph",
    semantics?.purpose?.frames,
  );
  return {
    name:
      declaration?.name ??
      graphSubject?.name ??
      index.snapshot.name ??
      "Graph",
    ...(declaration?.description ? { description: declaration.description } : {}),
    ...(semantics?.purpose?.text?.trim()
      ? { purpose: semantics.purpose.text.trim() }
      : {}),
    claims,
    frames,
    counts: countsOf(claims, frames),
  };
}

/** Build the meaning ViewModel from the loaded viewer index. */
export function buildMeaningModel(index: ViewerIndex): MeaningModel {
  const subjectsByKey = new Map<string, MeaningSubjectView>();
  const subjects: MeaningSubjectView[] = [];
  let attached = emptyMeaningCount();

  for (const subject of index.semanticSubjects) {
    if (subject.kind === "graph") continue;
    const profile =
      subject.kind === "asset"
        ? index.assetProfilesByName.get(subject.assetName ?? subject.name)
        : undefined;
    const view = subjectView(subject, profile);
    subjectsByKey.set(view.key, view);
    if (!hasContent(view)) continue;
    subjects.push(view);
    attached = addCounts(attached, view.counts);
  }

  const graphSubject = index.semanticSubjects.find(
    (subject) => subject.kind === "graph",
  );
  const graphSubjectView = graphSubject
    ? subjectView(graphSubject, undefined)
    : undefined;
  const graph = graphView(index, graphSubjectView);

  const groups = groupMeaningSubjects(subjects);
  const kindCounts = new Map<SemanticSubjectKind, number>();
  for (const group of groups) {
    kindCounts.set(group.kind, group.subjects.length);
  }

  return {
    graph,
    subjects,
    subjectsByKey,
    groups,
    attached,
    counts: addCounts(graph.counts, attached),
    subjectCount: subjects.length,
    kindCounts,
  };
}

/** Group subjects by kind, keeping the canonical kind order. */
export function groupMeaningSubjects(
  subjects: MeaningSubjectView[],
): MeaningSubjectGroup[] {
  const byKind = new Map<SemanticSubjectKind, MeaningSubjectView[]>();
  for (const subject of subjects) {
    const group = byKind.get(subject.kind) ?? [];
    group.push(subject);
    byKind.set(subject.kind, group);
  }
  return MEANING_KIND_ORDER.filter((kind) => byKind.has(kind)).map((kind) => {
    const group = byKind.get(kind) ?? [];
    return {
      kind,
      label: MEANING_KIND_LABELS[kind],
      subjects: [...group].sort((left, right) =>
        left.path.localeCompare(right.path, undefined, { sensitivity: "base" }),
      ),
    };
  });
}

export interface MeaningSubjectFilter {
  /** Case-insensitive text matched against a subject's path, name and kind. */
  query?: string;
  /** Restrict to these kinds. An empty set means no kind restriction. */
  kinds?: Iterable<SemanticSubjectKind>;
}

function matchesQuery(subject: MeaningSubjectView, needle: string): boolean {
  if (!needle) return true;
  return (
    subject.path.toLowerCase().includes(needle) ||
    subject.name.toLowerCase().includes(needle) ||
    subject.ownerName?.toLowerCase().includes(needle) === true ||
    KIND_LABEL_SINGULAR[subject.kind].includes(needle)
  );
}

/**
 * Filter and regroup the subject browser.
 *
 * A group survives only while it has a matching subject. The order is stable:
 * canonical kind order, then display path. The view decides how many rows to
 * render; this helper keeps every match so counts stay honest.
 */
export function filterMeaningSubjects(
  groups: MeaningSubjectGroup[],
  filter: MeaningSubjectFilter = {},
): MeaningSubjectGroup[] {
  const needle = filter.query?.trim().toLowerCase() ?? "";
  const kinds = filter.kinds ? new Set(filter.kinds) : undefined;
  const restricted = kinds && kinds.size > 0 ? kinds : undefined;
  return groups.flatMap((group) => {
    if (restricted && !restricted.has(group.kind)) return [];
    const subjects = group.subjects.filter((subject) =>
      matchesQuery(subject, needle),
    );
    return subjects.length ? [{ ...group, subjects }] : [];
  });
}

/** The limitations a frame displays; collapsed frames expose none. */
export function visibleFrameLimitations(
  frame: MeaningFrame,
  expanded: boolean,
): MeaningLimitation[] {
  return expanded ? frame.limitations : [];
}

/** Shared label contract for the sidebar and editor headers. */
export function meaningUnitLabel(
  kind: MeaningUnitKind,
  count: number,
): string {
  const label =
    kind === "claim" ? "claim" : kind === "frame" ? "frame" : "limitation";
  return `${count} ${label}${count === 1 ? "" : "s"}`;
}
