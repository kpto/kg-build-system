"use client";

/**
 * Audit feature surface.
 *
 * The shell owns the panels, their sizes and the workbench selection. This
 * module owns the audit's three bodies: the rule/filter sidebar, the findings
 * editor with evidence and a proof link, and the Problems / Evidence / Data
 * bottom tabs.
 */

import { useEffect, useMemo, useState, type JSX } from "react";
import {
  ArrowUpRight,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Database,
  ListFilter,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";

import {
  AUDIT_RULE_GROUPS,
  auditRuleGroup,
} from "@/lib/audit";
import type {
  AuditFinding,
  AuditReport,
  Severity,
} from "@/lib/reviewTypes";
import type { FeatureProps, WorkbenchSelection } from "@/workbench/types";
import {
  activeFinding,
  auditReportFor,
  countBySubject,
  decisionForFinding,
  filterAuditFindings,
  findingSubjectKind,
  proofSelectionFor,
  SEVERITY_ORDER,
  subjectLabel,
  type AuditFilters,
} from "./auditData";
import {
  allSeverities,
  resetAuditFilters,
  setGroupFilter,
  setQuery,
  setRuleFilter,
  setSubjectFilter,
  toggleSeverity,
  useAuditFilters,
} from "./viewState";
import styles from "./audit.module.css";

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

const SEVERITY_ROLE: Record<Severity, string> = {
  critical: styles.severityCritical,
  high: styles.severityHigh,
  medium: styles.severityMedium,
  low: styles.severityLow,
  info: styles.severityInfo,
};

function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}

function findingSelection(finding: AuditFinding): WorkbenchSelection {
  return {
    activity: "audit",
    kind: "finding",
    name: finding.rule,
    findingId: finding.id,
    ...(finding.subject?.component ? { component: finding.subject.component } : {}),
    ...(finding.subject?.property ? { property: finding.subject.property } : {}),
    ...(finding.subject?.stepId ? { stepId: finding.subject.stepId } : {}),
  };
}

function severityCounts(
  findings: readonly AuditFinding[],
): Record<Severity, number> {
  const counts = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  } as Record<Severity, number>;
  for (const finding of findings) counts[finding.severity] += 1;
  return counts;
}

function ruleCounts(findings: readonly AuditFinding[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const finding of findings) {
    counts.set(finding.rule, (counts.get(finding.rule) ?? 0) + 1);
  }
  return counts;
}

