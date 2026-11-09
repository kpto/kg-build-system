"use client";

/**
 * The meaning function: what the graph means.
 *
 * The surface is a reading surface. It shows the graph purpose,
 * the graph frames and claims, and the semantics attached to a subject. Nothing
 * here records a decision, a status or an approval.
 *
 * Low detail is the default: the purpose is open, every list is closed, and the
 * attached subject browser renders counts and collapsed kind groups rather than
 * the full unit set.
 */

import type { JSX, ReactNode } from "react";
import { useCallback, useMemo, useState } from "react";
import { BookOpen, ChevronRight, Search } from "lucide-react";

import type { SemanticSubjectKind } from "@/lib/types";
import type { FeatureProps } from "@/workbench/types";
import {
  buildMeaningModel,
  filterMeaningSubjects,
  meaningUnitLabel,
  visibleFrameLimitations,
  type MeaningFrame,
  type MeaningModel,
  type MeaningSubjectGroup,
  type MeaningSubjectView,
} from "./MeaningModel";
import styles from "./meaning.module.css";

function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

interface MeaningView {
  model: MeaningModel;
  selected?: MeaningSubjectView;
  selectedKey?: string;
  selectSubject(subject: MeaningSubjectView): void;
}

function useMeaning(props: FeatureProps): MeaningView {
  const { index, functions } = props.state;
  const { actions, activity } = props;
  const model = useMemo(() => buildMeaningModel(index), [index]);
  const functionState = functions[activity];
  const selectedKey = functionState?.selection?.component;
  const selected = selectedKey ? model.subjectsByKey.get(selectedKey) : undefined;
  const selectSubject = useCallback(
    (subject: MeaningSubjectView) => {
      actions.setSelection(activity, {
        activity,
        name: subject.name,
        component: subject.key,
      });
    },
    [actions, activity],
  );
  return { model, selected, selectedKey, selectSubject };
}

// ---------------------------------------------------------------------------
// Shared subject browser
// ---------------------------------------------------------------------------

interface SubjectBrowserProps {
  model: MeaningModel;
  selectedKey?: string;
  onSelect(subject: MeaningSubjectView): void;
  label: string;
  /** Rows rendered per group before the view asks for a narrower search. */
  limit?: number;
}

function toggleKind(
  kind: SemanticSubjectKind,
  active: SemanticSubjectKind[],
): SemanticSubjectKind[] {
  return active.includes(kind)
    ? active.filter((value) => value !== kind)
    : [...active, kind];
}

function SubjectBrowser({
  model,
  selectedKey,
  onSelect,
  label,
  limit = 40,
}: SubjectBrowserProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [activeKinds, setActiveKinds] = useState<SemanticSubjectKind[]>([]);
  const [expanded, setExpanded] = useState<SemanticSubjectKind[]>([]);

  const groups = useMemo(
    () =>
      filterMeaningSubjects(model.groups, {
        query,
        kinds: activeKinds,
      }),
    [model.groups, query, activeKinds],
  );

  const searching = query.trim().length > 0;
  const expandAll = searching;

  const toggleGroup = (kind: SemanticSubjectKind) => {
    setExpanded((current) =>
      current.includes(kind)
        ? current.filter((value) => value !== kind)
        : [...current, kind],
    );
  };

  return (
    <div className={styles.browser} aria-label={label}>
      <label className={styles.searchField}>
        <Search aria-hidden className="size-3" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Find a subject"
          aria-label="Find a subject"
        />
      </label>

      <div className={styles.filterRail} role="group" aria-label="Subject kinds">
        {model.groups.map((group) => {
          const active = activeKinds.includes(group.kind);
          return (
            <button
              key={group.kind}
              type="button"
              className={styles.filterButton}
              aria-pressed={active}
              onClick={() => setActiveKinds(toggleKind(group.kind, activeKinds))}
            >
              {group.label}
              <span className={styles.filterCount}>{group.subjects.length}</span>
            </button>
          );
        })}
      </div>

      <div className={styles.groupList}>
        {groups.map((group) => (
          <SubjectGroup
            key={group.kind}
            group={group}
            selectedKey={selectedKey}
            onSelect={onSelect}
            open={expandAll || expanded.includes(group.kind)}
            onToggle={() => toggleGroup(group.kind)}
            limit={limit}
          />
        ))}
        {!groups.length ? (
          <p className={styles.empty}>No subject matches this search.</p>
        ) : null}
      </div>
    </div>
  );
}

