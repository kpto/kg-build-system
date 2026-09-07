"use client";

import { useMemo } from "react";
import clsx from "clsx";

import {
  Chip,
  CloseIcon,
  CopyButton,
  EmptyState,
  RowButton,
  SeverityMark,
  VirtualList,
} from "@/components/ui";
import { refLabel } from "@/lib/ids";
import { PROBLEM_TIERS, TIER_LABEL, type Problem, type ProblemTier } from "@/lib/types";
import { areaForProblem, useProblemStore } from "@/stores/problemStore";
import { useSelectionStore } from "@/stores/selectionStore";

const ROW_HEIGHT = 26;

export interface ProblemsPanelProps {
  open: boolean;
  onToggle(): void;
  onClose(): void;
}

/**
 * The bottom problems panel: every tier in one list, filterable by tier.
 *
 * Rows are a fixed height and windowed, because pyright can report hundreds of
 * diagnostics across a generated project. A problem with no `ref` is still listed —
 * it just says so, rather than pretending to belong to a component.
 */
export function ProblemsPanel({ open, onToggle, onClose }: ProblemsPanelProps) {
  const problems = useProblemStore((state) => state.problems);
  const counts = useProblemStore((state) => state.counts);
  const activeTiers = useProblemStore((state) => state.activeTiers);
  const toggleTier = useProblemStore((state) => state.toggleTier);
  const pyright = useProblemStore((state) => state.pyright);
  const selectedRef = useSelectionStore((state) => state.selectedRef);
  const selectAndReveal = useSelectionStore((state) => state.selectAndReveal);

  const visible = useMemo(
    () => problems.filter((problem) => activeTiers.includes(problem.tier)),
    [problems, activeTiers],
  );

  const tierCount = (tier: ProblemTier): number =>
    problems.reduce((total, problem) => total + (problem.tier === tier ? 1 : 0), 0);

  const jump = (problem: Problem) => {
    if (problem.ref) selectAndReveal(problem.ref);
    else {
      // No ref: keep the current selection but still move to the tier's area when known.
      const area = areaForProblem(problem);
      if (area) useSelectionStore.getState().setArea(area);
    }
  };

  return (
    <section
      aria-label="Problems"
      className={clsx(
        "flex shrink-0 flex-col border-t border-edge bg-surface transition-[height]",
        open ? "h-56" : "h-8",
      )}
    >
      <header className="flex h-8 shrink-0 items-center gap-2 border-b border-edge px-2.5">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted hover:text-ink"
        >
          <Chevron open={open} />
          Problems
        </button>
        <span className="font-mono text-[11px] text-faint">
          <span className="text-danger">{counts.errors}</span>
          {" · "}
          <span className="text-warn">{counts.warnings}</span>
          {" · "}
          <span className="text-info">{counts.infos}</span>
        </span>

        <div className="ml-2 flex items-center gap-1" role="group" aria-label="Filter by tier">
          {PROBLEM_TIERS.map((tier) => (
            <Chip
              key={tier}
              plain
              active={activeTiers.includes(tier)}
              onClick={() => toggleTier(tier)}
              title={`Toggle the ${TIER_LABEL[tier]} tier`}
            >
              {TIER_LABEL[tier]} {tierCount(tier)}
            </Chip>
          ))}
        </div>

        {pyright?.state && pyright.state !== "ready" && (
          <span className="font-mono text-[11px] text-warn">pyright: {pyright.state}</span>
        )}
        {open && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close problems panel"
            className="ml-auto rounded p-1 text-muted hover:bg-raised hover:text-ink"
          >
            <CloseIcon />
          </button>
        )}
      </header>

      {open && (
        <div className="flex min-h-0 flex-1 flex-col">
          <VirtualList
            items={visible}
            rowHeight={ROW_HEIGHT}
            ariaLabel={`${visible.length} problems`}
            keyOf={(problem, index) => `${problem.id}-${index}`}
            empty={
              problems.length === 0 ? (
                <EmptyState
                  title="No problems reported"
                  body={
                    pyright?.state === "starting"
                      ? "Pyright is still warming up."
                      : "Nothing from pyright, blueprint validation or the last build."
                  }
                />
              ) : (
                <EmptyState title="All problems filtered out" body="Enable a tier above." />
              )
            }
            renderItem={(problem) => (
              <ProblemRow
                problem={problem}
                active={Boolean(problem.ref) && problem.ref === selectedRef}
                onJump={jump}
              />
            )}
          />
        </div>
      )}
    </section>
  );
}

/**
 * One diagnostic. `RowButton` rather than a `<button>` so the message can be
 * drag-selected and copied out; the row still jumps on click, Enter and Space.
 */
function ProblemRow({
  problem,
  active,
  onJump,
}: {
  problem: Problem;
  active: boolean;
  onJump(problem: Problem): void;
}) {
  const location = problem.file
    ? `${problem.file.split("/").pop()}${problem.line ? `:${problem.line}` : ""}`
    : null;
  return (
    <div
      className={clsx(
        "flex h-full w-full items-stretch border-b border-edge/50",
        active && "bg-raised",
      )}
    >
      <RowButton
        onActivate={() => onJump(problem)}
        active={active}
        className={clsx(
          "flex min-w-0 flex-1 items-center gap-2 px-2.5 text-left",
          "hover:bg-raised",
        )}
        title={problem.hint ? problem.hint : problem.message}
      >
        <SeverityMark severity={problem.severity} />
        <span className="w-[4.5rem] shrink-0 truncate font-mono text-[10px] uppercase text-faint">
          {TIER_LABEL[problem.tier] ?? problem.tier}
        </span>
        <span className="min-w-0 flex-1 truncate text-[12px] text-ink">{problem.message}</span>
        {problem.code && (
          <span className="hidden shrink-0 font-mono text-[10px] text-faint lg:inline">
            {problem.code}
          </span>
        )}
        <span className="shrink-0 font-mono text-[10px] text-muted">{location ?? "no file"}</span>
        <span
          className={clsx(
            "w-40 shrink-0 truncate text-right font-mono text-[10px]",
            problem.ref ? "text-info" : "text-faint italic",
          )}
        >
          {problem.ref ? `${refLabel(problem.ref)}${problem.ref_trusted === "name" ? " ≈" : ""}` : "no ref"}
        </span>
      </RowButton>
      <CopyButton text={problem.message} title="Copy the full message" />
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={12}
      height={12}
      aria-hidden
      className={clsx("transition-transform", open ? "rotate-90" : "")}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
    >
      <path d="m9 5 7 7-7 7" />
    </svg>
  );
}
