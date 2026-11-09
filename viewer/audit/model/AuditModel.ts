/**
 * The audit ViewModel.
 *
 * This module is framework-agnostic: it never imports React, JSX, a view or an
 * icon component. The view receives an `AuditModel`; the composition root calls
 * `buildAuditModel(campaign, input)`.
 *
 * The model owns the audit's meaning (score, findings, coverage, decisions,
 * build health, diff, dossier and the commands that act on them). The view owns
 * only view state: the selected rail entry, the local filter values, the waiver
 * draft, which sections are open and how many rows are mounted.
 */

import { hasChanges } from "@/lib/diff";
import { computeImpact } from "@/lib/impact";
import type {
  AuditSubject,
  DecisionStatus,
  DecisionView,
  EvidenceRef,
  ReviewQueueSummary,
  ReviewRecord,
  ReviewStatus,
  Severity,
} from "@/lib/reviewTypes";
import type {
  BuildReport,
  EntityKind,
  StepId,
  ViewerSnapshot,
} from "@/lib/types";
import type { AuditInput } from "@/shared/model/builders";
import type { CampaignView } from "@/shared/model/campaign";
import type {
  ActionModel,
  FieldModel,
  IconToken,
  PanelModel,
  RailModel,
  RowModel,
  SectionModel,
  Tone,
} from "@/shared/model/hierarchy";

// ---------------------------------------------------------------------------
// Model vocabulary
// ---------------------------------------------------------------------------

export type AuditSectionKind =
  | "summary"
  | "findings"
  | "questions"
  | "coverage"
  | "decisions"
  | "build"
  | "diff"
  | "dossier";

/**
 * How the view binds an action.
 *
 * `command` actions carry their command. The remaining kinds are view decisions
 * (opening a waiver editor, changing a bounded mount or opening a file picker);
 * the model names the intent and the view binds it to its local state.
 */
export type AuditActionKind =
  | "command"
  | "waive"
  | "show-all"
  | "show-more"
  | "show-less"
  | "compare";

/** An action plus the stable test id and pressed/explanation metadata. */
export interface AuditActionModel extends Omit<ActionModel, "run"> {
  kind: AuditActionKind;
  run?: () => void;
  testId?: string;
  tone?: Tone;
  pressed?: boolean;
  /** Secondary explanation for the dossier buttons. */
  hint?: string;
  primary?: boolean;
}

export interface AuditRowModel
  extends Omit<RowModel, "fields" | "actions"> {
  fields?: FieldModel[];
  actions?: AuditActionModel[];
  testId?: string;
}

export interface AuditSectionBase
  extends Omit<SectionModel, "rows" | "fields" | "actions"> {
  kind: AuditSectionKind;
  testId: string;
  toggleTestId: string;
  railTestId: string;
  icon: IconToken;
  /** Where the two-column audit body places this section. */
  layout: "full" | "left" | "right" | "full-tail";
  rows?: AuditRowModel[];
  fields?: FieldModel[];
  actions?: AuditActionModel[];
  collapsible: boolean;
  defaultOpen: boolean;
}

export interface AuditRailModel extends RailModel {
  /** The section's test id, used to scroll to it. */
  target: string;
  testId: string;
}

export type VerificationState =
  | "compile-only"
  | "failed"
  | "executed"
  | "unknown";

export type VerificationTone = "amber" | "red" | "green" | "neutral";

export interface AuditVerificationModel {
  state: VerificationState;
  label: string;
  detail: string;
  tone: VerificationTone;
}

export interface AuditLegendModel {
  severity: Severity;
  count: number;
  testId: string;
}

export interface AuditRubricRow extends AuditRowModel {
  componentId: string;
  detail: string;
  raw: number;
  weight: number;
  contribution: number;
  testId: string;
}

export interface AuditSummarySection extends AuditSectionBase {
  kind: "summary";
  score: number;
  band: string;
  ticks: number[];
  components: AuditRubricRow[];
  observations: number;
  queueOpen: number;
  verification: AuditVerificationModel;
  legend: AuditLegendModel[];
  queue: ReviewQueueSummary;
  reviewed: number;
  reviewedPercent: number;
}

export interface AuditImpactModel {
  label: string;
  title: string;
}

export interface AuditFindingRow extends AuditRowModel {
  findingId: string;
  severity: Severity;
  rule: string;
  status: ReviewStatus;
  tags: string[];
  question?: string;
  evidenceCount: number;
  note?: string;
  subject?: AuditSubject;
  subjectLabel: string;
  /**
   * Computed on demand. The view asks only for the rows it mounts, so a large
   * snapshot pays the lineage cost for the bounded page, not every finding.
   */
  impact: () => AuditImpactModel | undefined;
  acknowledge: AuditActionModel;
  waive: AuditActionModel;
  openSubject?: AuditActionModel;
}

export interface AuditFindingsSection extends AuditSectionBase {
  kind: "findings";
  rows: AuditFindingRow[];
  totalFindings: number;
  rules: string[];
  tags: string[];
  queue: ReviewQueueSummary;
  reviewed: number;
  reviewedPercent: number;
  showAll: AuditActionModel;
  showLess: AuditActionModel;
}

export interface AuditQuestionRow extends AuditRowModel {
  findingId: string;
  rule: string;
  status: ReviewStatus;
  evidenceCount: number;
  question: string;
  subject?: AuditSubject;
  subjectLabel: string;
  openSubject?: AuditActionModel;
  acknowledge: AuditActionModel;
}

export interface AuditQuestionsSection extends AuditSectionBase {
  kind: "questions";
  rows: AuditQuestionRow[];
  showMore: AuditActionModel;
}

