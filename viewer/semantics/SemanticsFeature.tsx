"use client";

/**
 * The semantics function: purpose, semantic ledger, decisions and sign-off.
 *
 * A semantic unit is evidence attached to a subject. It is never propagated to
 * a descendant. The view owns presentation only; every count, key, required
 * decision and sign-off gate comes from `semantics/model.ts`.
 */

import type { JSX } from "react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";
import {
  AlertTriangle,
  Check,
  ChevronRight,
  CircleDot,
  Download,
  FileText,
  ScrollText,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";

import type { FeatureProps } from "@/workbench/types";
import type {
  DecisionStatus,
  ReviewApproval,
  ReviewSidecar,
} from "@/lib/reviewTypes";
import type { ViewerIndex } from "@/lib/types";
import {
  assessSignoff,
  buildSemanticLedger,
  buildSignoffApproval,
  decisionLabel,
  defaultSemanticUnit,
  semanticReviewExport,
  type CoverageEntry,
  type RequiredDecision,
  type SemanticLedger,
  type SemanticUnit,
  type SignoffReadiness,
} from "./model";
import {
  commitSemanticApproval,
  commitSemanticDecision,
  getSemanticsState,
  hydrateSemantics,
  subscribeSemantics,
} from "./store";
import styles from "./semantics.module.css";

type StatusFilter = "all" | DecisionStatus;

const FILTERS: Array<{ id: StatusFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "open", label: "Open" },
  { id: "accepted", label: "Accepted" },
  { id: "rejected", label: "Rejected" },
  { id: "waived", label: "Waived" },
];

const KIND_ORDER: Record<SemanticUnit["kind"], number> = {
  limitation: 0,
  frame: 1,
  purpose: 2,
  claim: 3,
};

function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

let ledgerCache:
  | {
      index: ViewerIndex;
      review: ReviewSidecar | undefined;
      decisions: object;
      ledger: SemanticLedger;
    }
  | undefined;

function ledgerFor(
  index: ViewerIndex,
  review: ReviewSidecar | undefined,
  decisions: object,
): SemanticLedger {
  if (
    ledgerCache &&
    ledgerCache.index === index &&
    ledgerCache.review === review &&
    ledgerCache.decisions === decisions
  ) {
    return ledgerCache.ledger;
  }
  const ledger = buildSemanticLedger(index, review, decisions as never);
  ledgerCache = { index, review, decisions, ledger };
  return ledger;
}

interface SemanticsView {
  ledger: SemanticLedger;
  signoff: SignoffReadiness;
  unit?: SemanticUnit;
  requirement?: CoverageEntry;
  selectedKey?: string;
  selectUnit(unit: SemanticUnit): void;
  selectRequirement(requirement: RequiredDecision | CoverageEntry): void;
  snapshotName: string;
  decisions: ReturnType<typeof getSemanticsState>["decisions"];
  approvals: ReviewApproval[];
}

function useSemantics(props: FeatureProps): SemanticsView {
  const snapshotName = props.state.snapshot.name;
  const local = useSyncExternalStore(
    useCallback(
      (listener: () => void) => subscribeSemantics(snapshotName, listener),
      [snapshotName],
    ),
    useCallback(() => getSemanticsState(snapshotName), [snapshotName]),
    useCallback(() => getSemanticsState(snapshotName), [snapshotName]),
  );

  useEffect(() => {
    hydrateSemantics(snapshotName);
  }, [snapshotName]);

  const ledger = useMemo(
    () => ledgerFor(props.state.index, props.state.review, local.decisions),
    [props.state.index, props.state.review, local.decisions],
  );
  const signoff = useMemo(
    () =>
      assessSignoff(ledger.coverage, ledger.digest, {
        approvals: local.approvals,
      }),
    [ledger, local.approvals],
  );

  const selection = props.state.functions.semantics.selection;
  const selectedKey = selection.unitKey;
  const unit = selectedKey ? ledger.unitsByKey.get(selectedKey) : undefined;
  const requirement =
    selectedKey && !unit
      ? ledger.coverage.required.find((entry) => entry.key === selectedKey)
      : undefined;
  const fallback = defaultSemanticUnit(ledger);

  const selectUnit = useCallback(
    (next: SemanticUnit) => {
      props.actions.setSelection("semantics", {
        activity: "semantics",
        kind: "unit",
        unitKey: next.key,
        name: next.subject.name,
        component: next.subject.path,
      });
    },
    [props.actions],
  );

  const selectRequirement = useCallback(
    (next: RequiredDecision | CoverageEntry) => {
      props.actions.setSelection("semantics", {
        activity: "semantics",
        kind: "unit",
        unitKey: next.key,
        name: next.subject.name,
        component: next.subjectPath,
      });
    },
    [props.actions],
  );

  useEffect(() => {
    if (selectedKey || !fallback) return;
    selectUnit(fallback);
  }, [fallback, selectUnit, selectedKey]);

  return {
    ledger,
    signoff,
    unit: unit ?? (requirement ? undefined : fallback),
    requirement,
    selectedKey: unit?.key ?? requirement?.key,
    selectUnit,
    selectRequirement,
    snapshotName,
    decisions: local.decisions,
    approvals: local.approvals,
  };
}

