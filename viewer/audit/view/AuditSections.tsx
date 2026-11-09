"use client";

import { useMemo } from "react";
import type { ReactNode } from "react";
import {
  AlertOctagon,
  CheckCircle2,
  CircleAlert,
  CircleSlash,
  Database,
  FileSearch,
  HelpCircle,
  Pin,
  Play,
  ShieldAlert,
  SlidersHorizontal,
  X,
} from "lucide-react";
import type { EvidenceRef } from "@/lib/reviewTypes";
import type { FieldModel } from "@/shared/model/hierarchy";
import { Row } from "@/shared/ui/Row";
import { cx } from "@/shared/ui/theme";
import { AUDIT_BOUNDS } from "@/audit/view/bounds";
import {
  ActionButton,
  AuditIcon,
  EmptyState,
  SeverityDot,
  toneText,
  verificationText,
} from "@/audit/view/AuditControls";
import {
  formatCount,
  type AuditBuildSection,
  type AuditCoverageSection,
  type AuditDecisionRow,
  type AuditDecisionsSection,
  type AuditDiffSection,
  type AuditDossierSection,
  type AuditFilterOptions,
  type AuditFindingRow,
  type AuditFindingsSection,
  type AuditQuestionRow,
  type AuditQuestionsSection,
  type AuditSummarySection,
} from "@/audit/model/AuditModel";

// ---------------------------------------------------------------------------
// Shared row vocabulary
// ---------------------------------------------------------------------------

const STATUS_DOT: Record<string, string> = {
  open: "bg-accent",
  acknowledged: "bg-medium",
  waived: "bg-faint",
  resolved: "bg-asset",
  proposed: "bg-medium",
  accepted: "bg-asset",
  rejected: "bg-critical",
};

/** A subject/evidence separator, never a border between rows. */
function Sep() {
  return (
    <span aria-hidden className="select-none text-faint">
      ·
    </span>
  );
}

function StatusMark({ status }: { status: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-faint">
      <span
        aria-hidden
        className={cx(
          "inline-block size-1.5 rounded-full",
          STATUS_DOT[status] ?? "bg-faint",
        )}
      />
      {status}
    </span>
  );
}