export interface AuditCoverageCellModel {
  source: string;
  fields: number;
  literals: number;
  bindings: number;
  open: AuditActionModel;
}

export interface AuditCoverageRow extends AuditRowModel {
  key: string;
  entityKind: EntityKind;
  component: string;
  property: string;
  tracedFields: number;
  literals: number;
  cells: AuditCoverageCellModel[];
  open: AuditActionModel;
}

export interface AuditCoverageSection extends AuditSectionBase {
  kind: "coverage";
  sources: string[];
  rows: AuditCoverageRow[];
  showAll: AuditActionModel;
  showLess: AuditActionModel;
}

export interface AuditDecisionCounts {
  sidecar: number;
  derived: number;
  rationaleSupplied: number;
  rationaleMissing: number;
  open: number;
}

export interface AuditAiModel {
  model?: string;
  runId?: string;
  generatedAt?: string;
  note?: string;
  testId: string;
}

export interface AuditDecisionRow extends AuditRowModel {
  decisionId: string;
  status: DecisionStatus;
  source: "sidecar" | "derived";
  rationaleSupplied: boolean;
  rationale: string;
  tags: string[];
  evidence: EvidenceRef[];
  subject?: AuditSubject;
  subjectLabel: string;
  openSubject?: AuditActionModel;
}

export interface AuditDecisionsSection extends AuditSectionBase {
  kind: "decisions";
  rows: AuditDecisionRow[];
  counts: AuditDecisionCounts;
  ai?: AuditAiModel;
  showAll: AuditActionModel;
  showLess: AuditActionModel;
}

export interface AuditBuildStat {
  id: string;
  label: string;
  value: number;
  unit: string;
  tone: Tone;
}

export interface AuditBuildSection extends AuditSectionBase {
  kind: "build";
  verification: AuditVerificationModel;
  compileOnly: boolean;
  empty: boolean;
  stats: AuditBuildStat[];
  published: FieldModel[];
  publishedMore?: string;
  unresolved: FieldModel[];
  recovered: FieldModel[];
  components: FieldModel[];
}

export interface AuditDiffSteps {
  added: AuditActionModel[];
  removed: AuditActionModel[];
  changed: AuditActionModel[];
}

export interface AuditDiffSection extends AuditSectionBase {
  kind: "diff";
  baselineName?: string;
  hasDiff: boolean;
  changed: boolean;
  changedTotal: number;
  summary: FieldModel[];
  steps: AuditDiffSteps;
  topology: { added: AuditActionModel[]; removed: AuditActionModel[] };
  bindings: AuditDiffSteps;
  connections: { added: string[]; removed: string[] };
  pin: AuditActionModel;
  clear: AuditActionModel;
  compare: AuditActionModel;
}

export interface AuditDossierSection extends AuditSectionBase {
  kind: "dossier";
  description: string;
  note: string;
  actions: AuditActionModel[];
}

export type AuditSectionModel =
  | AuditSummarySection
  | AuditFindingsSection
  | AuditQuestionsSection
  | AuditCoverageSection
  | AuditDecisionsSection
  | AuditBuildSection
  | AuditDiffSection
  | AuditDossierSection;

export interface AuditHeaderCount {
  id: string;
  label: string;
  value: number;
  detail?: string;
  active?: boolean;
}

export interface AuditSubjectFilterModel {
  subject: AuditSubject | null;
  label: string;
  title: string;
  clear?: AuditActionModel;
}

export interface AuditFilterOptions {
  severities: Severity[];
  statuses: ReviewStatus[];
  rules: string[];
  tags: string[];
}

export interface AuditCommands {
  selectFinding: (findingId: string) => void;
  setStatus: (
    findingId: string,
    status: ReviewStatus,
    note?: string,
  ) => void;
  compareSnapshot: (file: File) => void;
}

