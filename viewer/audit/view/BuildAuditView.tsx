"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { PanelHeader } from "@/shared/ui/PanelHeader";
import { Section } from "@/shared/ui/Section";
import { cx } from "@/shared/ui/theme";
import { AUDIT_BOUNDS } from "@/audit/view/bounds";
import { ActionButton, AuditIcon } from "@/audit/view/AuditControls";
import {
  BuildBody,
  CoverageBody,
  DecisionsBody,
  DiffBody,
  DossierBody,
  FindingsBody,
  QuestionsBody,
  SummaryBody,
} from "@/audit/view/AuditSections";
import {
  formatCount,
  type AuditFindingRow,
  type AuditFindingsSection,
  type AuditModel,
  type AuditSectionModel,
} from "@/audit/model/AuditModel";

export interface BuildAuditViewProps {
  model: AuditModel;
}

/**
 * The audit view binds to an injected `AuditModel`.
 *
 * It owns only view state: the active rail entry, which sections are open, the
 * local filter values, the waiver draft and the bounded row counts. It never
 * builds the model and never imports the campaign or the audit engine.
 */
export function BuildAuditView({ model }: BuildAuditViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeSection, setActiveSection] = useState(
    model.sections[0]?.id ?? "summary",
  );
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(
    () =>
      Object.fromEntries(
        model.sections.map((section) => [section.id, section.defaultOpen]),
      ),
  );

  const [severityFilter, setSeverityFilter] = useState("all");
  const [ruleFilter, setRuleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [tagFilter, setTagFilter] = useState("all");
  const [findingsLimit, setFindingsLimit] = useState(AUDIT_BOUNDS.findings);
  const [questionsLimit, setQuestionsLimit] = useState(AUDIT_BOUNDS.questions);
  const [waivingId, setWaivingId] = useState<string | undefined>();
  const [draftNote, setDraftNote] = useState("");
  const [coverageShowAll, setCoverageShowAll] = useState(false);
  const [decisionsShowAll, setDecisionsShowAll] = useState(false);

  const findingsSection = model.sections.find(
    (section): section is AuditFindingsSection => section.kind === "findings",
  );

  const subjectKey = model.subject.subject
    ? JSON.stringify(model.subject.subject)
    : "";

  // A new subject or a filter change resets the bounded mount.
  useEffect(() => {
    setFindingsLimit(AUDIT_BOUNDS.findings);
  }, [subjectKey, severityFilter, ruleFilter, statusFilter, tagFilter]);

  useEffect(() => {
    setQuestionsLimit(AUDIT_BOUNDS.questions);
    setWaivingId(undefined);
    setDraftNote("");
  }, [subjectKey]);

  const filteredFindings = useMemo(() => {
    const rows = findingsSection?.rows ?? [];
    return rows.filter((row) => {
      if (severityFilter !== "all" && row.severity !== severityFilter) {
        return false;
      }
      if (ruleFilter !== "all" && row.rule !== ruleFilter) return false;
      if (statusFilter !== "all" && row.status !== statusFilter) return false;
      if (tagFilter !== "all" && !row.tags.includes(tagFilter)) return false;
      return true;
    });
  }, [findingsSection, ruleFilter, severityFilter, statusFilter, tagFilter]);

  const visibleFindings = useMemo(() => {
    const limited = filteredFindings.slice(0, findingsLimit);
    if (
      model.selectedFindingId &&
      !limited.some((row) => row.findingId === model.selectedFindingId)
    ) {
      const selected = filteredFindings.find(
        (row) => row.findingId === model.selectedFindingId,
      );
      if (selected) return [...limited, selected];
    }
    return limited;
  }, [filteredFindings, findingsLimit, model.selectedFindingId]);

  const questions = useMemo(
    () => model.sections.find((section) => section.kind === "questions"),
    [model.sections],
  );
  const visibleQuestionRows = useMemo(
    () =>
      questions && questions.kind === "questions"
        ? questions.rows.slice(0, questionsLimit)
        : [],
    [questions, questionsLimit],
  );

  const activeFilters =
    (severityFilter !== "all" ? 1 : 0) +
    (ruleFilter !== "all" ? 1 : 0) +
    (statusFilter !== "all" ? 1 : 0) +
    (tagFilter !== "all" ? 1 : 0);

  function clearFilters() {
    setSeverityFilter("all");
    setRuleFilter("all");
    setStatusFilter("all");
    setTagFilter("all");
  }

  function startWaiver(row: AuditFindingRow) {
    if (waivingId === row.findingId) {
      setWaivingId(undefined);
      return;
    }
    setWaivingId(row.findingId);
    setDraftNote(row.note ?? "");
  }

  function saveWaiver(row: AuditFindingRow) {
    const note = draftNote.trim();
    if (!note) return;
    model.commands.setStatus(row.findingId, "waived", note);
    setWaivingId(undefined);
    setDraftNote("");
  }

  function cancelWaiver() {
    setWaivingId(undefined);
    setDraftNote("");
  }

  function goToSection(section: AuditSectionModel) {
    setActiveSection(section.id);
    const scroller = scrollRef.current;
    const target = scroller?.querySelector<HTMLElement>(
      `[data-testid="${section.testId}"]`,
    );
    if (!scroller || !target) return;
    // Scroll the panel body only. `scrollIntoView` also scrolls the document
    // when the panel overflows, which shifted the whole workbench.
    const delta =
      target.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
    scroller.scrollTop += delta;
  }

  function sectionActions(section: AuditSectionModel): ReactNode {
    switch (section.kind) {
      case "findings": {
        if (filteredFindings.length <= AUDIT_BOUNDS.findings) return null;
        if (findingsLimit < filteredFindings.length) {
          return (
            <ActionButton
              action={section.showAll}
              label={`Show all ${formatCount(filteredFindings.length)}`}
              variant="ghost"
              onActivate={() => setFindingsLimit(filteredFindings.length)}
            />
          );
        }
        return (
          <ActionButton
            action={section.showLess}
            variant="ghost"
            onActivate={() => setFindingsLimit(AUDIT_BOUNDS.findings)}
          />
        );
      }
      case "coverage": {
        if (section.rows.length <= AUDIT_BOUNDS.coverage) return null;
        return coverageShowAll ? (
          <ActionButton
            action={section.showLess}
            variant="ghost"
            onActivate={() => setCoverageShowAll(false)}
          />
        ) : (
          <ActionButton
            action={section.showAll}
            label={`Show all ${formatCount(section.rows.length)}`}
            variant="ghost"
            onActivate={() => setCoverageShowAll(true)}
          />
        );
      }
      case "decisions": {
        if (section.rows.length <= AUDIT_BOUNDS.decisions) return null;
        return decisionsShowAll ? (
          <ActionButton
            action={section.showLess}
            variant="ghost"
            onActivate={() => setDecisionsShowAll(false)}
          />
        ) : (
          <ActionButton
            action={section.showAll}
            label={`Show all ${formatCount(section.rows.length)}`}
            variant="ghost"
            onActivate={() => setDecisionsShowAll(true)}
          />
        );
      }
      case "diff":
        return (
          <label className="ui-button ui-button-primary h-[26px] min-h-0 cursor-pointer px-2 text-[11px]">
            <AuditIcon token={section.compare.icon ?? "branch"} className="size-3" />
            {section.compare.label}
            <input
              data-testid={section.compare.testId}
              type="file"
              accept="application/json,.json"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) model.commands.compareSnapshot(file);
                event.target.value = "";
              }}
            />
          </label>
        );
      // The dossier body is the action list; repeating it in the band header
      // would publish the same test id twice and crowd the band.
      case "dossier":
        return null;
      default:
        return section.actions?.length ? (
          <>
            {section.actions.map((action) => (
              <ActionButton
                key={action.id}
                action={action}
                variant="ghost"
              />
            ))}
          </>
        ) : null;
    }
  }

  function sectionBody(section: AuditSectionModel): ReactNode {
    switch (section.kind) {
      case "summary":
        return <SummaryBody section={section} />;
      case "findings":
        return (
          <FindingsBody
            section={section}
            rows={visibleFindings}
            filters={model.filters}
            severityFilter={severityFilter}
            ruleFilter={ruleFilter}
            statusFilter={statusFilter}
            tagFilter={tagFilter}
            activeFilters={activeFilters}
            subjectLabel={model.subject.label}
            subjectFiltered={Boolean(model.subject.subject)}
            selectedFindingId={model.selectedFindingId}
            onSeverityFilter={setSeverityFilter}
            onRuleFilter={setRuleFilter}
            onStatusFilter={setStatusFilter}
            onTagFilter={setTagFilter}
            onClearFilters={clearFilters}
            onSelectFinding={model.commands.selectFinding}
            waivingId={waivingId}
            draftNote={draftNote}
            onDraftNote={setDraftNote}
            onStartWaiver={startWaiver}
            onSaveWaiver={saveWaiver}
            onCancelWaiver={cancelWaiver}
          />
        );
      case "questions":
        return (
          <QuestionsBody
            section={section}
            rows={visibleQuestionRows}
            subjectFiltered={Boolean(model.subject.subject)}
            onLoadMore={() =>
              setQuestionsLimit((value) => value + AUDIT_BOUNDS.questions)
            }
          />
        );
      case "coverage":
        return <CoverageBody section={section} showAll={coverageShowAll} />;
      case "decisions":
        return (
          <DecisionsBody section={section} showAll={decisionsShowAll} />
        );
      case "build":
        return <BuildBody section={section} />;
      case "diff":
        return <DiffBody section={section} />;
      case "dossier":
        return <DossierBody section={section} />;
    }
  }

  function renderSection(section: AuditSectionModel) {
    const open = openSections[section.id] ?? section.defaultOpen;
    return (
      <Section
        key={section.id}
        title={section.title}
        question={section.question}
        count={
          section.kind === "findings"
            ? `${formatCount(filteredFindings.length)} shown`
            : section.count
        }
        actions={sectionActions(section)}
        testId={section.testId}
        toggleTestId={section.toggleTestId}
        collapsible={section.collapsible}
        open={open}
        onOpenChange={(next) =>
          setOpenSections((current) => ({ ...current, [section.id]: next }))
        }
        lazy
        bodyClassName="p-0"
      >
        {sectionBody(section)}
      </Section>
    );
  }

  const fullSections = model.sections.filter(
    (section) => section.layout === "full",
  );
  const leftSections = model.sections.filter(
    (section) => section.layout === "left",
  );
  const rightSections = model.sections.filter(
    (section) => section.layout === "right",
  );
  const tailSections = model.sections.filter(
    (section) => section.layout === "full-tail",
  );

  return (
    <section
      data-testid="review-tab-content"
      data-level="panel"
      aria-label="Audit"
      className="flex h-full min-h-0 min-w-0 flex-1 flex-col bg-panel text-text"
    >
      <PanelHeader
        title={model.panel.title}
        icon={<AuditIcon token={model.panel.icon} className="size-3.5" />}
        meta={model.counts
          .filter((count) => !count.active)
          .map((count) => `${formatCount(count.value)} ${count.label}`)
          .join(" · ")}
      />
      <div className="flex min-h-0 flex-1">
        <nav
          data-testid="review-section-rail"
          aria-label="Review sections"
          className="ui-properties-rail"
        >
          {model.rails.map((rail) => {
            const active = activeSection === rail.id;
            const section = model.sections.find(
              (candidate) => candidate.id === rail.id,
            );
            return (
              <button
                key={rail.id}
                type="button"
                data-testid={rail.testId}
                onClick={() => section && goToSection(section)}
                aria-label={rail.label}
                aria-current={active ? "true" : undefined}
                title={rail.label}
                className={cx(
                  "ui-properties-rail-tab ui-focus-ring",
                  active
                    ? "bg-accent text-white"
                    : "text-faint hover:bg-panel-soft hover:text-muted",
                )}
              >
                <AuditIcon token={rail.icon} className="size-4" />
              </button>
            );
          })}
        </nav>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div
            data-testid="review-toolbar"
            data-level="panel-toolbar"
            className="ui-editor-header flex h-8 shrink-0 items-center gap-3 px-3"
          >
            <div className="flex min-w-0 items-center gap-3 overflow-hidden">
              {model.counts.map((count, index) => (
                <span
                  key={count.id}
                  className={cx(
                    "flex shrink-0 items-baseline gap-1.5 whitespace-nowrap text-[11.5px]",
                    index > 0 && "border-l border-line pl-3",
                    count.active ? "text-accent" : "text-muted",
                  )}
                >
                  <span
                    className={cx(
                      "font-mono tabular-nums",
                      count.active ? "text-accent-strong" : "text-text",
                    )}
                  >
                    {formatCount(count.value)}
                  </span>
                  {count.label}
                  {count.detail ? (
                    <span className="text-faint">· {count.detail}</span>
                  ) : null}
                </span>
              ))}
            </div>

            <div
              data-testid="subject-filter"
              className="ml-auto flex min-w-0 shrink-0 items-center gap-2"
            >
              <span className="shrink-0 text-[11px] text-faint">Subject</span>
              <span
                className={cx(
                  "max-w-[220px] truncate rounded-[3px] border px-2 py-0.5 text-[11px]",
                  model.subject.subject
                    ? "border-accent/50 bg-accent-soft/60 text-accent-strong"
                    : "border-line bg-panel-soft/60 text-muted",
                )}
                title={model.subject.title}
              >
                {model.subject.label}
              </span>
              {model.subject.clear ? (
                <button
                  type="button"
                  data-testid={model.subject.clear.testId}
                  onClick={model.subject.clear.run}
                  aria-label={model.subject.clear.label}
                  title={model.subject.clear.title ?? model.subject.clear.label}
                  className="ui-icon-button size-6"
                >
                  <AuditIcon
                    token={model.subject.clear.icon ?? "reset"}
                    className="size-3"
                  />
                </button>
              ) : null}
            </div>
          </div>

          <div
            ref={scrollRef}
            className="thin-scrollbar min-h-0 flex-1 overflow-y-auto bg-panel"
          >
            {fullSections.map(renderSection)}

            <div className="grid grid-cols-1 items-stretch min-[1440px]:grid-cols-[minmax(0,1.4fr)_minmax(0,0.9fr)]">
              <div className="flex min-w-0 flex-col bg-panel">
                {leftSections.map(renderSection)}
              </div>

              <div className="flex min-w-0 flex-col border-t border-line-soft bg-panel min-[1440px]:border-t-0 min-[1440px]:border-l min-[1440px]:border-line">
                {rightSections.map(renderSection)}
              </div>
            </div>

            {tailSections.map(renderSection)}

            <p className="border-t border-line-soft bg-panel px-3 py-2 text-center font-mono text-[10.5px] leading-relaxed text-faint">
              {model.footer}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