/** One label/value pair in a Build, Diff or Dossier body. */
function ValueRow({
  label,
  value,
  title,
  tone,
}: {
  label: ReactNode;
  value: ReactNode;
  title?: string;
  tone?: string;
}) {
  return (
    <div
      data-level="field"
      title={title}
      className="grid grid-cols-[minmax(72px,110px)_minmax(0,1fr)] items-baseline gap-3 py-0.5"
    >
      <span className="truncate text-[11px] text-faint">{label}</span>
      <span
        className={cx(
          "min-w-0 font-mono text-[11.5px] leading-relaxed text-text",
          tone,
        )}
      >
        {value}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export function SummaryBody({ section }: { section: AuditSummarySection }) {
  return (
    <div className="grid grid-cols-1 divide-y divide-line-soft min-[1100px]:grid-cols-[minmax(200px,0.7fr)_minmax(0,1.55fr)_minmax(260px,0.85fr)] min-[1100px]:divide-x min-[1100px]:divide-y-0">
      {/* The verdict: one number, one band, one meter. */}
      <div className="flex min-w-0 flex-col gap-3 p-3">
        <div>
          <p className="text-[11px] text-faint">Weighted score</p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-mono text-[30px] leading-none font-medium text-accent tabular-nums">
              {formatCount(section.score)}
            </span>
            <span className="text-[12px] text-faint">/ 100</span>
            <span className="ml-auto text-[11px] text-faint">
              Band <span className="text-[12px] text-muted">{section.band}</span>
            </span>
          </div>
        </div>

        <div>
          <div
            role="meter"
            aria-label={`Audit score ${section.score} of 100`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={section.score}
            className="relative h-1.5 overflow-hidden rounded-[2px] bg-inset"
          >
            <span
              className="block h-full rounded-[2px] bg-accent"
              style={{ width: `${section.score}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between font-mono text-[10.5px] text-faint tabular-nums">
            {section.ticks.map((tick) => (
              <span key={tick}>{tick}</span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <div>
            <p className="text-[11px] text-faint">Observations</p>
            <p className="font-mono text-[12px] text-text tabular-nums">
              {formatCount(section.observations)}
            </p>
          </div>
          <div>
            <p className="text-[11px] text-faint">Queue open</p>
            <p className="font-mono text-[12px] text-accent tabular-nums">
              {formatCount(section.queueOpen)}
            </p>
          </div>
        </div>
      </div>

      {/* The argument: every weighted component, with its basis. */}
      <div className="min-w-0 p-3">
        <div className="flex items-baseline justify-between gap-2">
          <p className="text-[11px] text-faint">Rubric components</p>
          <p className="font-mono text-[10.5px] text-faint tabular-nums">
            {formatCount(section.components.length)} weighted
          </p>
        </div>
        {section.components.length ? (
          <>
            <div className="mt-1 grid grid-cols-[minmax(0,1fr)_46px_44px_52px] items-center gap-2 border-b border-line-soft pb-1 text-[10.5px] text-faint">
              <span>Component</span>
              <span className="text-right">Raw</span>
              <span className="text-right">Weight</span>
              <span className="text-right">Value</span>
            </div>
            <div>
              {section.components.map((component) => (
                <Row
                  key={component.componentId}
                  data-testid={component.testId}
                  title={component.detail}
                  className="grid h-7 grid-cols-[minmax(0,1fr)_46px_44px_52px] items-center gap-2 py-0"
                >
                  <div className="min-w-0 leading-tight">
                    <span className="block truncate text-[12px] text-text">
                      {component.label}
                    </span>
                    <span className="block truncate text-[10.5px] text-faint">
                      {component.detail}
                    </span>
                  </div>
                  <span className="text-right font-mono text-[11px] text-muted tabular-nums">
                    {component.raw}
                  </span>
                  <span className="text-right font-mono text-[11px] text-faint tabular-nums">
                    {component.weight}
                  </span>
                  <span className="text-right font-mono text-[11px] text-accent tabular-nums">
                    {component.contribution}
                  </span>
                </Row>
              ))}
            </div>
          </>
        ) : (
          <EmptyState>
            No rubric components recorded for this snapshot.
          </EmptyState>
        )}
      </div>

      {/* The support: verification, severity legend and queue state. */}
      <div className="min-w-0 p-3">
        <div data-testid="audit-verification" className="flex items-start gap-2">
          <span
            aria-hidden
            className={cx(
              "mt-1 size-1.5 shrink-0 rounded-full bg-current",
              verificationText(section.verification.tone),
            )}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[11px] text-faint">Verification</span>
              <span
                className={cx(
                  "text-[12px] font-medium",
                  verificationText(section.verification.tone),
                )}
              >
                {section.verification.label}
              </span>
            </div>
            <p className="mt-0.5 text-[11px] leading-snug text-muted">
              {section.verification.detail}
            </p>
          </div>
        </div>

        <div className="mt-3">
          <p className="text-[11px] text-faint">Severity</p>
          <div className="mt-0.5">
            {section.legend.map((entry) => (
              <Row
                key={entry.severity}
                data-testid={entry.testId}
                className="h-6 py-0"
              >
                <SeverityDot severity={entry.severity} />
                <span className="min-w-0 flex-1 truncate text-[11px] text-muted">
                  {entry.severity}
                </span>
                <span className="font-mono text-[11px] text-faint tabular-nums">
                  {formatCount(entry.count)}
                </span>
              </Row>
            ))}
          </div>
        </div>

        <div
          data-testid="queue-progress"
          role="progressbar"
          aria-label="Review queue progress"
          aria-valuemin={0}
          aria-valuemax={section.queue.total}
          aria-valuenow={section.reviewed}
          className="mt-3 border-t border-line-soft pt-2"
        >
          <div className="flex items-baseline justify-between gap-2 text-[11px]">
            <span className="text-faint">Reviewed</span>
            <span className="font-mono text-text tabular-nums">
              {formatCount(section.reviewed)} /{" "}
              {formatCount(section.queue.total)}
            </span>
            <span className="font-mono text-accent tabular-nums">
              {formatCount(section.queue.open)} open
            </span>
          </div>
          <div className="mt-1 h-1 overflow-hidden rounded-[2px] bg-panel-soft">
            <div
              className="h-full bg-accent/80 transition-[width]"
              style={{ width: `${section.reviewedPercent}%` }}
            />
          </div>
          <div className="mt-1 grid grid-cols-4 gap-1 font-mono text-[10.5px] tabular-nums">
            <span className="text-accent">open {section.queue.open}</span>
            <span className="text-medium">
              ack {section.queue.acknowledged}
            </span>
            <span className="text-muted">waive {section.queue.waived}</span>
            <span className="text-asset">done {section.queue.resolved}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Findings
// ---------------------------------------------------------------------------

export interface FindingsBodyProps {
  section: AuditFindingsSection;
  rows: AuditFindingRow[];
  filters: AuditFilterOptions;
  severityFilter: string;
  ruleFilter: string;
  statusFilter: string;
  tagFilter: string;
  activeFilters: number;
  subjectLabel: string;
  subjectFiltered: boolean;
  selectedFindingId?: string;
  onSeverityFilter: (value: string) => void;
  onRuleFilter: (value: string) => void;
  onStatusFilter: (value: string) => void;
  onTagFilter: (value: string) => void;
  onClearFilters: () => void;
  onSelectFinding: (id: string) => void;
  waivingId?: string;
  draftNote: string;
  onDraftNote: (value: string) => void;
  onStartWaiver: (row: AuditFindingRow) => void;
  onSaveWaiver: (row: AuditFindingRow) => void;
  onCancelWaiver: () => void;
}

export function FindingsBody({
  section,
  rows,
  filters,
  severityFilter,
  ruleFilter,
  statusFilter,
  tagFilter,
  activeFilters,
  subjectLabel,
  subjectFiltered,
  selectedFindingId,
  onSeverityFilter,
  onRuleFilter,
  onStatusFilter,
  onTagFilter,
  onClearFilters,
  onSelectFinding,
  waivingId,
  draftNote,
  onDraftNote,
  onStartWaiver,
  onSaveWaiver,
  onCancelWaiver,
}: FindingsBodyProps) {
  const activeChips: Array<{
    key: string;
    label: string;
    onClear: () => void;
  }> = [];
  if (severityFilter !== "all") {
    activeChips.push({
      key: "severity",
      label: `severity ${severityFilter}`,
      onClear: () => onSeverityFilter("all"),
    });
  }
  if (ruleFilter !== "all") {
    activeChips.push({
      key: "rule",
      label: `rule ${ruleFilter}`,
      onClear: () => onRuleFilter("all"),
    });
  }
  if (statusFilter !== "all") {
    activeChips.push({
      key: "status",
      label: `status ${statusFilter}`,
      onClear: () => onStatusFilter("all"),
    });
  }
  if (tagFilter !== "all") {
    activeChips.push({
      key: "tag",
      label: `tag ${tagFilter}`,
      onClear: () => onTagFilter("all"),
    });
  }

  // Impact is a model selector; the view asks only for the rows it mounts.
  const impacts = useMemo(() => {
    const map = new Map<string, ReturnType<AuditFindingRow["impact"]>>();
    for (const row of rows) map.set(row.findingId, row.impact());
    return map;
  }, [rows]);

  const selectClass =
    "ui-input h-6 w-auto min-w-0 cursor-pointer px-1.5 text-[11px]";

  return (
    <>
      <div className="thin-scrollbar max-h-[64vh] overflow-y-auto">
        <div className="sticky top-0 z-30 border-b border-line-soft bg-panel">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3 py-2">
            <span className="inline-flex items-center gap-1.5 text-[11px] text-faint">
              <SlidersHorizontal className="size-3 text-accent" aria-hidden />
              Filter
            </span>
            <label className="inline-flex min-w-0 items-center gap-1.5 text-[11px] text-faint">
              Severity
              <select
                data-testid="findings-filter-severity"
                value={severityFilter}
                onChange={(event) => onSeverityFilter(event.target.value)}
                className={selectClass}
              >
                <option value="all">all</option>
                {filters.severities.map((severity) => (
                  <option key={severity} value={severity}>
                    {severity}
                  </option>
                ))}
              </select>
            </label>
            <label className="inline-flex min-w-0 items-center gap-1.5 text-[11px] text-faint">
              Status
              <select
                data-testid="findings-filter-status"
                value={statusFilter}
                onChange={(event) => onStatusFilter(event.target.value)}
                className={selectClass}
              >
                <option value="all">all</option>
                {filters.statuses.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </label>
            <label className="inline-flex min-w-0 items-center gap-1.5 text-[11px] text-faint">
              Tag
              <select
                data-testid="findings-filter-tag"
                value={tagFilter}
                onChange={(event) => onTagFilter(event.target.value)}
                className={`${selectClass} max-w-36`}
              >
                <option value="all">all</option>
                {filters.tags.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              data-testid="findings-clear-filters"
              disabled={!activeFilters}
              onClick={onClearFilters}
              className="ui-button ui-button-ghost ml-auto h-[26px] min-h-0 px-2 text-[11px] hover:text-accent"
            >
              <X className="size-3" aria-hidden />
              Clear
              {activeFilters ? (
                <span className="font-mono text-accent tabular-nums">
                  {activeFilters}
                </span>
              ) : null}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-x-1 gap-y-1 border-t border-line-soft px-3 py-1.5">
            <span className="mr-1 text-[11px] text-faint">Rule</span>
            <button
              type="button"
              onClick={() => onRuleFilter("all")}
              className={cx(
                "rounded-[3px] px-1.5 py-0.5 text-[11px]",
                ruleFilter === "all"
                  ? "bg-accent-soft text-accent-strong"
                  : "text-muted hover:bg-panel-soft hover:text-text",
              )}
            >
              all
            </button>
            {filters.rules.map((rule) => (
              <button
                key={rule}
                type="button"
                data-testid={`rule-${rule}`}
                onClick={() => onRuleFilter(rule)}
                className={cx(
                  "rounded-[3px] px-1.5 py-0.5 text-[11px]",
                  ruleFilter === rule
                    ? "bg-accent-soft text-accent-strong"
                    : "text-muted hover:bg-panel-soft hover:text-text",
                )}
              >
                {rule}
              </button>
            ))}
          </div>

          {activeChips.length ? (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-line-soft px-3 py-1 text-[11px] text-faint">
              <span>Active</span>
              {activeChips.map((chip) => (
                <button
                  key={chip.key}
                  type="button"
                  onClick={chip.onClear}
                  title={`Remove ${chip.label} filter`}
                  className="inline-flex items-center gap-1 rounded-[2px] px-1 text-accent hover:bg-accent-soft/60 hover:text-accent-strong"
                >
                  {chip.label}
                  <X className="size-2.5" aria-hidden />
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div role="rowgroup">
          {rows.length ? (
            rows.map((row) => {
              const selected = selectedFindingId === row.findingId;
              const isWaiving = waivingId === row.findingId;
              const impact = impacts.get(row.findingId);
              const impactParts = impact
                ? impact.label.split(" · ").filter(Boolean)
                : [];
              return (
                <Row
                  key={row.findingId}
                  role="row"
                  tabIndex={0}
                  aria-selected={selected}
                  aria-label={`${row.severity} ${row.label}`}
                  data-testid={row.testId}
                  selected={selected}
                  onClick={() => onSelectFinding(row.findingId)}
                  onKeyDown={(event) => {
                    if (event.target !== event.currentTarget) return;
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectFinding(row.findingId);
                    }
                  }}
                  className="group cursor-pointer items-start py-2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-accent-strong"
                >
                  <div className="flex w-full min-w-0 items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 items-center gap-2">
                        <SeverityDot severity={row.severity} />
                        <span className="text-[11px] text-muted">
                          {row.severity}
                        </span>
                        <span className="rounded-[3px] border border-line bg-panel-soft/40 px-1.5 py-0 text-[10.5px] text-muted">
                          {row.rule}
                        </span>
                        {row.question ? (
                          <HelpCircle
                            className="size-3 shrink-0 text-faint"
                            aria-label="Has a design question"
                          />
                        ) : null}
                        {row.openSubject ? (
                          <ActionButton
                            action={row.openSubject}
                            variant="ghost"
                            iconOnly
                            className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
                          />
                        ) : null}
                        <span className="ml-auto shrink-0">
                          <StatusMark status={row.status} />
                        </span>
                      </div>

                      <p className="mt-1 text-[13px] leading-snug font-medium text-text">
                        {row.label}
                      </p>

                      <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-faint">
                        <span
                          className="min-w-0 max-w-[260px] truncate"
                          title={row.subjectLabel}
                        >
                          {row.subjectLabel || "no subject"}
                        </span>
                        <Sep />
                        <span className="whitespace-nowrap">
                          evidence {formatCount(row.evidenceCount)}
                        </span>
                        {impactParts.length ? (
                          <>
                            <Sep />
                            {impactParts.map((part, index) => (
                              <span
                                key={`${row.findingId}-impact-${index}`}
                                className="whitespace-nowrap"
                                title={impact?.title}
                              >
                                {index > 0 ? (
                                  <span className="mr-2 text-faint">·</span>
                                ) : null}
                                {part}
                              </span>
                            ))}
                          </>
                        ) : null}
                      </div>

                      {row.note ? (
                        <p
                          className="mt-1 max-w-full truncate text-[11px] text-faint"
                          title={row.note}
                        >
                          note: {row.note}
                        </p>
                      ) : null}

                      {isWaiving ? (
                        <div
                          className="mt-2 border-t border-line-soft pt-2"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <label
                            htmlFor={`waive-note-${row.findingId}`}
                            className="flex items-baseline justify-between gap-2 text-[11px] text-faint"
                          >
                            Waiver note
                            <span className="text-accent">required</span>
                          </label>
                          <div className="mt-1 flex flex-wrap items-center gap-1.5">
                            <input
                              id={`waive-note-${row.findingId}`}
                              data-testid={`waive-note-${row.findingId}`}
                              value={draftNote}
                              onChange={(event) =>
                                onDraftNote(event.target.value)
                              }
                              placeholder="Why is this safe to leave unresolved?"
                              aria-label={`Waiver note for ${row.label}`}
                              className="ui-input h-7 min-w-0 flex-1 px-2 text-[11.5px]"
                            />
                            <button
                              type="button"
                              data-testid={`waive-save-${row.findingId}`}
                              disabled={!draftNote.trim()}
                              onClick={(event) => {
                                event.stopPropagation();
                                onSaveWaiver(row);
                              }}
                              className="ui-button ui-button-primary h-[26px] min-h-0 px-2 text-[11px]"
                            >
                              <CheckCircle2 className="size-3" aria-hidden />
                              Save waiver
                            </button>
                            <button
                              type="button"
                              data-testid={`waive-cancel-${row.findingId}`}
                              onClick={(event) => {
                                event.stopPropagation();
                                onCancelWaiver();
                              }}
                              className="ui-button ui-button-ghost h-[26px] min-h-0 px-2 text-[11px]"
                            >
                              Cancel
                            </button>
                          </div>
                          <p className="mt-1 text-[10.5px] leading-snug text-faint">
                            The waiver is stored in the local review queue with
                            the finding.
                          </p>
                        </div>
                      ) : null}
                    </div>

                    <div className="flex shrink-0 items-center gap-1 self-start pt-0.5 opacity-80 transition-opacity group-hover:opacity-100">
                      <ActionButton action={row.acknowledge} variant="ghost" />
                      <button
                        type="button"
                        data-testid={row.waive.testId}
                        aria-expanded={isWaiving}
                        onClick={(event) => {
                          event.stopPropagation();
                          onStartWaiver(row);
                        }}
                        className={cx(
                          "ui-button ui-button-ghost h-[26px] min-h-0 px-2 text-[11px]",
                          isWaiving &&
                            "border-accent/50 bg-accent-soft text-accent",
                        )}
                      >
                        <CircleSlash className="size-3" aria-hidden />
                        Waive
                      </button>
                    </div>
                  </div>
                </Row>
              );
            })
          ) : (
            <EmptyState>
              {section.totalFindings === 0
                ? "No findings. This is an observation about the snapshot, not proof of correctness."
                : `No findings match the current filters${
                    subjectFiltered ? ` for ${subjectLabel}` : ""
                  }. Adjust a control above or clear the filters.`}
            </EmptyState>
          )}
        </div>
      </div>

      <div className="border-t border-line-soft px-3 py-1.5">
        <div
          role="progressbar"
          aria-label="Findings review progress"
          aria-valuemin={0}
          aria-valuemax={section.queue.total}
          aria-valuenow={section.reviewed}
          className="flex items-center gap-2"
        >
          <span className="font-mono text-[10.5px] text-faint tabular-nums">
            {formatCount(section.reviewed)}/{formatCount(section.queue.total)}{" "}
            reviewed
          </span>
          <span className="h-1 min-w-0 flex-1 overflow-hidden rounded-[2px] bg-panel-soft">
            <span
              className="block h-full bg-accent/80 transition-[width]"
              style={{ width: `${section.reviewedPercent}%` }}
            />
          </span>
          <span className="font-mono text-[10.5px] text-accent tabular-nums">
            {formatCount(section.queue.open)} open
          </span>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Questions
// ---------------------------------------------------------------------------

export interface QuestionsBodyProps {
  section: AuditQuestionsSection;
  rows: AuditQuestionRow[];
  subjectFiltered: boolean;
  onLoadMore: () => void;
}

export function QuestionsBody({
  section,
  rows,
  subjectFiltered,
  onLoadMore,
}: QuestionsBodyProps) {
  const total = section.rows.length;
  return rows.length ? (
    <>
      <div className="thin-scrollbar max-h-[44vh] overflow-y-auto">
        {rows.map((row) => (
          <Row
            key={row.findingId}
            data-testid={row.testId}
            className="group items-start py-2"
          >
            <div className="flex w-full min-w-0 items-start gap-3">
              <HelpCircle
                className="mt-1 size-3.5 shrink-0 text-accent/80"
                aria-hidden
              />
              <div className="min-w-0 flex-1">
                <p className="text-[13px] leading-snug font-medium text-text">
                  {row.label}
                </p>
                <p className="mt-1 max-w-[78ch] text-[12px] leading-relaxed text-muted">
                  {row.question}
                </p>
                <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-faint">
                  <span className="whitespace-nowrap">{row.rule}</span>
                  <Sep />
                  <StatusMark status={row.status} />
                  <Sep />
                  <span className="whitespace-nowrap">
                    evidence {formatCount(row.evidenceCount)}
                  </span>
                  <Sep />
                  {row.openSubject ? (
                    <ActionButton
                      action={row.openSubject}
                      variant="chip"
                      className="max-w-[240px] text-accent"
                    />
                  ) : (
                    <span>no subject</span>
                  )}
                </div>
              </div>
              <div className="shrink-0 self-start pt-0.5 opacity-80 transition-opacity group-hover:opacity-100">
                <ActionButton action={row.acknowledge} variant="ghost" />
              </div>
            </div>
          </Row>
        ))}
      </div>

      {rows.length < total ? (
        <div className="flex items-center justify-between gap-2 border-t border-line-soft px-3 py-1.5">
          <span className="font-mono text-[10.5px] text-faint tabular-nums">
            showing {formatCount(rows.length)} of {formatCount(total)}
          </span>
          <ActionButton
            action={section.showMore}
            variant="ghost"
            onActivate={onLoadMore}
          />
        </div>
      ) : null}
    </>
  ) : (
    <EmptyState>
      {subjectFiltered
        ? "No design questions for the selected subject. Clear the subject filter to widen the queue."
        : "No design questions in this snapshot. The audit found no open decision points."}
    </EmptyState>
  );
}

// ---------------------------------------------------------------------------
// Coverage
// ---------------------------------------------------------------------------

/** A short column header; the full relation stays in `title`. */
function abbreviateSource(source: string): string {
  const trimmed = source.replace(/^(has|is|was)_/, "");
  const head = trimmed.split(/[_.]/).filter(Boolean)[0] ?? trimmed;
  return head.length <= 11 ? head : `${head.slice(0, 10)}…`;
}

/** Cell counts are words, not chips; zero counts stay out of the way. */
function CoverageMarks({
  fields,
  literals,
  bindings,
}: {
  fields: number;
  literals: number;
  bindings: number;
}) {
  const parts: Array<{ key: string; text: string; tone: string }> = [];
  if (fields) parts.push({ key: "f", text: `${fields}f`, tone: "text-text" });
  if (literals)
    parts.push({ key: "l", text: `${literals}l`, tone: "text-accent/80" });
  if (bindings)
    parts.push({ key: "b", text: `${bindings}b`, tone: "text-asset/80" });
  return (
    <>
      {parts.map((part, index) => (
        <span key={part.key}>
          {index > 0 ? <span className="text-faint"> · </span> : null}
          <span className={part.tone}>{part.text}</span>
        </span>
      ))}
    </>
  );
}

export function CoverageBody({
  section,
  showAll,
}: {
  section: AuditCoverageSection;
  showAll: boolean;
}) {
  const visibleRows = showAll
    ? section.rows
    : section.rows.slice(0, AUDIT_BOUNDS.coverage);
  const sourceColumns = Math.max(1, section.sources.length);
  const gridTemplate = `minmax(190px, 1.2fr) repeat(${sourceColumns}, minmax(68px, 0.7fr))`;

  return section.rows.length ? (
    <>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line-soft px-3 py-2 text-[11px] text-faint">
        <span className="inline-flex items-center gap-1.5">
          <span className="font-mono text-accent">f</span> traced fields
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="font-mono text-accent">l</span> literals
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="font-mono text-asset">b</span> bindings
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="font-mono">—</span> no traced source
        </span>
        <span className="ml-auto inline-flex items-center gap-1 text-faint">
          Click a row or cell to open the property
          <AuditIcon token="open" className="size-2.5" />
        </span>
      </div>

      <div
        role="grid"
        aria-label="Coverage matrix"
        className="thin-scrollbar max-h-[50vh] overflow-auto"
      >
        <div
          role="row"
          style={{ gridTemplateColumns: gridTemplate }}
          className="sticky top-0 z-20 grid h-[26px] items-center border-b border-line bg-panel"
        >
          <span
            role="columnheader"
            className="sticky left-0 z-30 h-full bg-panel px-2 text-[10.5px] leading-[26px] text-faint"
          >
            Property
          </span>
          {section.sources.length ? (
            section.sources.map((source) => (
              <span
                key={source}
                role="columnheader"
                title={source}
                className="truncate px-1 text-center text-[10.5px] leading-[26px] text-muted"
              >
                {abbreviateSource(source)}
              </span>
            ))
          ) : (
            <span
              role="columnheader"
              className="px-1 text-center text-[10.5px] leading-[26px] text-faint"
            >
              source
            </span>
          )}
        </div>

        <div role="rowgroup">
          {visibleRows.map((row) => {
            const literalOnly = row.cells.length === 0;
            return (
              <Row
                key={row.key}
                role="row"
                tabIndex={0}
                onClick={() => row.open.run?.()}
                onKeyDown={(event) => {
                  if (event.target !== event.currentTarget) return;
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    row.open.run?.();
                  }
                }}
                style={{ gridTemplateColumns: gridTemplate }}
                title={`${row.component} · ${row.property}`}
                className="group grid h-[26px] cursor-pointer items-center gap-1.5 py-0 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-accent-strong"
              >
                <span
                  role="gridcell"
                  className="sticky left-0 z-10 flex h-full min-w-0 items-baseline gap-2 bg-panel px-2 group-hover:bg-[#343434]"
                >
                  <span className="min-w-0 truncate text-[11px] text-text">
                    {row.component}
                  </span>
                  <span className="shrink-0 text-[10px] text-faint">
                    {row.entityKind}
                  </span>
                  <span className="min-w-0 truncate font-mono text-[10.5px] text-muted">
                    {row.property}
                  </span>
                </span>

                {literalOnly ? (
                  <span
                    role="gridcell"
                    style={{ gridColumn: `2 / span ${sourceColumns}` }}
                    className="min-w-0 px-1"
                  >
                    <button
                      type="button"
                      data-testid={`coverage-literal-${row.component}-${row.property}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        row.open.run?.();
                      }}
                      title={`${row.component}.${row.property}: ${
                        row.literals
                      } literal value${
                        row.literals === 1 ? "" : "s"
                      }. Click to open the property.`}
                      className="max-w-full cursor-pointer truncate rounded-[2px] px-1 text-[10.5px] text-faint underline-offset-2 hover:bg-panel-soft hover:text-accent hover:underline"
                    >
                      literal only
                    </button>
                  </span>
                ) : (
                  section.sources.map((source) => {
                    const cell = row.cells.find(
                      (candidate) => candidate.source === source,
                    );
                    if (!cell) {
                      return (
                        <span
                          key={source}
                          role="gridcell"
                          className="text-center font-mono text-[10.5px] text-faint/50"
                          title={`${row.component}.${row.property}: no traced value from ${source}`}
                        >
                          —
                        </span>
                      );
                    }
                    return (
                      <span
                        key={source}
                        role="gridcell"
                        className="min-w-0 px-0.5"
                      >
                        <button
                          type="button"
                          data-testid={cell.open.testId}
                          onClick={(event) => {
                            event.stopPropagation();
                            cell.open.run?.();
                          }}
                          title={cell.open.title}
                          aria-label={`Open ${row.component}.${row.property} from ${source}: ${cell.fields} traced fields, ${cell.literals} literals, ${cell.bindings} bindings`}
                          className="h-full w-full cursor-pointer truncate rounded-[2px] px-1 text-center font-mono text-[10.5px] tabular-nums hover:bg-panel-soft/70"
                        >
                          <CoverageMarks
                            fields={cell.fields}
                            literals={cell.literals}
                            bindings={cell.bindings}
                          />
                        </button>
                      </span>
                    );
                  })
                )}
              </Row>
            );
          })}
        </div>
      </div>

      <p className="border-t border-line-soft px-3 py-1.5 text-[10.5px] leading-relaxed text-faint">
        f = traced fields · l = literals · b = bindings. Hover a cell for the
        full source relation; click to open it in Explorer.
      </p>
    </>
  ) : (
    <EmptyState>
      No topology properties to cover. The snapshot has no nodes, edges or
      properties to trace.
    </EmptyState>
  );
}