export interface AuditModel {
  panel: PanelModel;
  counts: AuditHeaderCount[];
  subject: AuditSubjectFilterModel;
  rails: AuditRailModel[];
  sections: AuditSectionModel[];
  filters: AuditFilterOptions;
  selectedFindingId?: string;
  commands: AuditCommands;
  footer: string;
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

export const SEVERITIES: Severity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

export const REVIEW_STATUSES: ReviewStatus[] = [
  "open",
  "acknowledged",
  "waived",
  "resolved",
];

export function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

function percent(value: number, total: number): number {
  if (total <= 0) return 100;
  return Math.max(0, Math.min(100, (value / total) * 100));
}

function contribution(value: number, weight: number): number {
  return Math.round(value * weight * 10) / 10;
}

function scoreBand(score: number): string {
  if (score >= 85) return "sound";
  if (score >= 65) return "review";
  if (score >= 40) return "needs attention";
  return "thin evidence";
}

export function verificationOf(
  report: BuildReport | undefined,
): AuditVerificationModel {
  const provenance = report?.provenance;
  const mode =
    provenance && typeof provenance === "object"
      ? (provenance as Record<string, unknown>).mode
      : undefined;
  const compileOnly = mode === "compile-only";
  const unresolved = report?.unresolved_failures?.length ?? 0;
  const published = report?.published_artifacts?.length ?? 0;

  if (compileOnly) {
    return {
      state: "compile-only",
      label: "Compile-only",
      detail: "Compiled from source; the graph was not executed.",
      tone: "amber",
    };
  }
  if (unresolved > 0) {
    return {
      state: "failed",
      label: `${formatCount(unresolved)} unresolved`,
      detail: `${formatCount(published)} artifact${
        published === 1 ? "" : "s"
      } published before the failure.`,
      tone: "red",
    };
  }
  if (published > 0) {
    return {
      state: "executed",
      label: "Executed",
      detail: `${formatCount(published)} artifact${
        published === 1 ? "" : "s"
      } published from a graph run.`,
      tone: "green",
    };
  }
  return {
    state: "unknown",
    label: "No build record",
    detail: "No provenance or published artifacts in this snapshot.",
    tone: "neutral",
  };
}

export function subjectText(subject: AuditSubject | undefined): string {
  if (!subject) return "no subject";
  const component = subject.component ?? subject.name;
  if (subject.kind === "property") {
    return `${subject.entityKind ?? "node"} · ${component}.${subject.property ?? ""}`;
  }
  if (subject.kind === "step") {
    return subject.stepId
      ? `step · ${subject.stepId.join("/")}`
      : `step · ${subject.name}`;
  }
  if (subject.kind === "binding") {
    return `binding · ${subject.name}${
      typeof subject.bindingIndex === "number" ? ` #${subject.bindingIndex}` : ""
    }`;
  }
  return `${subject.kind} · ${component}`;
}

/**
 * A node or edge subject selection also covers findings about its properties.
 * A property selection is exact; every other kind compares the subject directly.
 */
export function subjectMatches(
  filter: AuditSubject | undefined,
  subject: AuditSubject | undefined,
): boolean {
  if (!filter) return true;
  if (!subject) return false;
  const filterComponent = filter.component ?? filter.name;
  const subjectComponent = subject.component ?? subject.name;

  if (filter.kind === "property") {
    return (
      subject.kind === "property" &&
      subjectComponent === filterComponent &&
      (!filter.property || subject.property === filter.property) &&
      (!filter.entityKind ||
        !subject.entityKind ||
        subject.entityKind === filter.entityKind)
    );
  }

  if (filter.kind === "node" || filter.kind === "edge") {
    const subjectKind =
      subject.kind === "property" ? subject.entityKind : subject.kind;
    return (
      subjectKind === filter.kind &&
      subjectComponent === filterComponent &&
      (!filter.entityKind || subjectKind === filter.entityKind)
    );
  }

  if (filter.kind === "step") {
    if (subject.kind !== "step") return false;
    if (filter.stepId && subject.stepId) {
      return filter.stepId.join("/") === subject.stepId.join("/");
    }
    return (
      (subject.component ?? subject.name) === filterComponent ||
      subject.name === filter.name
    );
  }

  if (filter.kind === "binding") {
    if (subject.kind !== "binding") return false;
    if (
      typeof filter.bindingIndex === "number" &&
      typeof subject.bindingIndex === "number" &&
      filter.bindingIndex !== subject.bindingIndex
    ) {
      return false;
    }
    return subjectComponent === filterComponent;
  }

  return subject.kind === filter.kind && subjectComponent === filterComponent;
}

function statusOf(
  findingId: string,
  queue: Record<string, ReviewRecord>,
): ReviewStatus {
  return queue[findingId]?.status ?? "open";
}

function failureText(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    for (const key of ["message", "detail", "error", "reason"]) {
      if (typeof record[key] === "string") return record[key] as string;
    }
    try {
      return JSON.stringify(value).slice(0, 300);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function runtimeFieldLabel(field: unknown): string {
  if (typeof field === "string") return field;
  if (field && typeof field === "object") {
    const record = field as Record<string, unknown>;
    const key = typeof record.key === "string" ? record.key : "runtime field";
    const valueType =
      typeof record.value_type === "string" ? record.value_type : "unknown";
    const required = record.required === true ? "required" : "optional";
    return `${key} (${valueType}, ${required})`;
  }
  return String(field);
}

function command(
  action: Omit<AuditActionModel, "kind"> & { kind?: AuditActionKind },
): AuditActionModel {
  return { kind: "command", ...action };
}

function viewAction(
  action: Omit<AuditActionModel, "kind"> & { kind: AuditActionKind },
): AuditActionModel {
  return action;
}

function baselineNameOf(record: {
  baseline: ViewerSnapshot | null;
}): string | undefined {
  return record.baseline?.title ?? record.baseline?.name;
}

// ---------------------------------------------------------------------------
// Builder
// ---------------------------------------------------------------------------

export function buildAuditModel(
  campaign: CampaignView,
  input: AuditInput,
): AuditModel {
  const { record, commands } = campaign;
  const {
    index,
    audit,
    coverage,
    decisions,
    queue,
    queueSummary,
  } = record;
  const subjectFilter = input.subjectFilter;
  const selectedFindingId = input.selectedFindingId;
  const findings = audit?.findings ?? [];
  const questions = audit?.questions ?? [];
  const baselineName = baselineNameOf(record);
  const diff = record.diff;
  const review = record.review;

  const filterName = subjectFilter?.component ?? subjectFilter?.name;
  const filterLabel = subjectFilter
    ? subjectFilter.property
      ? `${subjectFilter.kind} ${filterName}.${subjectFilter.property}`
      : `${subjectFilter.kind} ${filterName}`
    : "";

  const filteredFindings = findings.filter((finding) =>
    subjectMatches(subjectFilter, finding.subject),
  );
  const filteredQuestions = questions.filter((finding) =>
    subjectMatches(subjectFilter, finding.subject),
  );

  const openDecisions = decisions.filter(
    (decision) => decision.status === "open",
  ).length;
  const reviewed = Math.max(0, queueSummary.total - queueSummary.open);
  const reviewedPercent = percent(reviewed, queueSummary.total);

  // ---- Summary -----------------------------------------------------------

  const score = Math.max(0, Math.min(100, audit?.score.value ?? 0));
  const components: AuditRubricRow[] = (audit?.score.components ?? []).map(
    (component) => ({
      id: `rubric-${component.id}`,
      testId: `rubric-${component.id}`,
      label: component.label,
      title: component.detail,
      componentId: component.id,
      detail: component.detail,
      raw: component.value,
      weight: component.weight,
      contribution: contribution(component.value, component.weight),
      fields: [
        { id: "raw", label: "raw", value: String(component.value) },
        { id: "weight", label: "w", value: String(component.weight) },
        {
          id: "contribution",
          label: "v × w",
          value: String(contribution(component.value, component.weight)),
        },
      ],
    }),
  );

  const legend: AuditLegendModel[] = SEVERITIES.map((severity) => ({
    severity,
    count: audit?.counts[severity] ?? 0,
    testId: `severity-${severity}`,
  }));

  const verification = verificationOf(index.snapshot.report);

  const summary: AuditSummarySection = {
    id: "summary",
    kind: "summary",
    title: "Summary",
    question: "is the model trustworthy?",
    count: `${formatCount(score)} / 100`,
    testId: "review-summary",
    toggleTestId: "summary-section-toggle",
    railTestId: "review-rail-summary",
    icon: "audit",
    layout: "full",
    collapsible: true,
    defaultOpen: true,
    score,
    band: scoreBand(score),
    ticks: [0, 40, 65, 85, 100],
    components,
    rows: components,
    observations: findings.length,
    queueOpen: queueSummary.open,
    verification,
    legend,
    queue: queueSummary,
    reviewed,
    reviewedPercent,
    fields: [
      {
        id: "score",
        label: "weighted score",
        value: `${formatCount(score)} / 100`,
        tone: "accent",
      },
      {
        id: "observations",
        label: "observations",
        value: formatCount(findings.length),
      },
      {
        id: "queue-open",
        label: "queue open",
        value: formatCount(queueSummary.open),
        tone: "accent",
      },
      {
        id: "verification",
        label: "verification",
        value: `${verification.label} · ${verification.detail}`,
      },
      ...legend.map((entry) => ({
        id: `severity-${entry.severity}`,
        label: entry.severity,
        value: formatCount(entry.count),
        tone: entry.severity,
      })),
      {
        id: "queue-progress",
        label: "reviewed",
        value: `${formatCount(reviewed)} / ${formatCount(
          queueSummary.total,
        )} · ${formatCount(queueSummary.open)} open`,
      },
    ],
  };

  // ---- Findings ----------------------------------------------------------

  const findingRows: AuditFindingRow[] = filteredFindings.map((finding) => {
    const rowStatus = statusOf(finding.id, queue);
    const recordNote = queue[finding.id]?.note;

    return {
      id: `finding-${finding.id}`,
      testId: `finding-${finding.id}`,
      label: finding.title,
      tone: finding.severity,
      selected: selectedFindingId === finding.id,
      findingId: finding.id,
      severity: finding.severity,
      rule: finding.rule,
      status: rowStatus,
      tags: finding.tags,
      question: finding.question,
      evidenceCount: finding.evidence.length,
      note: recordNote,
      subject: finding.subject,
      subjectLabel: subjectText(finding.subject),
      impact: () => {
        if (!finding.subject) return undefined;
        const impact = computeImpact(index, finding.subject);
        return {
          label: `${
            typeof impact.records === "number" ? `${impact.records} rec · ` : ""
          }↑${impact.upstream.length} ↓${impact.downstream.length}${
            impact.targets.length ? ` · ${impact.targets.join("/")}` : ""
          }`,
          title: `${impact.upstream.length} upstream, ${
            impact.downstream.length
          } downstream, targets: ${impact.targets.join(", ") || "none"}`,
        };
      },
      fields: [
        {
          id: "evidence",
          label: "evidence",
          value: formatCount(finding.evidence.length),
        },
      ],
      acknowledge: command({
        id: `ack-${finding.id}`,
        testId: `ack-${finding.id}`,
        label:
          rowStatus === "acknowledged" ? "Acknowledged" : "Acknowledge",
        icon: "check",
        pressed: rowStatus === "acknowledged",
        run: () => commands.setReviewStatus(finding.id, "acknowledged"),
      }),
      waive: viewAction({
        id: `waive-${finding.id}`,
        testId: `waive-${finding.id}`,
        label: "Waive",
        icon: "warning",
        kind: "waive",
      }),
      openSubject: finding.subject
        ? command({
            id: `open-subject-${finding.id}`,
            label: subjectText(finding.subject),
            icon: "open",
            title: `Open ${subjectText(finding.subject)} in Explorer`,
            run: () => commands.openReview(finding.subject as AuditSubject),
          })
        : undefined,
    };
  });

  const findingsSection: AuditFindingsSection = {
    id: "findings",
    kind: "findings",
    title: "Findings",
    question: "what is wrong?",
    count: `${formatCount(findingRows.length)} shown`,
    testId: "findings-panel",
    toggleTestId: "findings-section-toggle",
    railTestId: "review-rail-findings",
    icon: "warning",
    layout: "left",
    collapsible: true,
    defaultOpen: true,
    rows: findingRows,
    totalFindings: findings.length,
    rules: [...new Set(findings.map((finding) => finding.rule))].sort(),
    tags: [...new Set(findings.flatMap((finding) => finding.tags))].sort(),
    queue: queueSummary,
    reviewed,
    reviewedPercent,
    showAll: viewAction({
      id: "findings-load-more",
      testId: "findings-load-more",
      label: "Show all",
      kind: "show-all",
    }),
    showLess: viewAction({
      id: "findings-show-less",
      testId: "findings-show-less",
      label: "Show less",
      kind: "show-less",
    }),
    actions: [],
  };

  // ---- Questions ---------------------------------------------------------

  const questionRows: AuditQuestionRow[] = filteredQuestions.map((finding) => {
    const rowStatus = statusOf(finding.id, queue);
    return {
      id: `question-${finding.id}`,
      testId: `question-${finding.id}`,
      label: finding.title,
      tone: finding.severity,
      findingId: finding.id,
      rule: finding.rule,
      status: rowStatus,
      evidenceCount: finding.evidence.length,
      question: finding.question ?? finding.title,
      subject: finding.subject,
      subjectLabel: subjectText(finding.subject),
      fields: [
        {
          id: "evidence",
          label: "evidence",
          value: formatCount(finding.evidence.length),
        },
      ],
      openSubject: finding.subject
        ? command({
            id: `question-open-${finding.id}`,
            testId: `question-open-${finding.id}`,
            label: subjectText(finding.subject),
            icon: "open",
            title: `Open ${subjectText(finding.subject)} in Explorer`,
            run: () => commands.openReview(finding.subject as AuditSubject),
          })
        : undefined,
      acknowledge: command({
        id: `question-ack-${finding.id}`,
        testId: `question-ack-${finding.id}`,
        label:
          rowStatus === "acknowledged" ? "Acknowledged" : "Acknowledge",
        icon: "check",
        pressed: rowStatus === "acknowledged",
        run: () => commands.setReviewStatus(finding.id, "acknowledged"),
      }),
    };
  });

  const questionsSection: AuditQuestionsSection = {
    id: "questions",
    kind: "questions",
    title: "Questions",
    question: "what is unresolved?",
    count: `${formatCount(questionRows.length)} question${
      questionRows.length === 1 ? "" : "s"
    }`,
    testId: "design-questions",
    toggleTestId: "questions-section-toggle",
    railTestId: "review-rail-questions",
    icon: "question",
    layout: "left",
    collapsible: true,
    defaultOpen: true,
    rows: questionRows,
    showMore: viewAction({
      id: "questions-load-more",
      testId: "questions-load-more",
      label: "Show more",
      icon: "expand",
      kind: "show-more",
    }),
    actions: [],
  };

  // ---- Coverage ----------------------------------------------------------

  const coverageRows: AuditCoverageRow[] = (coverage?.rows ?? []).map((row) => {
    const key = `${row.kind}:${row.component}.${row.property}`;
    const open = command({
      id: `coverage-open-${row.component}-${row.property}`,
      label: `${row.component}.${row.property}`,
      title: `Open ${row.kind} ${row.component}.${row.property}`,
      run: () =>
        commands.selectProperty(row.kind, row.component, row.property),
    });
    return {
      id: key,
      label: `${row.component}.${row.property}`,
      meta: `${formatCount(row.tracedFields)}f / ${formatCount(row.literals)}l`,
      tone: row.cells.length ? "neutral" : "low",
      key,
      entityKind: row.kind,
      component: row.component,
      property: row.property,
      tracedFields: row.tracedFields,
      literals: row.literals,
      cells: row.cells.map((cell) => ({
        source: cell.source,
        fields: cell.fields,
        literals: cell.literals,
        bindings: cell.bindings,
        open: command({
          id: `coverage-cell-${row.component}-${row.property}-${cell.source}`,
          testId: `coverage-cell-${row.component}-${row.property}-${cell.source}`,
          label: `${cell.fields}f ${cell.literals}l ${cell.bindings}b`,
          title: `${row.component}.${row.property} ← ${cell.source}\n${cell.fields} traced field(s) · ${cell.literals} literal(s) · ${cell.bindings} binding(s)\nClick to open the property.`,
          run: () =>
            commands.selectProperty(
              row.kind,
              row.component,
              row.property,
              cell.source,
            ),
        }),
      })),
      open,
    };
  });

  const coverageSection: AuditCoverageSection = {
    id: "coverage",
    kind: "coverage",
    title: "Coverage",
    question: "what is untested?",
    count: `${formatCount(coverageRows.length)} rows · ${formatCount(
      coverage?.sources.length ?? 0,
    )} src`,
    testId: "coverage-matrix",
    toggleTestId: "coverage-section-toggle",
    railTestId: "review-rail-coverage",
    icon: "layers",
    layout: "right",
    collapsible: true,
    defaultOpen: true,
    sources: coverage?.sources ?? [],
    rows: coverageRows,
    showAll: viewAction({
      id: "coverage-show-all",
      testId: "coverage-show-all",
      label: "Show all",
      kind: "show-all",
    }),
    showLess: viewAction({
      id: "coverage-show-less",
      testId: "coverage-show-less",
      label: "Show less",
      kind: "show-less",
    }),
    fields: [
      {
        id: "coverage-rows",
        label: "rows",
        value: formatCount(coverageRows.length),
      },
      {
        id: "coverage-sources",
        label: "sources",
        value: formatCount(coverage?.sources.length ?? 0),
      },
    ],
    actions: [],
  };

  // ---- Decisions ---------------------------------------------------------

  const decisionOrdered = orderDecisions(decisions);
  const decisionCounts: AuditDecisionCounts = {
    sidecar: decisions.filter((decision) => decision.source === "sidecar").length,
    derived: decisions.filter((decision) => decision.source !== "sidecar").length,
    rationaleSupplied: decisions.filter(
      (decision) => decision.rationaleSupplied,
    ).length,
    rationaleMissing: decisions.filter(
      (decision) => !decision.rationaleSupplied,
    ).length,
    open: openDecisions,
  };

  const decisionRows: AuditDecisionRow[] = decisionOrdered.map((decision) => ({
    id: `decision-${decision.id}`,
    testId: `decision-${decision.id}`,
    label: decision.title,
    decisionId: decision.id,
    status: decision.status,
    source: decision.source,
    rationaleSupplied: decision.rationaleSupplied,
    rationale: decision.rationale,
    tags: decision.tags ?? [],
    evidence: decision.evidence,
    subject: decision.subject,
    subjectLabel: subjectText(decision.subject),
    fields: [
      {
        id: "evidence",
        label: "evidence",
        value: formatCount(decision.evidence.length),
      },
    ],
    openSubject: decision.subject
      ? command({
          id: `decision-open-${decision.id}`,
          testId: `decision-open-${decision.id}`,
          label: subjectText(decision.subject),
          icon: "open",
          title: `Open ${subjectText(decision.subject)} in Explorer`,
          run: () => commands.openReview(decision.subject as AuditSubject),
        })
      : undefined,
  }));

  const ai = review?.ai;
  const hasAi = Boolean(
    ai && (ai.model || ai.runId || ai.generatedAt || ai.note),
  );

  const decisionsSection: AuditDecisionsSection = {
    id: "decisions",
    kind: "decisions",
    title: "Decisions",
    question: "what did we decide?",
    count: `${formatCount(decisions.length)} cards · ${formatCount(
      openDecisions,
    )} open`,
    testId: "decision-ledger",
    toggleTestId: "decision-section-toggle",
    railTestId: "review-rail-decisions",
    icon: "review",
    layout: "full-tail",
    collapsible: true,
    defaultOpen: true,
    rows: decisionRows,
    counts: decisionCounts,
    ai: hasAi && ai ? { ...ai, testId: "ai-provenance" } : undefined,
    showAll: viewAction({
      id: "decision-show-all",
      testId: "decision-show-all",
      label: "Show all",
      kind: "show-all",
    }),
    showLess: viewAction({
      id: "decision-show-less",
      testId: "decision-show-less",
      label: "Show less",
      kind: "show-less",
    }),
    fields: [
      {
        id: "sidecar",
        label: "sidecar",
        value: formatCount(decisionCounts.sidecar),
      },
      {
        id: "derived",
        label: "derived",
        value: formatCount(decisionCounts.derived),
      },
      {
        id: "rationale",
        label: "rationale",
        value: formatCount(decisionCounts.rationaleSupplied),
        tone: "info",
      },
      {
        id: "missing",
        label: "missing",
        value: formatCount(decisionCounts.rationaleMissing),
        tone: "medium",
      },
    ],
    actions: [],
  };

  // ---- Build health ------------------------------------------------------

  const report = index.snapshot.report;
  const published = report?.published_artifacts ?? [];
  const recovered = report?.recovered_failures ?? [];
  const unresolved = report?.unresolved_failures ?? [];
  const workflowComponents = index.workflow.components ?? [];
  const compileOnly = verification.state === "compile-only";
  const completelyEmpty =
    published.length === 0 &&
    recovered.length === 0 &&
    unresolved.length === 0 &&
    workflowComponents.length === 0;

  const publishedFields: FieldModel[] = published.slice(0, 6).map(
    (artifact, position) => ({
      id: `published-${position}`,
      label: `${position + 1}`,
      value: `${artifact.type.join(".")} · ${artifact.opening.join(" / ")}`,
      title: `${artifact.type.join(".")}\n${artifact.opening.join(" / ")}`,
    }),
  );

  const unresolvedFields: FieldModel[] = unresolved.map((failure, position) => {
    const text = failureText(failure);
    return {
      id: `unresolved-${position}`,
      label: `#${position + 1}`,
      value: text,
      title: text,
      tone: "critical",
    };
  });

  const recoveredFields: FieldModel[] = recovered.map((failure, position) => {
    const text = failureText(failure);
    return {
      id: `recovered-${position}`,
      label: `#${position + 1}`,
      value: text,
      title: text,
      tone: "medium",
    };
  });

  const componentFields: FieldModel[] = workflowComponents.map((component) => {
    const fields = (component.runtime_fields ?? []).map(runtimeFieldLabel);
    return {
      id: `component-${component.id}`,
      label: component.id,
      value: `v${component.version ?? "—"} · ${
        fields.join(", ") || "no runtime fields"
      }`,
      title: `${component.id}\nversion ${
        component.version ?? "—"
      }\nruntime fields: ${fields.join(", ") || "—"}`,
    };
  });

  const buildSection: AuditBuildSection = {
    id: "build",
    kind: "build",
    title: "Build",
    question: "did it publish?",
    count: `${formatCount(published.length)} published`,
    testId: "build-health",
    toggleTestId: "build-health-section-toggle",
    railTestId: "review-rail-build",
    icon: "workflow",
    layout: "full-tail",
    collapsible: true,
    defaultOpen: true,
    verification,
    compileOnly,
    empty: completelyEmpty,
    stats: [
      {
        id: "published",
        label: "published",
        value: published.length,
        unit: "artifacts",
        tone: "info",
      },
      {
        id: "recovered",
        label: "recovered",
        value: recovered.length,
        unit: "failures",
        tone: "medium",
      },
      {
        id: "unresolved",
        label: "unresolved",
        value: unresolved.length,
        unit: "failures",
        tone: "critical",
      },
    ],
    published: publishedFields,
    publishedMore:
      published.length > publishedFields.length
        ? `+${formatCount(published.length - publishedFields.length)} more`
        : undefined,
    unresolved: unresolvedFields,
    recovered: recoveredFields,
    components: componentFields,
    fields: [
      {
        id: "verification",
        label: "verification",
        value: `${verification.label} · ${verification.detail}`,
      },
      {
        id: "published",
        label: "published",
        value: formatCount(published.length),
      },
      {
        id: "recovered",
        label: "recovered",
        value: formatCount(recovered.length),
      },
      {
        id: "unresolved",
        label: "unresolved",
        value: formatCount(unresolved.length),
      },
    ],
    actions: [],
  };

  // ---- Diff --------------------------------------------------------------

  const changed = diff ? hasChanges(diff) : false;
  const diffItems: Array<[string, number, Tone]> = diff
    ? [
        ["steps +", diff.summary.stepsAdded, "accent"],
        ["steps -", diff.summary.stepsRemoved, "critical"],
        ["steps ~", diff.steps.changed.length, "info"],
        ["connections +", diff.summary.connectionsAdded, "accent"],
        ["connections -", diff.summary.connectionsRemoved, "critical"],
        ["nodes +", diff.summary.nodesAdded, "accent"],
        ["nodes -", diff.summary.nodesRemoved, "critical"],
        ["edges +", diff.summary.edgesAdded, "accent"],
        ["edges -", diff.summary.edgesRemoved, "critical"],
        ["bindings +", diff.summary.bindingsAdded, "accent"],
        ["bindings -", diff.summary.bindingsRemoved, "critical"],
        ["properties ~", diff.summary.propertiesChanged, "info"],
      ]
    : [];
  const diffSummary: FieldModel[] = diffItems.map(([label, value, tone]) => ({
    id: label,
    label,
    value: formatCount(value),
    tone: value ? tone : "info",
  }));
  const changedTotal = diffItems.reduce((total, [, value]) => total + value, 0);

  const topologySubject = (name: string): AuditSubject => {
    if (
      index.topologyEdgesByName.has(name) &&
      !index.topologyNodesByName.has(name)
    ) {
      return { kind: "edge", name, component: name, entityKind: "edge" };
    }
    return { kind: "node", name, component: name, entityKind: "node" };
  };

  const bindingSubject = (bindingIndex: number): AuditSubject | undefined => {
    const binding = index.bindings.find(
      (candidate) => candidate.index === bindingIndex,
    );
    if (!binding) return undefined;
    return {
      kind: "binding",
      name: binding.component,
      component: binding.component,
      entityKind: binding.kind,
      bindingIndex: binding.index,
    };
  };

  const stepAction = (step: StepId, prefix: string): AuditActionModel =>
    command({
      id: `step-${prefix}-${step[0]}-${step[1]}`,
      label: `${step[0]}/${step[1]}`,
      title: `${prefix} ${step[0]}/${step[1]}`,
      run: () =>
        commands.openReview({
          kind: "step",
          name: `${step[0]}/${step[1]}`,
          component: step[0],
          stepId: [step[0], step[1]],
        }),
    });

  const topologyAction = (
    name: string,
    direction: "added" | "removed",
  ): AuditActionModel =>
    command({
      id: `topology-${direction}-${name}`,
      label: name,
      tone: direction === "added" ? "accent" : "critical",
      run: () => commands.openReview(topologySubject(name)),
    });

  const bindingAction = (
    bindingIndex: number,
    direction: string,
  ): AuditActionModel => {
    const subject = bindingSubject(bindingIndex);
    return command({
      id: `binding-${direction}-${bindingIndex}`,
      label: `#${bindingIndex}`,
      run: subject ? () => commands.openReview(subject) : undefined,
    });
  };

  const diffSection: AuditDiffSection = {
    id: "diff",
    kind: "diff",
    title: "Diff",
    question: "what changed?",
    count: diff ? `${formatCount(changedTotal)} changed` : "no baseline",
    testId: "snapshot-diff",
    toggleTestId: "snapshot-diff-section-toggle",
    railTestId: "review-rail-diff",
    icon: "branch",
    layout: "full-tail",
    collapsible: true,
    defaultOpen: true,
    baselineName,
    hasDiff: Boolean(diff),
    changed,
    changedTotal,
    summary: diffSummary,
    fields: [
      ...(baselineName
        ? [{ id: "baseline", label: "baseline", value: baselineName }]
        : []),
      ...diffSummary,
    ],
    steps: {
      added: diff?.steps.added.map((step) => stepAction(step, "added")) ?? [],
      removed:
        diff?.steps.removed.map((step) => stepAction(step, "removed")) ?? [],
      changed:
        diff?.steps.changed.map((step) => stepAction(step, "changed")) ?? [],
    },
    topology: {
      added:
        diff?.topology.added.map((name) => topologyAction(name, "added")) ?? [],
      removed:
        diff?.topology.removed.map((name) =>
          topologyAction(name, "removed"),
        ) ?? [],
    },
    bindings: {
      added:
        diff?.bindings.added.map((index) =>
          bindingAction(index, "added"),
        ) ?? [],
      removed:
        diff?.bindings.removed.map((index) =>
          bindingAction(index, "removed"),
        ) ?? [],
      changed:
        diff?.bindings.changed.map((index) =>
          bindingAction(index, "changed"),
        ) ?? [],
    },
    connections: {
      added: diff?.connections.added ?? [],
      removed: diff?.connections.removed ?? [],
    },
    pin: command({
      id: "pin-baseline",
      testId: "pin-baseline",
      label: baselineName ? "Re-pin current" : "Pin current",
      icon: "focus",
      run: () => commands.pinBaseline(),
    }),
    clear: command({
      id: "clear-baseline",
      testId: "clear-baseline",
      label: "Clear",
      icon: "collapse",
      disabled: !baselineName,
      run: () => commands.clearBaseline(),
    }),
    compare: viewAction({
      id: "compare-input",
      testId: "compare-input",
      label: "Compare…",
      icon: "branch",
      kind: "compare",
    }),
    actions: [],
  };

  // ---- Dossier -----------------------------------------------------------

  const dossierActions: AuditActionModel[] = [
    command({
      id: "dossier-export-markdown",
      testId: "dossier-export-markdown",
      label: "Export Markdown",
      hint: "Download the human-readable review.",
      icon: "read",
      primary: true,
      run: () => commands.exportDossier("markdown"),
    }),
    command({
      id: "dossier-export-json",
      testId: "dossier-export-json",
      label: "Export JSON",
      hint: "Download the machine-readable review.",
      icon: "code",
      run: () => commands.exportDossier("json"),
    }),
    command({
      id: "dossier-copy-markdown",
      testId: "dossier-copy-markdown",
      label: "Copy Markdown",
      hint: "Copy the human-readable review.",
      icon: "copy",
      run: () => commands.copyDossier("markdown"),
    }),
    command({
      id: "dossier-copy-json",
      testId: "dossier-copy-json",
      label: "Copy JSON",
      hint: "Copy the machine-readable review.",
      icon: "copy",
      run: () => commands.copyDossier("json"),
    }),
  ];

  const dossierSection: AuditDossierSection = {
    id: "dossier",
    kind: "dossier",
    title: "Dossier",
    question: "what do we hand over?",
    count: "4 outputs",
    testId: "dossier-panel",
    toggleTestId: "dossier-section-toggle",
    railTestId: "review-rail-dossier",
    icon: "import",
    layout: "full-tail",
    collapsible: true,
    defaultOpen: true,
    description:
      "Export or copy the complete review dossier. Markdown is for a human hand-off; JSON is the machine-readable equivalent.",
    note: "The dossier records findings, questions, decisions, build health, the snapshot diff and the review queue. It adds no generated rationale and no preview is drawn here.",
    actions: dossierActions,
    rows: [],
    fields: [{ id: "outputs", label: "outputs", value: "4" }],
  };

  const sections: AuditSectionModel[] = [
    summary,
    findingsSection,
    questionsSection,
    coverageSection,
    decisionsSection,
    buildSection,
    diffSection,
    dossierSection,
  ];

  const rails: AuditRailModel[] = sections.map((section) => ({
    id: section.id,
    label: section.title,
    question: section.question,
    icon: section.icon,
    target: section.testId,
    testId: section.railTestId,
    // A rail entry indexes its section. The full body stays in AuditModel.sections.
    sections: [
      {
        id: section.id,
        title: section.title,
        question: section.question,
        ...(section.count !== undefined ? { count: section.count } : {}),
      },
    ],
  }));

  const filters: AuditFilterOptions = {
    severities: SEVERITIES,
    statuses: REVIEW_STATUSES,
    rules: [...new Set(findings.map((finding) => finding.rule))].sort(),
    tags: [...new Set(findings.flatMap((finding) => finding.tags))].sort(),
  };

  return {
    panel: {
      id: "audit",
      title: "Audit",
      meta: "findings · coverage · decisions",
      question: "what does the build claim, and what supports it?",
      icon: "audit",
      rails,
    },
    counts: [
      {
        id: "findings",
        label: "findings",
        value: findings.length,
      },
      {
        id: "questions",
        label: "questions",
        value: questions.length,
      },
      {
        id: "decisions",
        label: "decisions",
        value: decisions.length,
        detail: openDecisions ? `${formatCount(openDecisions)} open` : undefined,
      },
      {
        id: "open-findings",
        label: "open findings",
        value: queueSummary.open,
        active: true,
      },
    ],
    subject: {
      subject: subjectFilter ?? null,
      label: subjectFilter ? filterLabel : "all",
      title: subjectFilter ? filterLabel : "All audit subjects",
      clear: subjectFilter
        ? command({
            id: "clear-subject-filter",
            testId: "clear-subject-filter",
            label: "Clear subject filter",
            icon: "reset",
            title: "Clear subject filter",
            run: input.onClearSubjectFilter,
          })
        : undefined,
    },
    rails,
    sections,
    filters,
    selectedFindingId,
    commands: {
      selectFinding: commands.selectFinding,
      setStatus: commands.setReviewStatus,
      compareSnapshot: commands.compareSnapshot,
    },
    footer:
      "Deterministic review surface. No build is executed and no network call is made. Findings are observations, not proof of correctness.",
  };
}

// ---------------------------------------------------------------------------
// Section-specific ordering
// ---------------------------------------------------------------------------

/**
 * Keep every sidecar and open decision in the first page; the remaining
 * derived decisions are the bounded tail.
 */
function orderDecisions(decisions: DecisionView[]): DecisionView[] {
  const sidecar = decisions.filter(
    (decision) => decision.source === "sidecar",
  );
  const openDerived = decisions.filter(
    (decision) => decision.source !== "sidecar" && decision.status === "open",
  );
  const rest = decisions.filter(
    (decision) => decision.source !== "sidecar" && decision.status !== "open",
  );
  return [...sidecar, ...openDerived, ...rest];
}