function StatusBadge({ status }: { status: DecisionStatus | "mixed" | "none" }) {
  return (
    <span className={cx(styles.badge, styles[`badge_${status}`])}>
      {status === "mixed" || status === "none" ? status : decisionLabel(status)}
    </span>
  );
}

function unitMatches(unit: SemanticUnit, filter: StatusFilter, query: string, ledger: SemanticLedger): boolean {
  const status = ledger.statusByKey.get(unit.key) ?? "open";
  if (filter !== "all" && status !== filter) return false;
  if (!query.trim()) return true;
  const needle = query.trim().toLowerCase();
  return (
    unit.text.toLowerCase().includes(needle) ||
    unit.subjectPath.toLowerCase().includes(needle) ||
    unit.kind.includes(needle)
  );
}

function coverageSubjectMatches(entry: CoverageEntry, filter: StatusFilter, query: string): boolean {
  if (filter !== "all" && entry.status !== filter) return false;
  if (!query.trim()) return true;
  const needle = query.trim().toLowerCase();
  return (
    entry.title.toLowerCase().includes(needle) ||
    entry.detail.toLowerCase().includes(needle) ||
    entry.subjectPath.toLowerCase().includes(needle)
  );
}

function graphUnits(ledger: SemanticLedger, kind: SemanticUnit["kind"]): SemanticUnit[] {
  return ledger.units.filter(
    (unit) => unit.subject.kind === "graph" && unit.kind === kind,
  );
}

function unitKindLabel(kind: SemanticUnit["kind"]): string {
  switch (kind) {
    case "purpose":
      return "Purpose";
    case "claim":
      return "Claim";
    case "frame":
      return "Frame";
    default:
      return "Limitation";
  }
}