function ruleLabel(rule: string): string {
  const leaf = rule.split(".").slice(1).join(".");
  const words = (leaf || rule).replaceAll("-", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function groupLabel(group: AuditFilters["group"]): string {
  if (!group) return "All";
  return AUDIT_RULE_GROUPS.find((entry) => entry.id === group)?.label ?? group;
}

function SeverityDot({ severity }: { severity: Severity }) {
  return (
    <span
      className={`${styles.severityDot} ${SEVERITY_ROLE[severity]}`}
      aria-hidden
    />
  );
}

function SeverityChip({ severity }: { severity: Severity }) {
  return (
    <span className={`${styles.severityChip} ${SEVERITY_ROLE[severity]}`}>
      <SeverityDot severity={severity} />
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function RuleGroup({
  group,
  findings,
  filters,
  snapshotName,
  defaultOpen,
}: {
  group: (typeof AUDIT_RULE_GROUPS)[number];
  findings: readonly AuditFinding[];
  filters: AuditFilters;
  snapshotName: string;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const groupFindings = findings.filter(
    (finding) => auditRuleGroup(finding.rule) === group.id,
  );
  const counts = ruleCounts(groupFindings);
  const rules = [...counts.entries()].sort(
    (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
  );
  const active =
    filters.group === group.id ||
    (filters.rule !== null && auditRuleGroup(filters.rule) === group.id);

  useEffect(() => {
    if (active) setOpen(true);
  }, [active]);

  return (
    <div className={styles.ruleGroup} data-active={active ? "true" : undefined}>
      <button
        type="button"
        className={styles.ruleGroupHead}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        data-testid={`audit-group-${group.id}`}
      >
        {open ? (
          <ChevronDown aria-hidden className={styles.iconSmall} />
        ) : (
          <ChevronRight aria-hidden className={styles.iconSmall} />
        )}
        <span className={styles.ruleGroupTitle}>{group.label}</span>
        <span className={styles.count}>{groupFindings.length}</span>
      </button>
      {open ? (
        <div className={styles.ruleGroupBody}>
          <p className={styles.ruleGroupDetail}>{group.detail}</p>
          {rules.length === 0 ? (
            <p className={styles.emptyLine}>No findings under the current filters.</p>
          ) : (
            rules.map(([rule, count]) => (
              <button
                key={rule}
                type="button"
                className={styles.ruleRow}
                data-active={filters.rule === rule ? "true" : undefined}
                onClick={() => setRuleFilter(snapshotName, rule)}
                title={rule}
                data-testid={`audit-rule-${rule}`}
              >
                <code className={styles.ruleCode}>{rule}</code>
                <span className={styles.count}>{count}</span>
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

export function AuditSidebar(props: FeatureProps): JSX.Element {
  const { index, snapshot, review } = props.state;
  const report = auditReportFor(index, review);
  const filters = useAuditFilters(snapshot.name);
  const selection = props.state.functions.audit.selection;

  const visible = useMemo(
    () => filterAuditFindings(report.findings, filters),
    [report.findings, filters],
  );
  // Group counts keep the current severity/subject/query scope but ignore the
  // focused group, so every group count remains meaningful while one is open.
  const groupScope = useMemo(
    () =>
      filterAuditFindings(report.findings, {
        ...filters,
        group: null,
        rule: null,
      }),
    [report.findings, filters],
  );
  // Severity counts describe the focused queue (group or rule), not the whole
  // snapshot. The summary still states the full finding count.
  const severityScope = useMemo(
    () =>
      filterAuditFindings(report.findings, {
        ...filters,
        severities: [...SEVERITY_ORDER],
        rule: null,
      }),
    [report.findings, filters],
  );
  // Subject counts describe what is reachable in the current focus, including
  // the exact rule when one is selected.
  const subjectScope = useMemo(
    () =>
      filterAuditFindings(report.findings, {
        ...filters,
        severities: [...SEVERITY_ORDER],
        subjectKind: null,
      }),
    [report.findings, filters],
  );
  const counts = severityCounts(severityScope);
  const subjectCounts = countBySubject(subjectScope);
  const selectedId = selection.findingId;
  const focusLabel = filters.rule ?? groupLabel(filters.group);

  return (
    <div className={styles.sidebar} data-testid="audit-sidebar">
      <section className={styles.summary}>
        <div className={styles.summaryTop}>
          <span className={styles.summaryIcon} aria-hidden>
            <ShieldCheck className={styles.icon} />
          </span>
          <div>
            <p className={styles.kicker}>Finding ledger</p>
            <p className={styles.summaryValue}>{plural(report.findings.length, "finding")}</p>
          </div>
          <span
            className={styles.summaryOpen}
            title="Findings in the current filter scope. Decisions live in the Semantics ledger."
          >
            <span className={styles.openDot} aria-hidden />
            {plural(visible.length, "shown")}
          </span>
        </div>
        <div className={styles.filterRow}>
          <button
            type="button"
            className={styles.filterChip}
            data-active={
              filters.severities.length === SEVERITY_ORDER.length ? "true" : undefined
            }
            onClick={() => allSeverities(snapshot.name)}
          >
            All <span className={styles.count}>{severityScope.length}</span>
          </button>
          {SEVERITY_ORDER.map((severity) => (
            <button
              key={severity}
              type="button"
              className={styles.filterChip}
              data-active={filters.severities.includes(severity) ? "true" : undefined}
              onClick={() => toggleSeverity(snapshot.name, severity)}
              title={`${SEVERITY_LABEL[severity]} findings`}
              data-testid={`audit-severity-${severity}`}
            >
              <SeverityDot severity={severity} />
              {SEVERITY_LABEL[severity]}
              <span className={styles.count}>{counts[severity]}</span>
            </button>
          ))}
        </div>

        <div className={styles.focusRow}>
          <button
            type="button"
            className={styles.focusChip}
            data-active={filters.group === null ? "true" : undefined}
            onClick={() => setGroupFilter(snapshot.name, null)}
            data-testid="audit-focus-all"
          >
            All <span className={styles.count}>{groupScope.length}</span>
          </button>
          {AUDIT_RULE_GROUPS.map((group) => {
            const count = groupScope.filter(
              (finding) => auditRuleGroup(finding.rule) === group.id,
            ).length;
            return (
              <button
                key={group.id}
                type="button"
                className={styles.focusChip}
                data-active={filters.group === group.id ? "true" : undefined}
                onClick={() => setGroupFilter(snapshot.name, group.id)}
                data-testid={`audit-focus-${group.id}`}
              >
                {group.label} <span className={styles.count}>{count}</span>
              </button>
            );
          })}
        </div>
        <p className={styles.focusNote}>
          Identity is the default focus; switch rule group to review grounding,
          semantics or type/presence.
        </p>
      </section>

      <section className={styles.section}>
        <header className={styles.sectionHead}>
          <span>
            <ListFilter aria-hidden className={styles.iconSmall} /> Subject
          </span>
          {filters.subjectKind || filters.rule || filters.query ? (
            <button
              type="button"
              className={styles.linkButton}
              onClick={() => resetAuditFilters(snapshot.name)}
              data-testid="audit-clear-filters"
            >
              Clear
            </button>
          ) : null}
        </header>
        <div className={styles.chipWrap}>
          <button
            type="button"
            className={styles.subjectChip}
            data-active={filters.subjectKind === null ? "true" : undefined}
            onClick={() => setSubjectFilter(snapshot.name, null)}
          >
            All <span className={styles.count}>{subjectScope.length}</span>
          </button>
          {subjectCounts.map((entry) => (
            <button
              key={entry.kind}
              type="button"
              className={styles.subjectChip}
              data-active={filters.subjectKind === entry.kind ? "true" : undefined}
              onClick={() =>
                setSubjectFilter(
                  snapshot.name,
                  filters.subjectKind === entry.kind ? null : entry.kind,
                )
              }
              data-testid={`audit-subject-${entry.kind}`}
            >
              {entry.kind} <span className={styles.count}>{entry.count}</span>
            </button>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <header className={styles.sectionHead}>
          <span>
            <ShieldCheck aria-hidden className={styles.iconSmall} /> Rules
          </span>
          <span className={styles.count}>{visible.length} shown</span>
        </header>
        <div className={styles.search}>
          <Search aria-hidden className={styles.iconSmall} />
          <input
            value={filters.query}
            onChange={(event) => setQuery(snapshot.name, event.target.value)}
            placeholder="Filter findings"
            aria-label="Filter findings"
            spellCheck={false}
          />
          {filters.query ? (
            <button
              type="button"
              className={styles.iconButton}
              onClick={() => setQuery(snapshot.name, "")}
              aria-label="Clear finding filter"
            >
              <X aria-hidden className={styles.iconSmall} />
            </button>
          ) : null}
        </div>
        <div className={styles.ruleGroups}>
          {AUDIT_RULE_GROUPS.map((group, position) => (
            <RuleGroup
              key={group.id}
              group={group}
              findings={groupScope}
              filters={filters}
              snapshotName={snapshot.name}
              defaultOpen={
                position === 0 || filters.group === group.id || filters.rule !== null
              }
            />
          ))}
        </div>
      </section>

      <p className={styles.sidebarNote}>
        Deterministic observations only. Each finding points at snapshot evidence;
        review decisions are recorded in the sidecar, not here.
      </p>

      {selectedId ? (
        <span className={styles.hiddenSelection} data-testid="audit-selected-id">
          {selectedId}
        </span>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

function FindingRow({
  finding,
  selected,
  onSelect,
}: {
  finding: AuditFinding;
  selected: boolean;
  onSelect(): void;
}) {
  return (
    <button
      type="button"
      className={styles.findingRow}
      data-selected={selected ? "true" : undefined}
      onClick={onSelect}
      data-testid={`audit-finding-${finding.id}`}
    >
      <SeverityDot severity={finding.severity} />
      <span className={styles.findingCopy}>
        <span className={styles.findingTitle}>{finding.title}</span>
        <span className={styles.findingMeta}>
          <code>{finding.rule}</code>
          <span>{subjectLabel(finding)}</span>
        </span>
      </span>
      <ChevronRight aria-hidden className={styles.findingChevron} />
    </button>
  );
}

function EvidenceList({ finding }: { finding: AuditFinding }) {
  return (
    <ul className={styles.evidenceList}>
      {finding.evidence.map((entry, position) => (
        <li
          key={`${entry.artifact}:${entry.jsonPointer}:${position}`}
          className={styles.evidenceItem}
        >
          <span className={styles.evidenceLabel}>{entry.label}</span>
          <span className={styles.evidencePointer}>
            <span className={styles.artifact}>{entry.artifact}</span>
            <code>{entry.jsonPointer}</code>
          </span>
          {entry.ref ? <code className={styles.evidenceRef}>{entry.ref.join(".")}</code> : null}
        </li>
      ))}
    </ul>
  );
}

export function AuditEditor(props: FeatureProps): JSX.Element {
  const { index, snapshot, review } = props.state;
  const report = auditReportFor(index, review);
  const filters = useAuditFilters(snapshot.name);
  const selection = props.state.functions.audit.selection;
  const visible = useMemo(
    () => filterAuditFindings(report.findings, filters),
    [report.findings, filters],
  );
  const selected = activeFinding(report, visible, selection.findingId);
  const decision = decisionForFinding(review, selected);
  const proofTarget = selected ? proofSelectionFor(selected) : null;
  const focusLabel = filters.rule ?? groupLabel(filters.group);

  useEffect(() => {
    // The editor always shows a finding. Persist that default so the workbench
    // status bar, the bottom panel and a later Proof jump agree on the subject.
    if (!selection.findingId && selected) {
      props.actions.setSelection("audit", findingSelection(selected));
    }
  }, [props.actions, selected, selection.findingId]);

  const select = (finding: AuditFinding) => {
    props.actions.setSelection("audit", findingSelection(finding));
  };

  const openProof = () => {
    if (!proofTarget) return;
    props.actions.setActivity("proof");
    props.actions.setSelection("proof", proofTarget);
  };

  return (
    <div className={styles.editor} data-testid="audit-editor">
      <header className={styles.editorHead}>
        <div>
          <p className={styles.kicker}>Rule ledger</p>
          <h1 className={styles.editorTitle}>Audit</h1>
        </div>
        <div className={styles.editorMeta}>
          <span>{plural(report.findings.length, "finding")}</span>
          <span className={styles.metaDivider} aria-hidden />
          <span>{plural(new Set(report.findings.map((finding) => finding.rule)).size, "rule")}</span>
          <span className={styles.metaDivider} aria-hidden />
          <span>{plural(review.decisions.length, "decision")}</span>
        </div>
      </header>

      <div className={styles.editorBody}>
        <section className={styles.listPane} aria-label="Findings">
          <header className={styles.paneHead}>
            <span>Findings</span>
            <span className={styles.focusLabel} data-testid="audit-focus-label">
              {focusLabel}
            </span>
            <span className={styles.count}>{visible.length}</span>
            {filters.rule ? (
              <button
                type="button"
                className={styles.activeFilter}
                onClick={() => setRuleFilter(snapshot.name, null)}
                title="Clear rule filter"
              >
                <code>{filters.rule}</code>
                <X aria-hidden className={styles.iconTiny} />
              </button>
            ) : null}
          </header>
          <div className={styles.findingList}>
            {visible.length === 0 ? (
              <p className={styles.emptyState}>
                <CircleDot aria-hidden className={styles.icon} />
                No finding matches the current filters.
              </p>
            ) : (
              visible.slice(0, 220).map((finding) => (
                <FindingRow
                  key={finding.id}
                  finding={finding}
                  selected={selected?.id === finding.id}
                  onSelect={() => select(finding)}
                />
              ))
            )}
          </div>
          {visible.length > 220 ? (
            <p className={styles.limitNote}>
              Showing 220 of {visible.length}. Narrow the rule or subject filter.
            </p>
          ) : null}
        </section>

        <aside className={styles.detailPane} aria-label="Selected finding">
          {selected ? (
            <>
              <header className={styles.detailHead}>
                <SeverityChip severity={selected.severity} />
                <code className={styles.detailRule}>{selected.rule}</code>
                <span
                  className={styles.decisionPill}
                  data-status={decision?.status ?? "none"}
                >
                  {decision ? decision.status : "no decision"}
                </span>
              </header>
              <h2 className={styles.detailTitle}>{selected.title}</h2>
              <p className={styles.detailCopy}>{selected.detail}</p>

              <dl className={styles.subjectGrid}>
                <div>
                  <dt>Subject</dt>
                  <dd>{subjectLabel(selected)}</dd>
                </div>
                <div>
                  <dt>Kind</dt>
                  <dd>{findingSubjectKind(selected)}</dd>
                </div>
                {selected.subject?.bindingIndex !== undefined ? (
                  <div>
                    <dt>Binding</dt>
                    <dd className={styles.mono}>#{selected.subject.bindingIndex}</dd>
                  </div>
                ) : null}
                {selected.subject?.stepId ? (
                  <div>
                    <dt>Step</dt>
                    <dd className={styles.mono}>{selected.subject.stepId.join(" / ")}</dd>
                  </div>
                ) : null}
              </dl>

              {selected.question ? (
                <div className={styles.questionBox}>
                  <p className={styles.questionLabel}>Design question</p>
                  <p>{selected.question}</p>
                </div>
              ) : null}

              <section className={styles.evidenceSection}>
                <header className={styles.sectionHead}>
                  <span>Evidence</span>
                  <span className={styles.count}>{selected.evidence.length}</span>
                </header>
                <EvidenceList finding={selected} />
              </section>

              <footer className={styles.detailFooter}>
                <button
                  type="button"
                  className={styles.proofButton}
                  onClick={openProof}
                  disabled={!proofTarget}
                  title={
                    proofTarget
                      ? "Open this subject in the Proof function"
                      : "This subject has no proof target"
                  }
                  data-testid="audit-open-proof"
                >
                  <ArrowUpRight aria-hidden className={styles.iconSmall} />
                  Open in Proof
                </button>
                {decision ? (
                  <p className={styles.decisionNote}>
                    Decision: {decision.title}
                    {decision.rationale ? ` — ${decision.rationale}` : ""}
                  </p>
                ) : (
                  <p className={styles.decisionNote}>
                    No sidecar decision is attached to this subject.
                  </p>
                )}
              </footer>
            </>
          ) : (
            <p className={styles.emptyState}>Select a finding to inspect its evidence.</p>
          )}
        </aside>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bottom
// ---------------------------------------------------------------------------

function ProblemsBody({
  report,
  filtered,
  selected,
  onSelect,
}: {
  report: AuditReport;
  filtered: readonly AuditFinding[];
  selected: AuditFinding | undefined;
  onSelect(finding: AuditFinding): void;
}) {
  return (
    <div className={styles.bottomBody} data-testid="audit-problems">
      <header className={styles.bottomHead}>
        <span>Problems</span>
        <span className={styles.count}>{filtered.length}</span>
        <span className={styles.bottomHint}>
          Deterministic findings; no score is computed.
        </span>
      </header>
      <div className={styles.problemList}>
        {filtered.length === 0 ? (
          <p className={styles.emptyState}>No problem matches the current filters.</p>
        ) : (
          filtered.slice(0, 120).map((finding) => (
            <button
              key={finding.id}
              type="button"
              className={styles.problemRow}
              data-selected={selected?.id === finding.id ? "true" : undefined}
              onClick={() => onSelect(finding)}
              data-testid={`audit-problem-${finding.id}`}
            >
              <SeverityDot severity={finding.severity} />
              <code className={styles.problemRule}>{finding.rule}</code>
              <span className={styles.problemTitle}>{finding.title}</span>
              <span className={styles.problemSubject}>{subjectLabel(finding)}</span>
            </button>
          ))
        )}
      </div>
      {filtered.length > 120 ? (
        <p className={styles.limitNote}>
          Showing 120 of {filtered.length} problems.
        </p>
      ) : null}
      <span className={styles.hiddenSelection}>{report.findings.length}</span>
    </div>
  );
}

function EvidenceBody({ finding }: { finding: AuditFinding | undefined }) {
  return (
    <div className={styles.bottomBody} data-testid="audit-evidence">
      {finding ? (
        <>
          <header className={styles.bottomHead}>
            <span>{finding.title}</span>
            <code className={styles.bottomRule}>{finding.rule}</code>
          </header>
          <div className={styles.bottomEvidence}>
            <EvidenceList finding={finding} />
          </div>
        </>
      ) : (
        <p className={styles.emptyState}>Select a finding to inspect its evidence.</p>
      )}
    </div>
  );
}

function DataBody({ finding }: { finding: AuditFinding | undefined }) {
  return (
    <div className={styles.bottomBody} data-testid="audit-data">
      <header className={styles.bottomHead}>
        <span>
          <Database aria-hidden className={styles.iconSmall} /> Finding JSON
        </span>
        {finding ? <code className={styles.bottomRule}>{finding.rule}</code> : null}
      </header>
      {finding ? (
        <pre className={styles.json}>{JSON.stringify(finding, null, 2)}</pre>
      ) : (
        <p className={styles.emptyState}>Select a finding to inspect its JSON.</p>
      )}
    </div>
  );
}

export function AuditBottom(props: FeatureProps): JSX.Element {
  const { index, snapshot, review } = props.state;
  const layout = props.state.functions.audit.layout;
  const report = auditReportFor(index, review);
  const filters = useAuditFilters(snapshot.name);
  const selection = props.state.functions.audit.selection;
  const filtered = useMemo(
    () => filterAuditFindings(report.findings, filters),
    [report.findings, filters],
  );
  const selected = activeFinding(report, filtered, selection.findingId);
  const tab = layout.bottomTab || "problems";

  const select = (finding: AuditFinding) => {
    props.actions.setSelection("audit", findingSelection(finding));
  };

  if (tab === "evidence") {
    return <EvidenceBody finding={selected} />;
  }
  if (tab === "data") {
    return <DataBody finding={selected} />;
  }
  return (
    <ProblemsBody
      report={report}
      filtered={filtered}
      selected={selected}
      onSelect={select}
    />
  );
}