// ---------------------------------------------------------------------------
// Decisions
// ---------------------------------------------------------------------------

export function DecisionsBody({
  section,
  showAll,
}: {
  section: AuditDecisionsSection;
  showAll: boolean;
}) {
  const visible = boundedDecisions(section.rows, showAll);
  return (
    <>
      <div className="grid grid-cols-2 gap-x-6 px-3 py-2">
        <ValueRow label="Sidecar" value={section.counts.sidecar} />
        <ValueRow label="Derived" value={section.counts.derived} />
        <ValueRow
          label="Rationale"
          value={section.counts.rationaleSupplied}
          tone="text-asset"
        />
        <ValueRow
          label="Missing"
          value={section.counts.rationaleMissing}
          tone="text-medium"
        />
      </div>

      {section.ai ? (
        <div
          data-testid={section.ai.testId}
          className="border-t border-line-soft px-3 py-2"
        >
          <p className="flex items-center gap-1.5 text-[11.5px] text-asset">
            <AuditIcon token="read" className="size-3" />
            AI provenance
          </p>
          <p className="mt-1 font-mono text-[10.5px] leading-relaxed text-asset/90">
            {[
              section.ai.model ? `model=${section.ai.model}` : undefined,
              section.ai.runId ? `run=${section.ai.runId}` : undefined,
              section.ai.generatedAt
                ? `generated=${section.ai.generatedAt}`
                : undefined,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {section.ai.note ? (
            <p className="mt-1 text-[11px] leading-relaxed text-asset/80">
              {section.ai.note}
            </p>
          ) : null}
          <p className="mt-1 text-[10.5px] text-asset/60">
            Recorded by the sidecar; this viewer did not call a model.
          </p>
        </div>
      ) : null}

      {section.rows.length ? (
        <div className="thin-scrollbar max-h-[54vh] overflow-y-auto">
          {visible.map((row) => (
            <Row
              key={row.decisionId}
              data-testid={row.testId}
              className="group items-start py-2"
            >
              <div className="flex w-full min-w-0 items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-faint">
                    <StatusMark status={row.status} />
                    <Sep />
                    <span className="whitespace-nowrap">{row.source}</span>
                    <Sep />
                    <span
                      className={cx(
                        "whitespace-nowrap",
                        row.rationaleSupplied ? "text-asset" : "text-medium",
                      )}
                    >
                      {row.rationaleSupplied
                        ? "rationale supplied"
                        : "rationale missing"}
                    </span>
                    <span className="ml-auto shrink-0 whitespace-nowrap">
                      evidence {formatCount(row.evidence.length)}
                    </span>
                  </div>

                  <p className="mt-1 text-[13px] leading-snug font-medium text-text">
                    {row.label}
                  </p>
                  <p
                    className={cx(
                      "mt-1 max-w-[78ch] text-[12px] leading-relaxed",
                      row.rationaleSupplied
                        ? "text-muted"
                        : "italic text-medium/80",
                    )}
                  >
                    {row.rationale || "No rationale recorded."}
                  </p>
                  {row.tags.length ? (
                    <p className="mt-1 text-[11px] text-faint">
                      {row.tags.join(" · ")}
                    </p>
                  ) : null}

                  <EvidenceList evidence={row.evidence} />
                </div>

                <div className="shrink-0 self-start pt-0.5">
                  {row.openSubject ? (
                    <ActionButton action={row.openSubject} variant="ghost" />
                  ) : (
                    <span className="text-[11px] text-faint">no subject</span>
                  )}
                </div>
              </div>
            </Row>
          ))}
        </div>
      ) : (
        <EmptyState>
          No decisions in the sidecar or the snapshot. Load a review sidecar to
          record rationale, or inspect the derived snapshot cards.
        </EmptyState>
      )}
    </>
  );
}

function boundedDecisions(
  rows: AuditDecisionRow[],
  showAll: boolean,
): AuditDecisionRow[] {
  if (showAll) return rows;
  const head = rows.slice(0, AUDIT_BOUNDS.decisions);
  const headIds = new Set(head.map((row) => row.decisionId));
  const retained = rows
    .slice(AUDIT_BOUNDS.decisions)
    .filter(
      (row) =>
        (row.source === "sidecar" || row.status === "open") &&
        !headIds.has(row.decisionId),
    );
  return [...head, ...retained];
}

function EvidenceList({ evidence }: { evidence: EvidenceRef[] }) {
  if (!evidence.length) {
    return (
      <p className="mt-1.5 text-[11px] text-faint">
        No evidence pointer recorded.
      </p>
    );
  }
  return (
    <ul className="mt-1.5 border-t border-line-soft pt-1">
      {evidence.map((entry, index) => (
        <li
          key={`${entry.artifact}:${entry.jsonPointer}:${index}`}
          className="flex min-w-0 items-baseline gap-2 py-0.5"
        >
          <span className="w-[72px] shrink-0 truncate text-[11px] text-faint">
            {entry.artifact}
          </span>
          <span
            className="min-w-0 truncate font-mono text-[10.5px] text-muted"
            title={`${entry.label} — ${entry.artifact} ${entry.jsonPointer}${
              entry.ref ? ` (${entry.ref.join(" / ")})` : ""
            }`}
          >
            {entry.label} · {entry.jsonPointer}
          </span>
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Build health
// ---------------------------------------------------------------------------

export function BuildBody({ section }: { section: AuditBuildSection }) {
  const verification = section.verification;
  return (
    <>
      {section.compileOnly ? (
        <div
          data-testid="compile-only-note"
          className="flex items-start gap-2 px-3 py-2.5"
        >
          <AlertOctagon
            className="mt-0.5 size-3.5 shrink-0 text-medium"
            aria-hidden
          />
          <div className="min-w-0">
            <p className="text-[11.5px] text-medium">Compile-only snapshot</p>
            <p className="mt-1 text-[11.5px] leading-relaxed text-muted">
              The blueprint and workflow were compiled from source. The graph
              was not executed, so published artifacts and observed counts are
              absent. Health here describes the compile contract, not a run.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex items-start gap-2 px-3 py-2.5">
          {verification.state === "failed" ? (
            <ShieldAlert
              className={cx(
                "mt-0.5 size-3.5 shrink-0",
                verificationText(verification.tone),
              )}
              aria-hidden
            />
          ) : verification.state === "executed" ? (
            <CheckCircle2
              className={cx(
                "mt-0.5 size-3.5 shrink-0",
                verificationText(verification.tone),
              )}
              aria-hidden
            />
          ) : (
            <CircleAlert
              className={cx(
                "mt-0.5 size-3.5 shrink-0",
                verificationText(verification.tone),
              )}
              aria-hidden
            />
          )}
          <div className="min-w-0">
            <p
              className={cx(
                "text-[11.5px]",
                verificationText(verification.tone),
              )}
            >
              {verification.label}
            </p>
            <p className="mt-1 text-[11.5px] leading-relaxed text-muted">
              {verification.detail}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-6 border-t border-line-soft px-3 py-2">
        {section.stats.map((stat) => (
          <ValueRow
            key={stat.id}
            label={stat.label}
            value={`${formatCount(stat.value)} ${stat.unit}`}
            tone={toneText(stat.tone)}
          />
        ))}
      </div>

      {section.empty ? (
        <EmptyState>
          No artifacts, failures or components recorded. This snapshot has no
          build evidence to inspect.
        </EmptyState>
      ) : (
        <>
          <div className="border-t border-line-soft px-3 py-2">
            <p className="flex items-center gap-1.5 text-[11px] text-faint">
              <Database className="size-3" aria-hidden />
              Published artifacts
            </p>
            <div className="mt-1">
              {section.published.length ? (
                section.published.map((field) => (
                  <ValueRow
                    key={field.id}
                    label={field.label}
                    value={field.value}
                    title={field.title}
                  />
                ))
              ) : (
                <ValueRow
                  label="—"
                  value="no artifact published"
                  tone="text-faint"
                />
              )}
            </div>
            {section.publishedMore ? (
              <p className="mt-1 text-[11px] text-faint">
                {section.publishedMore}
              </p>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-4 border-t border-line-soft px-3 py-2">
            <FailureList
              label="Unresolved"
              fields={section.unresolved}
              toneClass="text-critical"
            />
            <FailureList
              label="Recovered"
              fields={section.recovered}
              toneClass="text-medium"
            />
          </div>

          <div className="border-t border-line-soft px-3 py-2">
            <p className="flex items-center gap-1.5 text-[11px] text-faint">
              <Play className="size-3" aria-hidden />
              Components
              <span className="ml-auto font-mono text-[10.5px] tabular-nums">
                {formatCount(section.components.length)}
              </span>
            </p>
            {section.components.length ? (
              <div className="thin-scrollbar mt-1 max-h-32 overflow-y-auto">
                {section.components.map((field) => (
                  <ValueRow
                    key={field.id}
                    label={field.label}
                    value={field.value}
                    title={field.title}
                  />
                ))}
              </div>
            ) : (
              <ValueRow
                label="—"
                value="no workflow components"
                tone="text-faint"
              />
            )}
          </div>
        </>
      )}
    </>
  );
}

function FailureList({
  label,
  fields,
  toneClass,
}: {
  label: string;
  fields: FieldModel[];
  toneClass: string;
}) {
  return (
    <div className="min-w-0">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] text-faint">{label}</p>
        <span className={cx("font-mono text-[10.5px] tabular-nums", toneClass)}>
          {formatCount(fields.length)}
        </span>
      </div>
      {fields.length ? (
        <div className="thin-scrollbar mt-1 max-h-24 overflow-y-auto">
          {fields.slice(0, 8).map((field) => (
            <ValueRow
              key={field.id}
              label={field.label}
              value={field.value}
              title={field.title}
              tone={toneText(field.tone)}
            />
          ))}
        </div>
      ) : (
        <ValueRow label="—" value="none recorded" tone="text-faint" />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Diff
// ---------------------------------------------------------------------------

export function DiffBody({ section }: { section: AuditDiffSection }) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 border-b border-line-soft px-3 py-2">
        <span className="inline-flex items-center gap-1.5 text-[11px] text-faint">
          <Pin className="size-3" aria-hidden />
          Baseline
        </span>
        <span
          data-testid="baseline-name"
          className="min-w-0 max-w-[55%] truncate font-mono text-[11.5px] text-text"
          title={section.baselineName ?? "No baseline pinned"}
        >
          {section.baselineName ?? "no baseline pinned"}
        </span>
        <ActionButton action={section.pin} variant="ghost" />
        <ActionButton
          action={section.clear}
          variant="ghost"
          className="text-critical hover:text-critical"
        />
      </div>

      {!section.hasDiff ? (
        <EmptyState>
          <FileSearch className="mr-1 inline size-3" aria-hidden />
          No comparison loaded. Pin the current snapshot as a baseline, or
          choose another snapshot with Compare.
        </EmptyState>
      ) : (
        <>
          <div data-testid="diff-summary" className="border-b border-line-soft px-3 py-2">
            {!section.changed ? (
              <p className="flex items-center gap-1.5 text-[11.5px] text-asset">
                <CheckCircle2 className="size-3" aria-hidden />
                No structural changes against the baseline.
              </p>
            ) : (
              <div className="grid grid-cols-2 gap-x-6 sm:grid-cols-3">
                {section.summary.map((field) => (
                  <ValueRow
                    key={field.id}
                    label={field.label}
                    value={field.value}
                    tone={toneText(field.tone)}
                  />
                ))}
              </div>
            )}
          </div>

          {section.changed ? (
            <>
              <div className="border-b border-line-soft px-3 py-2">
                <p className="mb-1 text-[11px] text-faint">Steps</p>
                {(
                  [
                    ["Added", section.steps.added, "text-asset"],
                    ["Removed", section.steps.removed, "text-critical"],
                    ["Changed", section.steps.changed, "text-accent"],
                  ] as const
                ).map(([label, actions, toneClass]) => (
                  <div
                    key={label}
                    className="flex min-w-0 items-start gap-3 py-0.5"
                  >
                    <span className="w-[72px] shrink-0 text-[11px] text-faint">
                      {label}
                    </span>
                    <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                      {actions.length ? (
                        actions.map((action) => (
                          <ActionButton
                            key={action.id}
                            action={action}
                            variant="chip"
                            className={toneClass}
                          />
                        ))
                      ) : (
                        <span className="text-[11px] text-faint">—</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-4 border-b border-line-soft px-3 py-2">
                <TopologyList
                  label="Topology added"
                  actions={section.topology.added}
                  toneClass="text-asset"
                />
                <TopologyList
                  label="Topology removed"
                  actions={section.topology.removed}
                  toneClass="text-critical"
                />
              </div>

              <div className="grid grid-cols-2 gap-4 px-3 py-2">
                <div className="min-w-0">
                  <p className="text-[11px] text-faint">Bindings</p>
                  <div className="thin-scrollbar mt-1 max-h-20 overflow-y-auto">
                    {(
                      [
                        ["Added", section.bindings.added, "text-asset"],
                        ["Removed", section.bindings.removed, "text-critical"],
                        ["Changed", section.bindings.changed, "text-accent"],
                      ] as const
                    ).map(([label, actions, toneClass]) => (
                      <div
                        key={label}
                        className="flex min-w-0 items-baseline gap-2 py-0.5"
                      >
                        <span className="w-[56px] shrink-0 text-[11px] text-faint">
                          {label}
                        </span>
                        <span className="flex min-w-0 flex-wrap items-center gap-x-2">
                          {actions.length ? (
                            actions.map((action) =>
                              action.run ? (
                                <ActionButton
                                  key={action.id}
                                  action={action}
                                  variant="chip"
                                  className={toneClass}
                                />
                              ) : (
                                <span
                                  key={action.id}
                                  className="font-mono text-[10.5px] text-faint"
                                >
                                  {action.label}
                                </span>
                              ),
                            )
                          ) : (
                            <span className="text-[11px] text-faint">—</span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] text-faint">Connections</p>
                  <div className="thin-scrollbar mt-1 max-h-20 space-y-0.5 overflow-y-auto font-mono text-[10.5px]">
                    {section.connections.added.map((connection) => (
                      <p
                        key={`connection-added-${connection}`}
                        className="truncate text-asset"
                        title={connection}
                      >
                        + {connection}
                      </p>
                    ))}
                    {section.connections.removed.map((connection) => (
                      <p
                        key={`connection-removed-${connection}`}
                        className="truncate text-critical"
                        title={connection}
                      >
                        − {connection}
                      </p>
                    ))}
                    {!section.connections.added.length &&
                    !section.connections.removed.length ? (
                      <span className="text-[11px] text-faint">—</span>
                    ) : null}
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </>
      )}
    </>
  );
}

function TopologyList({
  label,
  actions,
  toneClass,
}: {
  label: string;
  actions: AuditDiffSection["topology"]["added"];
  toneClass: string;
}) {
  return (
    <div className="min-w-0">
      <p className="flex items-baseline gap-1.5 text-[11px] text-faint">
        {label}
        <span className={cx("font-mono text-[10.5px] tabular-nums", toneClass)}>
          {formatCount(actions.length)}
        </span>
      </p>
      <div className="thin-scrollbar mt-1 max-h-24 overflow-y-auto">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          {actions.length ? (
            actions.map((action) => (
              <ActionButton
                key={action.id}
                action={action}
                variant="chip"
                className={toneClass}
              />
            ))
          ) : (
            <span className="text-[11px] text-faint">—</span>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dossier
// ---------------------------------------------------------------------------

export function DossierBody({ section }: { section: AuditDossierSection }) {
  return (
    <>
      <p className="px-3 pt-2 text-[12px] leading-relaxed text-muted">
        {section.description}
      </p>
      <div className="grid grid-cols-1 gap-1 px-2 py-2 sm:grid-cols-2">
        {section.actions.map((action) => (
          <ActionButton key={action.id} action={action} variant="dossier" />
        ))}
      </div>
      <p className="border-t border-line-soft px-3 py-2 text-[10.5px] leading-relaxed text-faint">
        {section.note}
      </p>
    </>
  );
}