function requirementReasonLabel(reason: RequiredDecision["reason"]): string {
  switch (reason) {
    case "limitation":
      return "Limitation";
    case "untraced-property":
      return "No traced source";
    case "identity":
      return "Identity finding";
    case "type":
      return "Type finding";
    default:
      return "Abstract producer";
  }
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

export function SemanticsSidebar(props: FeatureProps): JSX.Element {
  const view = useSemantics(props);
  const { ledger } = view;
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");

  const groups = useMemo(
    () =>
      ledger.groups
        .map((group) => ({
          group,
          units: group.units.filter((unit) => unitMatches(unit, filter, query, ledger)),
        }))
        .filter((entry) => entry.units.length > 0),
    [ledger, filter, query],
  );

  const claims = graphUnits(ledger, "claim");
  const frames = graphUnits(ledger, "frame");
  const limitations = graphUnits(ledger, "limitation");
  const purpose = graphUnits(ledger, "purpose")[0];

  return (
    <div className={styles.sidebar} data-testid="semantics-sidebar">
      <section className={styles.purposeCard}>
        <p className={styles.kicker}>Graph purpose</p>
        <p className={styles.purposeText}>
          {purpose?.text ?? "No graph declaration purpose is attached."}
        </p>
        <div className={styles.metricGrid}>
          <div className={styles.metric}>
            <span className={styles.metricValue}>{ledger.counts.units}</span>
            <span className={styles.metricLabel}>Units</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricValue}>{ledger.counts.subjects}</span>
            <span className={styles.metricLabel}>Subjects</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricValue}>{ledger.counts.required}</span>
            <span className={styles.metricLabel}>Required</span>
          </div>
          <div className={styles.metric}>
            <span className={cx(styles.metricValue, view.signoff.ready && styles.metricReady)}>
              {ledger.coverage.open}
            </span>
            <span className={styles.metricLabel}>Open</span>
          </div>
        </div>
      </section>

      <section className={styles.sideSection}>
        <header className={styles.sideHeader}>
          <span>Decision status</span>
          <span className={styles.sideCount}>{ledger.coverage.open} open</span>
        </header>
        <div className={styles.filterRail} role="group" aria-label="Decision status filters">
          {FILTERS.map((entry) => (
            <button
              key={entry.id}
              type="button"
              className={styles.filterButton}
              aria-pressed={filter === entry.id}
              onClick={() => setFilter(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </div>
        <label className={styles.searchField}>
          <Search aria-hidden className="size-3" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Find a unit or subject"
          />
        </label>
      </section>

      <section className={styles.sideSection}>
        <header className={styles.sideHeader}>
          <span>Graph claims</span>
          <span className={styles.sideCount}>{claims.length}</span>
        </header>
        <div className={styles.unitList}>
          {claims.map((unit) => (
            <button
              key={unit.key}
              type="button"
              className={styles.unitRow}
              data-selected={view.unit?.key === unit.key ? "true" : undefined}
              onClick={() => view.selectUnit(unit)}
              title={unit.text}
            >
              <span className={styles.unitText}>{unit.text}</span>
              <StatusBadge status={ledger.statusByKey.get(unit.key) ?? "proposed"} />
            </button>
          ))}
          {!claims.length ? <p className={styles.empty}>No graph claims.</p> : null}
        </div>
      </section>

      <section className={styles.sideSection}>
        <header className={styles.sideHeader}>
          <span>Frames and limitations</span>
          <span className={styles.sideCount}>{frames.length + limitations.length}</span>
        </header>
        <div className={styles.unitList}>
          {frames.map((unit) => (
            <div key={unit.key} className={styles.frameGroup}>
              <button
                type="button"
                className={styles.unitRow}
                data-selected={view.unit?.key === unit.key ? "true" : undefined}
                onClick={() => view.selectUnit(unit)}
                title={unit.text}
              >
                <span className={styles.unitText}>{unit.text}</span>
                <StatusBadge status={ledger.statusByKey.get(unit.key) ?? "proposed"} />
              </button>
              {limitations
                .filter((limitation) => limitation.frame === unit.text)
                .map((limitation) => (
                  <button
                    key={limitation.key}
                    type="button"
                    className={cx(styles.unitRow, styles.limitationRow)}
                    data-selected={view.unit?.key === limitation.key ? "true" : undefined}
                    onClick={() => view.selectUnit(limitation)}
                    title={limitation.text}
                  >
                    <span className={styles.unitText}>{limitation.text}</span>
                    <StatusBadge status={ledger.statusByKey.get(limitation.key) ?? "open"} />
                  </button>
                ))}
            </div>
          ))}
          {!frames.length ? <p className={styles.empty}>No framed statements.</p> : null}
        </div>
      </section>

      <section className={styles.sideSection}>
        <header className={styles.sideHeader}>
          <span>Subjects</span>
          <span className={styles.sideCount}>{groups.length}</span>
        </header>
        <div className={styles.subjectList}>
          {groups.map(({ group, units }) => {
            const first = units[0];
            const open = group.units.filter(
              (unit) => (ledger.statusByKey.get(unit.key) ?? "open") === "open",
            ).length;
            return (
              <button
                key={group.key}
                type="button"
                className={styles.subjectRow}
                data-selected={
                  view.unit?.subjectKey === group.key ? "true" : undefined
                }
                onClick={() => first && view.selectUnit(first)}
                title={group.path}
              >
                <span className={styles.subjectMain}>
                  <span className={styles.subjectKind}>{group.kind}</span>
                  <span className={styles.subjectName}>{group.name}</span>
                </span>
                <span className={styles.subjectMeta}>
                  {open ? <span className={styles.openDot} title={`${open} open`} /> : null}
                  <span className={styles.unitCount}>{units.length}</span>
                  <ChevronRight aria-hidden className="size-3" />
                </span>
              </button>
            );
          })}
          {!groups.length ? <p className={styles.empty}>No subject matches this filter.</p> : null}
        </div>
      </section>

      <section className={styles.sideSection}>
        <header className={styles.sideHeader}>
          <span>Coverage</span>
          <span className={styles.sideCount}>
            {ledger.coverage.resolved}/{ledger.coverage.total}
          </span>
        </header>
        <div className={styles.coverageBar} aria-hidden>
          <span
            style={{
              width: `${
                ledger.coverage.total
                  ? (ledger.coverage.resolved / ledger.coverage.total) * 100
                  : 100
              }%`,
            }}
          />
        </div>
        <p className={styles.coverageCopy}>
          {ledger.coverage.open === 0
            ? "Every required decision is resolved."
            : `${ledger.coverage.open} required decision${
                ledger.coverage.open === 1 ? "" : "s"
              } still open.`}
        </p>
        <div className={styles.unitList}>
          {ledger.coverage.required
            .filter((entry) => !entry.resolved)
            .slice(0, 6)
            .map((entry) => (
              <button
                key={entry.key}
                type="button"
                className={styles.coverageRow}
                onClick={() => view.selectRequirement(entry)}
                title={entry.detail}
              >
                <span className={styles.coverageReason}>
                  {requirementReasonLabel(entry.reason)}
                </span>
                <span className={styles.coverageTitle}>{entry.title}</span>
              </button>
            ))}
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

export function SemanticsEditor(props: FeatureProps): JSX.Element {
  const view = useSemantics(props);
  const { ledger } = view;
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState<string | undefined>();

  const targetKey = view.unit?.key ?? view.requirement?.key;
  const coverageEntry = targetKey
    ? ledger.coverage.required.find((entry) => entry.key === targetKey)
    : undefined;
  const currentDecision = targetKey ? view.decisions[targetKey] : undefined;
  const currentStatus: DecisionStatus =
    (targetKey ? ledger.statusByKey.get(targetKey) : undefined) ??
    coverageEntry?.status ??
    "open";

  const [decisionStatus, setDecisionStatus] = useState<DecisionStatus>(currentStatus);
  const [rationale, setRationale] = useState("");
  const [decisionReviewer, setDecisionReviewer] = useState("");
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    setDecisionStatus(currentStatus);
    setRationale(
      currentDecision?.rationale ??
        (view.requirement?.decision?.rationale ?? ""),
    );
    setDecisionReviewer(currentDecision?.reviewer ?? reviewer);
    setError(undefined);
    // The target key and the stored decision are the state reset boundary.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetKey, currentDecision?.rationale, currentDecision?.reviewer, currentStatus]);

  const requiredUnits = useMemo(
    () => new Set(ledger.required.map((entry) => entry.unitKey).filter(Boolean)),
    [ledger.required],
  );

  const visibleUnits = useMemo(() => {
    const units = ledger.units.filter((unit) =>
      unitMatches(unit, filter, query, ledger),
    );
    return [...units].sort((left, right) => {
      const required =
        Number(requiredUnits.has(right.key)) - Number(requiredUnits.has(left.key));
      if (required) return required;
      const kind = KIND_ORDER[left.kind] - KIND_ORDER[right.kind];
      if (kind) return kind;
      const subject = left.subjectPath.localeCompare(right.subjectPath);
      return subject || left.text.localeCompare(right.text);
    });
  }, [ledger, filter, query, requiredUnits]);

  const visibleCoverage = useMemo(
    () =>
      ledger.coverage.required
        .filter((entry) => coverageSubjectMatches(entry, filter, query))
        .sort((left, right) => {
          if (left.resolved !== right.resolved) return left.resolved ? 1 : -1;
          return left.title.localeCompare(right.title);
        }),
    [ledger.coverage.required, filter, query],
  );

  const readiness = useMemo(
    () =>
      assessSignoff(ledger.coverage, ledger.digest, {
        reviewer: reviewer || signoffReviewer(view.approvals),
        at: reviewer || signoffReviewer(view.approvals) ? "pending" : undefined,
        approvals: view.approvals,
      }),
    [ledger.coverage, ledger.digest, reviewer, view.approvals],
  );

  const commitDecision = () => {
    if (!targetKey) return;
    try {
      commitSemanticDecision(view.snapshotName, targetKey, decisionStatus, {
        rationale,
        reviewer: decisionReviewer,
        at: new Date().toISOString(),
      });
      setError(undefined);
      setNotice(`Recorded ${decisionLabel(decisionStatus).toLowerCase()} for this decision.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const signOff = () => {
    const effectiveReviewer = reviewer.trim() || signoffReviewer(view.approvals);
    if (!effectiveReviewer || ledger.coverage.open > 0) return;
    const at = new Date().toISOString();
    const approval = buildSignoffApproval(
      ledger.digest,
      ledger.coverage,
      effectiveReviewer,
      at,
      note,
    );
    commitSemanticApproval(view.snapshotName, approval);
    props.actions.updateReview({
      ...props.state.review,
      approvals: [
        approval,
        ...(props.state.review.approvals ?? []).filter(
          (entry) => entry.id !== approval.id,
        ),
      ],
    });
    setNotice(`Signed off by ${effectiveReviewer} at ${at}.`);
  };

  const exportReview = () => {
    const payload = semanticReviewExport(ledger, {
      reviewer: reviewer || signoffReviewer(view.approvals),
      at: new Date().toISOString(),
      approvals: view.approvals,
    });
    const text = JSON.stringify(payload, null, 2);
    if (typeof document === "undefined") return;
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${view.snapshotName}.semantics.review.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice("Exported the semantic review JSON.");
  };

  return (
    <div className={styles.editor} data-testid="semantics-editor">
      <header className={styles.editorHeader}>
        <div className={styles.editorTitle}>
          <span className={styles.titleIcon}>
            <ScrollText aria-hidden className="size-[18px]" />
          </span>
          <div>
            <p className={styles.kicker}>Orientation</p>
            <h1>{ledger.graphName || "Graph"}</h1>
            <p className={styles.lede}>
              Understand what this graph is before auditing it: its purpose,
              frames, claims and limits. The ledger below records what is
              attached and what still needs a decision.
            </p>
            <div className={styles.orientationActions}>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={() => props.actions.setActivity("audit")}
              >
                Start with the Audit
                <span aria-hidden>→</span>
              </button>
              <span className={styles.orientationPath}>
                Orient · Audit · Proof · Topology
              </span>
            </div>
          </div>
        </div>
        <div className={styles.headerMeta}>
          <span className={styles.digestChip} title={ledger.digest}>
            digest {ledger.shortDigest}
          </span>
          <span className={cx(styles.signoffChip, view.signoff.ready && styles.signoffReady)}>
            {view.signoff.approved
              ? "Signed off"
              : view.signoff.ready
                ? "Ready to sign"
                : `${ledger.coverage.open} open`}
          </span>
        </div>
      </header>

      <div className={styles.editorBody}>
        <div className={styles.mainColumn}>
        <section className={styles.purposePanel} data-level="section">
          <header className={styles.panelHeader}>
            <span className={styles.panelTitle}>Purpose</span>
            <span className={styles.panelCount}>
              {ledger.counts.claims} claims · {ledger.counts.frames} frames ·{" "}
              {ledger.counts.limitations} limitations
            </span>
          </header>
          <p className={styles.purposeBody}>
            {graphUnits(ledger, "purpose")[0]?.text ??
              "The graph declaration carries no purpose text."}
          </p>
          <div className={styles.purposeClaims}>
            {graphUnits(ledger, "claim").map((claim) => (
              <button
                key={claim.key}
                type="button"
                className={styles.claimChip}
                data-selected={view.unit?.key === claim.key ? "true" : undefined}
                onClick={() => view.selectUnit(claim)}
                title={claim.text}
              >
                {claim.text}
              </button>
            ))}
            {graphUnits(ledger, "frame").map((frame) => (
              <button
                key={frame.key}
                type="button"
                className={cx(styles.claimChip, styles.frameChip)}
                data-selected={view.unit?.key === frame.key ? "true" : undefined}
                onClick={() => view.selectUnit(frame)}
                title={frame.text}
              >
                Frame: {frame.text}
              </button>
            ))}
          </div>
        </section>

        <section className={styles.ledgerPanel}>
            <header className={styles.panelHeader}>
              <span className={styles.panelTitle}>Ledger</span>
              <span className={styles.panelCount}>
                {visibleUnits.length} of {ledger.units.length} units
              </span>
            </header>
            <div className={styles.ledgerToolbar}>
              <div className={styles.filterRail} role="group" aria-label="Ledger status filters">
                {FILTERS.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    className={styles.filterButton}
                    aria-pressed={filter === entry.id}
                    onClick={() => setFilter(entry.id)}
                  >
                    {entry.label}
                  </button>
                ))}
              </div>
              <label className={styles.searchField}>
                <Search aria-hidden className="size-3" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Find a unit"
                />
              </label>
            </div>
            <div className={styles.ledgerScroll}>
              <table className={styles.ledgerTable}>
                <thead>
                  <tr>
                    <th>Kind</th>
                    <th>Text</th>
                    <th>Subject</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleUnits.slice(0, 400).map((unit) => {
                    const status = ledger.statusByKey.get(unit.key) ?? "open";
                    return (
                      <tr
                        key={unit.key}
                        data-selected={view.unit?.key === unit.key ? "true" : undefined}
                        onClick={() => view.selectUnit(unit)}
                      >
                        <td>
                          <span className={cx(styles.kindBadge, styles[`kind_${unit.kind}`])}>
                            {unitKindLabel(unit.kind)}
                          </span>
                        </td>
                        <td className={styles.ledgerText}>{unit.text}</td>
                        <td className={styles.ledgerSubject} title={unit.subjectPath}>
                          {unit.subjectPath}
                        </td>
                        <td>
                          <StatusBadge status={status} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {!visibleUnits.length ? (
                <p className={styles.empty}>No unit matches this filter.</p>
              ) : null}
              {visibleUnits.length > 400 ? (
                <p className={styles.tableNote}>
                  Showing the first 400 of {visibleUnits.length}. Filter or search to
                  narrow the ledger.
                </p>
              ) : null}
            </div>
          </section>

          <section className={styles.coveragePanel}>
            <header className={styles.panelHeader}>
              <span className={styles.panelTitle}>Required coverage</span>
              <span className={styles.panelCount}>
                {ledger.coverage.resolved}/{ledger.coverage.total} resolved
              </span>
            </header>
            <div className={styles.coverageList}>
              {visibleCoverage.slice(0, 12).map((entry) => (
                <button
                  key={entry.key}
                  type="button"
                  className={styles.coverageListItem}
                  data-resolved={entry.resolved ? "true" : undefined}
                  onClick={() => view.selectRequirement(entry)}
                  title={entry.detail}
                >
                  <span className={styles.coverageListReason}>
                    {requirementReasonLabel(entry.reason)}
                  </span>
                  <span className={styles.coverageListTitle}>{entry.title}</span>
                  <StatusBadge status={entry.status} />
                </button>
              ))}
              {!visibleCoverage.length ? (
                <p className={styles.empty}>No required decision matches this filter.</p>
              ) : null}
            </div>
          </section>

        </div>

        <div className={styles.sideColumn}>
          <aside className={styles.detailPanel}>
            <header className={styles.panelHeader}>
              <span className={styles.panelTitle}>Selected unit</span>
              <span className={styles.panelCount}>{view.unit ? "attached" : "required"}</span>
            </header>

            {view.unit ? (
              <div className={styles.detailBody}>
                <div className={styles.detailKinds}>
                  <span className={cx(styles.kindBadge, styles[`kind_${view.unit.kind}`])}>
                    {unitKindLabel(view.unit.kind)}
                  </span>
                  <StatusBadge status={currentStatus} />
                </div>
                <p className={styles.detailText}>{view.unit.text}</p>
                {view.unit.frame ? (
                  <p className={styles.detailFrame}>
                    <span>Frame</span> {view.unit.frame}
                  </p>
                ) : null}
                <dl className={styles.factList}>
                  <div>
                    <dt>Subject</dt>
                    <dd>{view.unit.subjectPath}</dd>
                  </div>
                  <div>
                    <dt>Unit key</dt>
                    <dd className={styles.mono} title={view.unit.key}>
                      {view.unit.shortKey}
                    </dd>
                  </div>
                  <div>
                    <dt>Evidence</dt>
                    <dd>
                      {view.unit.attached
                        ? "Attached to this subject only; no propagation."
                        : "Graph declaration."}
                    </dd>
                  </div>
                </dl>
              </div>
            ) : view.requirement ? (
              <div className={styles.detailBody}>
                <div className={styles.detailKinds}>
                  <span className={styles.requirementBadge}>
                    {requirementReasonLabel(view.requirement.reason)}
                  </span>
                  <StatusBadge status={view.requirement.status} />
                </div>
                <p className={styles.detailText}>{view.requirement.title}</p>
                <p className={styles.detailFrame}>{view.requirement.detail}</p>
                <dl className={styles.factList}>
                  <div>
                    <dt>Subject</dt>
                    <dd>{view.requirement.subjectPath}</dd>
                  </div>
                  <div>
                    <dt>Requirement</dt>
                    <dd className={styles.mono} title={view.requirement.key}>
                      {view.requirement.key}
                    </dd>
                  </div>
                </dl>
              </div>
            ) : (
              <p className={styles.empty}>The snapshot carries no semantic units.</p>
            )}

            {targetKey ? (
              <div className={styles.decisionForm}>
                <p className={styles.formLabel}>Decision</p>
                <div className={styles.decisionButtons}>
                  {(["accepted", "rejected", "waived", "open"] as DecisionStatus[]).map(
                    (status) => (
                      <button
                        key={status}
                        type="button"
                        className={cx(
                          styles.decisionButton,
                          decisionStatus === status && styles.decisionButtonActive,
                          status === "accepted" && styles.decisionAccept,
                          status === "rejected" && styles.decisionReject,
                          status === "waived" && styles.decisionWaive,
                        )}
                        aria-pressed={decisionStatus === status}
                        onClick={() => setDecisionStatus(status)}
                      >
                        {status === "accepted" ? <Check aria-hidden className="size-3" /> : null}
                        {status === "rejected" ? <X aria-hidden className="size-3" /> : null}
                        {status === "open" ? <CircleDot aria-hidden className="size-3" /> : null}
                        {status === "waived" ? <AlertTriangle aria-hidden className="size-3" /> : null}
                        {decisionLabel(status)}
                      </button>
                    ),
                  )}
                </div>
                <label className={styles.formField}>
                  <span>Rationale</span>
                  <textarea
                    value={rationale}
                    onChange={(event) => setRationale(event.target.value)}
                    rows={2}
                    placeholder="State the reason this decision is correct."
                  />
                </label>
                <label className={styles.formField}>
                  <span>Reviewer</span>
                  <input
                    value={decisionReviewer}
                    onChange={(event) => setDecisionReviewer(event.target.value)}
                    placeholder="Name or handle"
                  />
                </label>
                {error ? <p className={styles.error}>{error}</p> : null}
                <button type="button" className={styles.primaryButton} onClick={commitDecision}>
                  Record decision
                </button>
              </div>
            ) : null}
          </aside>

          <section className={styles.signoffPanel}>
            <header className={styles.panelHeader}>
              <span className={styles.panelTitle}>Sign-off</span>
              <span className={cx(styles.panelCount, readiness.ready && styles.readyText)}>
                {view.signoff.approved
                  ? "approved"
                  : readiness.ready
                    ? "ready"
                    : "blocked"}
              </span>
            </header>
            <div className={styles.signoffBody}>
              <div className={styles.signoffStatus}>
                <ShieldCheck aria-hidden className="size-4" />
                <div>
                  <p>
                    {view.signoff.approved
                      ? `Approved by ${view.signoff.reviewer ?? "a reviewer"}`
                      : readiness.ready
                        ? "All required decisions are resolved."
                        : "Resolve every blocker before sign-off."}
                  </p>
                  <p className={styles.signoffDetail}>
                    Snapshot digest <span className={styles.mono}>{ledger.digest}</span>
                  </p>
                </div>
              </div>
              {readiness.blockers.length ? (
                <ul className={styles.blockers}>
                  {readiness.blockers.map((blocker) => (
                    <li key={blocker}>
                      <AlertTriangle aria-hidden className="size-3" />
                      {blocker}
                    </li>
                  ))}
                </ul>
              ) : null}
              <label className={styles.formField}>
                <span>Reviewer</span>
                <input
                  value={reviewer}
                  onChange={(event) => setReviewer(event.target.value)}
                  placeholder="Name or handle"
                />
              </label>
              <div className={styles.signoffActions}>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={signOff}
                  disabled={!readiness.ready}
                >
                  <ShieldCheck aria-hidden className="size-3.5" />
                  Sign off
                </button>
                <button type="button" className={styles.secondaryButton} onClick={exportReview}>
                  <Download aria-hidden className="size-3.5" />
                  Export JSON
                </button>
              </div>
              <label className={styles.formField}>
                <span>Sign-off note</span>
                <input
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Optional note"
                />
              </label>
              {notice ? <p className={styles.notice}>{notice}</p> : null}
              {view.approvals.length ? (
                <div className={styles.approvalList}>
                  {view.approvals.slice(0, 4).map((approval) => (
                    <div key={approval.id} className={styles.approvalRow}>
                      <span>{approval.status}</span>
                      <span>{approval.reviewer}</span>
                      <span className={styles.mono}>{approval.at}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function signoffReviewer(approvals: ReviewApproval[]): string {
  return (
    approvals
      .filter((approval) => approval.status === "signed-off")
      .sort((left, right) => right.at.localeCompare(left.at))[0]?.reviewer ?? ""
  );
}

// ---------------------------------------------------------------------------
// Bottom panel
// ---------------------------------------------------------------------------

export function SemanticsBottom(props: FeatureProps): JSX.Element {
  const view = useSemantics(props);
  const { ledger } = view;
  const tab = props.state.functions.semantics.layout.bottomTab;

  if (tab === "coverage") {
    return (
      <div className={styles.bottom} data-testid="semantics-bottom">
        <header className={styles.bottomHeader}>
          <span>Required decisions</span>
          <span>
            {ledger.coverage.resolved}/{ledger.coverage.total} resolved ·{" "}
            {ledger.coverage.open} open
          </span>
        </header>
        <div className={styles.bottomList}>
          {ledger.coverage.required.map((entry) => (
            <button
              key={entry.key}
              type="button"
              className={styles.bottomRow}
              onClick={() => view.selectRequirement(entry)}
            >
              <span className={styles.bottomReason}>
                {requirementReasonLabel(entry.reason)}
              </span>
              <span className={styles.bottomTitle}>{entry.title}</span>
              <span className={styles.bottomSubject}>{entry.subjectPath}</span>
              <StatusBadge status={entry.status} />
            </button>
          ))}
          {!ledger.coverage.required.length ? (
            <p className={styles.empty}>No decision is required by this snapshot.</p>
          ) : null}
        </div>
      </div>
    );
  }

  if (tab === "data") {
    return (
      <div className={styles.bottom} data-testid="semantics-bottom">
        <header className={styles.bottomHeader}>
          <span>Unit and review JSON</span>
          <span className={styles.mono}>{ledger.digest}</span>
        </header>
        <pre className={styles.dataBlock}>
          {JSON.stringify(
            semanticReviewExport(ledger, {
              approvals: view.approvals,
              reviewer: signoffReviewer(view.approvals),
            }),
            null,
            2,
          )}
        </pre>
      </div>
    );
  }

  const rows = [
    ...ledger.decisions.filter((decision) => decision.source === "sidecar"),
    ...ledger.decisions.filter((decision) => decision.source === "queue"),
  ];

  return (
    <div className={styles.bottom} data-testid="semantics-bottom">
      <header className={styles.bottomHeader}>
        <span>Decisions</span>
        <span>
          {rows.length} recorded · {ledger.coverage.open} required still open
        </span>
      </header>
      <div className={styles.bottomList}>
        {rows.map((decision) => (
          <button
            key={`${decision.source}:${decision.id}`}
            type="button"
            className={styles.bottomRow}
            onClick={() => {
              const unit = ledger.unitsByKey.get(decision.key);
              if (unit) {
                view.selectUnit(unit);
                return;
              }
              const entry = ledger.coverage.required.find(
                (candidate) => candidate.key === decision.key,
              );
              if (entry) view.selectRequirement(entry);
            }}
          >
            <span className={styles.bottomReason}>{decision.source}</span>
            <span className={styles.bottomTitle}>
              {decision.title === decision.key
                ? ledger.unitsByKey.get(decision.key)?.text ?? decision.key
                : decision.title}
            </span>
            <span className={styles.bottomSubject}>
              {decision.rationale || "No rationale captured."}
            </span>
            <StatusBadge status={decision.status} />
          </button>
        ))}
        {!rows.length ? (
          <div className={styles.emptyBottom}>
            <FileText aria-hidden className="size-4" />
            <div>
              <p>No decisions are recorded yet.</p>
              <p>
                The sidecar is empty and the local queue has no semantic
                decisions for this snapshot.
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