interface SubjectGroupProps {
  group: MeaningSubjectGroup;
  selectedKey?: string;
  onSelect(subject: MeaningSubjectView): void;
  open: boolean;
  onToggle(): void;
  limit: number;
}

function SubjectGroup({
  group,
  selectedKey,
  onSelect,
  open,
  onToggle,
  limit,
}: SubjectGroupProps): JSX.Element {
  const rows = group.subjects.slice(0, limit);
  return (
    <section className={styles.group}>
      <button
        type="button"
        className={styles.groupHeader}
        aria-expanded={open}
        onClick={onToggle}
      >
        <ChevronRight
          aria-hidden
          className={cx(styles.groupChevron, open && styles.chevronOpen)}
        />
        <span className={styles.groupName}>{group.label}</span>
        <span className={styles.groupCount}>{group.subjects.length}</span>
      </button>
      {open ? (
        <div className={styles.subjectList}>
          {rows.map((subject) => (
            <button
              key={subject.key}
              type="button"
              className={styles.subjectRow}
              data-selected={selectedKey === subject.key ? "true" : undefined}
              title={subject.path}
              onClick={() => onSelect(subject)}
            >
              <span className={styles.subjectPath}>{subject.path}</span>
              <span className={styles.subjectMeta}>
                {meaningUnitLabel("claim", subject.counts.claims)}
                <span className={styles.metaDivider}>·</span>
                {meaningUnitLabel("frame", subject.counts.frames)}
              </span>
            </button>
          ))}
          {group.subjects.length > rows.length ? (
            <p className={styles.note}>
              Showing the first {rows.length} of {group.subjects.length}. Search
              to narrow the list.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

export function MeaningSidebar(props: FeatureProps): JSX.Element {
  const { model, selectedKey, selectSubject } = useMeaning(props);

  return (
    <div className={styles.sidebar} data-testid="meaning-sidebar">
      <section className={styles.purposeCard}>
        <p className={styles.kicker}>Graph purpose</p>
        <p className={styles.graphName}>{model.graph.name}</p>
        <p className={styles.purposeText}>
          {model.graph.purpose ?? "No purpose is attached to the graph declaration."}
        </p>
        <div className={styles.metricGrid}>
          <div className={styles.metric}>
            <span className={styles.metricValue}>{model.graph.counts.claims}</span>
            <span className={styles.metricLabel}>Claims</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricValue}>{model.graph.counts.frames}</span>
            <span className={styles.metricLabel}>Frames</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricValue}>
              {model.graph.counts.limitations}
            </span>
            <span className={styles.metricLabel}>Limits</span>
          </div>
          <div className={styles.metric}>
            <span className={styles.metricValue}>{model.subjectCount}</span>
            <span className={styles.metricLabel}>Subjects</span>
          </div>
        </div>
        <p className={styles.attachedLine}>
          {model.attached.units.toLocaleString()} attached units across{" "}
          {model.subjectCount.toLocaleString()} subjects.
        </p>
      </section>

      <section className={styles.sideSection}>
        <header className={styles.sideHeader}>
          <span>Attached semantics</span>
          <span className={styles.sideCount}>
            {model.attached.units.toLocaleString()} units
          </span>
        </header>
        <SubjectBrowser
          model={model}
          selectedKey={selectedKey}
          onSelect={selectSubject}
          label="Attached semantics subjects"
        />
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

interface FrameRowProps {
  frame: MeaningFrame;
  open: boolean;
  onToggle(): void;
}

function FrameRow({ frame, open, onToggle }: FrameRowProps): JSX.Element {
  const limitations = visibleFrameLimitations(frame, open);
  return (
    <div className={styles.frame}>
      <button
        type="button"
        className={styles.frameRow}
        aria-expanded={open}
        onClick={onToggle}
      >
        <ChevronRight
          aria-hidden
          className={cx(styles.frameChevron, open && styles.chevronOpen)}
        />
        <span className={styles.frameText}>{frame.text}</span>
        <span className={styles.frameCount}>
          {meaningUnitLabel("limitation", frame.limitations.length)}
        </span>
      </button>
      {open ? (
        limitations.length ? (
          <ul className={styles.limitationList}>
            {limitations.map((limitation, index) => (
              <li
                key={`${frame.key}:limitation:${index}`}
                className={styles.limitationRow}
              >
                <span className={styles.limitationMark} aria-hidden>
                  —
                </span>
                {limitation.text}
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.empty}>This frame carries no limitation.</p>
        )
      ) : null}
    </div>
  );
}

function Toggle({
  label,
  pressed,
  onClick,
  disabled,
}: {
  label: string;
  pressed: boolean;
  onClick(): void;
  disabled?: boolean;
}): JSX.Element {
  return (
    <button
      type="button"
      className={styles.control}
      aria-pressed={pressed}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
}

export function MeaningEditor(props: FeatureProps): JSX.Element {
  const { model, selected, selectedKey, selectSubject } = useMeaning(props);
  const [expandFrames, setExpandFrames] = useState(false);
  const [showLimitations, setShowLimitations] = useState(false);
  const [showClaims, setShowClaims] = useState(false);
  const [showSubjects, setShowSubjects] = useState(false);
  const [openFrames, setOpenFrames] = useState<string[]>([]);

  const toggleFrame = (key: string) => {
    setOpenFrames((current) =>
      current.includes(key)
        ? current.filter((value) => value !== key)
        : [...current, key],
    );
  };

  return (
    <div className={styles.editor} data-testid="meaning-editor">
      <header className={styles.editorHeader}>
        <span className={styles.titleIcon}>
          <BookOpen aria-hidden className="size-[18px]" />
        </span>
        <div className={styles.editorTitle}>
          <p className={styles.kicker}>Meaning</p>
          <h1>{model.graph.name}</h1>
          {model.graph.description ? (
            <p className={styles.description}>{model.graph.description}</p>
          ) : null}
          <p className={styles.lede}>
            What this graph is for, the statements it makes about itself, and the
            limits it records. Meaning is descriptive: it records what the
            design says, not how good it is.
          </p>
        </div>
      </header>

      <div className={styles.controlBar} role="toolbar" aria-label="Meaning detail">
        <Toggle
          label="Expand frames"
          pressed={expandFrames}
          onClick={() => setExpandFrames((value) => !value)}
          disabled={!model.graph.frames.length}
        />
        <Toggle
          label="Show limitations"
          pressed={showLimitations}
          onClick={() => {
            const next = !showLimitations;
            setShowLimitations(next);
            if (next) setExpandFrames(true);
          }}
          disabled={!model.graph.counts.limitations}
        />
        <Toggle
          label="Show claims"
          pressed={showClaims}
          onClick={() => setShowClaims((value) => !value)}
          disabled={!model.graph.claims.length}
        />
        <Toggle
          label="Show subjects"
          pressed={showSubjects}
          onClick={() => setShowSubjects((value) => !value)}
          disabled={!model.subjectCount}
        />
        <span className={styles.controlHint}>
          {model.attached.units.toLocaleString()} attached units ·{" "}
          {model.subjectCount.toLocaleString()} subjects
        </span>
      </div>

      <section className={styles.purposePanel}>
        <header className={styles.panelHeader}>
          <span className={styles.panelTitle}>Purpose</span>
          <span className={styles.panelCount}>
            {meaningUnitLabel("claim", model.graph.counts.claims)} ·{" "}
            {meaningUnitLabel("frame", model.graph.counts.frames)} ·{" "}
            {meaningUnitLabel("limitation", model.graph.counts.limitations)}
          </span>
        </header>
        <p className={styles.purposeBody}>
          {model.graph.purpose ?? "The graph declaration carries no purpose text."}
        </p>
      </section>

      {showClaims ? (
        <section className={styles.unitSection}>
          <header className={styles.sectionHeader}>
            <span className={styles.panelTitle}>Graph claims</span>
            <span className={styles.panelCount}>
              {meaningUnitLabel("claim", model.graph.claims.length)}
            </span>
          </header>
          <ul className={styles.claimList}>
            {model.graph.claims.map((claim, index) => (
              <li key={`graph:claim:${index}`} className={styles.claimRow}>
                <span className={styles.claimMark} aria-hidden>
                  ·
                </span>
                {claim.text}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {expandFrames ? (
        <section className={styles.unitSection}>
          <header className={styles.sectionHeader}>
            <span className={styles.panelTitle}>Purpose frames</span>
            <span className={styles.panelCount}>
              {meaningUnitLabel("frame", model.graph.frames.length)} ·{" "}
              {meaningUnitLabel("limitation", model.graph.counts.limitations)}
            </span>
          </header>
          <div className={styles.frameList}>
            {model.graph.frames.map((frame) => (
              <FrameRow
                key={frame.key}
                frame={frame}
                open={showLimitations || openFrames.includes(frame.key)}
                onToggle={() => toggleFrame(frame.key)}
              />
            ))}
          </div>
        </section>
      ) : null}

      {selected ? (
        <section className={styles.unitSection} data-testid="meaning-selected">
          <header className={styles.sectionHeader}>
            <span className={styles.panelTitle}>Selected subject</span>
            <span className={styles.panelCount}>
              {selected.path} · {meaningUnitLabel("claim", selected.counts.claims)} ·{" "}
              {meaningUnitLabel("frame", selected.counts.frames)} ·{" "}
              {meaningUnitLabel("limitation", selected.counts.limitations)}
            </span>
          </header>
          {selected.profile ? (
            <p className={styles.selectedProfile}>
              {selected.profile.subject} · coverage: {selected.profile.coverage} ·{" "}
              {selected.profile.authority} · {selected.profile.basis}
            </p>
          ) : null}
          <ul className={styles.claimList}>
            {selected.claims.slice(0, 8).map((claim, index) => (
              <li
                key={`${selected.key}:claim:${index}`}
                className={styles.claimRow}
              >
                <span className={styles.claimMark} aria-hidden>
                  ·
                </span>
                {claim.text}
              </li>
            ))}
            {!selected.claims.length ? (
              <li className={styles.note}>No claim is attached.</li>
            ) : null}
          </ul>
          {selected.frames.length ? (
            <div className={styles.frameList}>
              {selected.frames.map((frame) => (
                <FrameRow
                  key={frame.key}
                  frame={frame}
                  open={showLimitations || openFrames.includes(frame.key)}
                  onToggle={() => toggleFrame(frame.key)}
                />
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {showSubjects ? (
        <section className={styles.browserPanel}>
          <header className={styles.sectionHeader}>
            <span className={styles.panelTitle}>Attached semantics</span>
            <span className={styles.panelCount}>
              {model.attached.units.toLocaleString()} units ·{" "}
              {model.subjectCount.toLocaleString()} subjects
            </span>
          </header>
          <SubjectBrowser
            model={model}
            selectedKey={selectedKey}
            onSelect={selectSubject}
            label="Attached semantics"
            limit={60}
          />
        </section>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bottom panel
// ---------------------------------------------------------------------------

function DetailSection({
  title,
  children,
  count,
}: {
  title: string;
  children: ReactNode;
  count?: string;
}): JSX.Element {
  return (
    <section className={styles.detailSection}>
      <header className={styles.detailSectionHeader}>
        <span className={styles.detailSectionTitle}>{title}</span>
        {count ? <span className={styles.detailCount}>{count}</span> : null}
      </header>
      {children}
    </section>
  );
}

export function MeaningBottom(props: FeatureProps): JSX.Element {
  const { model, selected } = useMeaning(props);

  return (
    <div className={styles.bottom} data-testid="meaning-bottom">
      <header className={styles.bottomHeader}>
        <span className={styles.bottomTitle}>Subject</span>
        <span className={styles.bottomCount}>
          {selected
            ? `${meaningUnitLabel("claim", selected.counts.claims)} · ${meaningUnitLabel("frame", selected.counts.frames)} · ${meaningUnitLabel("limitation", selected.counts.limitations)}`
            : `${model.subjectCount.toLocaleString()} subjects with attached semantics`}
        </span>
      </header>

      {!selected ? (
        <div className={styles.bottomEmpty}>
          <BookOpen aria-hidden className="size-4" />
          <div>
            <p>Select a subject to read its meaning.</p>
            <p>
              The attached claims, frames and limitations appear here. The
              purpose above belongs to the graph declaration.
            </p>
          </div>
        </div>
      ) : (
        <div className={styles.bottomBody}>
          <div className={styles.detailHead}>
            <div>
              <p className={styles.kicker}>{selected.kind}</p>
              <p className={styles.selectedPath}>{selected.path}</p>
            </div>
            <div className={styles.detailTotals}>
              {meaningUnitLabel("claim", selected.counts.claims)} ·{" "}
              {meaningUnitLabel("frame", selected.counts.frames)} ·{" "}
              {meaningUnitLabel("limitation", selected.counts.limitations)}
            </div>
          </div>

          {selected.profile ? (
            <dl className={styles.profileGrid}>
              <div>
                <dt>Subject</dt>
                <dd>{selected.profile.subject}</dd>
              </div>
              <div>
                <dt>Coverage</dt>
                <dd>{selected.profile.coverage}</dd>
              </div>
              <div>
                <dt>Authority</dt>
                <dd>{selected.profile.authority}</dd>
              </div>
              <div>
                <dt>Basis</dt>
                <dd>{selected.profile.basis}</dd>
              </div>
            </dl>
          ) : null}

          <DetailSection
            title="Claims"
            count={meaningUnitLabel("claim", selected.counts.claims)}
          >
            {selected.claims.length ? (
              <ul className={styles.claimList}>
                {selected.claims.map((claim, index) => (
                  <li
                    key={`${selected.key}:claim:${index}`}
                    className={styles.claimRow}
                  >
                    <span className={styles.claimMark} aria-hidden>
                      ·
                    </span>
                    {claim.text}
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.detailEmpty}>No claim is attached.</p>
            )}
          </DetailSection>

          <DetailSection
            title="Frames and limitations"
            count={meaningUnitLabel("frame", selected.counts.frames)}
          >
            {selected.frames.length ? (
              <div className={styles.frameList}>
                {selected.frames.map((frame) => (
                  <div key={frame.key} className={styles.frame}>
                    <p className={styles.frameText}>{frame.text}</p>
                    {frame.limitations.length ? (
                      <ul className={styles.limitationList}>
                        {frame.limitations.map((limitation, index) => (
                          <li
                            key={`${frame.key}:limitation:${index}`}
                            className={styles.limitationRow}
                          >
                            <span className={styles.limitationMark} aria-hidden>
                              —
                            </span>
                            {limitation.text}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className={styles.detailEmpty}>
                        This frame carries no limitation.
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.detailEmpty}>No frame is attached.</p>
            )}
          </DetailSection>
        </div>
      )}
    </div>
  );
}
