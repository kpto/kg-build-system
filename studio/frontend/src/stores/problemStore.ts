import { create } from "zustand";

import { entityRef, parseRef } from "@/lib/ids";
import {
  AREA_FOR_REF_KIND,
  SEVERITY_RANK,
  type Problem,
  type ProblemSeverity,
  type ProblemTier,
  type TabArea,
} from "@/lib/types";

/**
 * Problem store: the one problem list every tier feeds.
 *
 * Indexed twice on arrival — by IR ref (inline badges) and by file (the problems
 * list groups by file). Building both indices in `setProblems` keeps every badge
 * lookup O(1) per ref, which matters when pyright reports across a whole project.
 */

export type TierFilter = ProblemTier;

export interface ProblemState {
  problems: Problem[];
  /** Ref → problems, keyed on both the exact ref and its whole-entity ref. */
  byRefIndex: Record<string, Problem[]>;
  byFile: Record<string, Problem[]>;
  counts: { errors: number; warnings: number; infos: number };
  /** Tier filter chips in the problems panel; all tiers on by default. */
  activeTiers: ProblemTier[];
  /** From the diagnostics payload, so the panel can say "pyright: starting". */
  pyright: { state?: string; files_open?: number } | null;

  setProblems(problems: readonly Problem[]): void;
  /**
   * Replace exactly the named tiers and keep every other tier's problems.
   *
   * A single tier's producer (the blueprint pass, a build, pyright) says nothing about
   * the others, so it must not clear them — and it must still clear its own tier when
   * the pass comes back clean, which is why the tiers are given and not inferred from
   * the payload.
   */
  setTierProblems(tiers: readonly ProblemTier[], problems: readonly Problem[]): void;
  /**
   * Replace only the tiers present in `problems`: a blueprint or build event knows
   * nothing about pyright's output, so it must not clear it.
   */
  mergeProblems(problems: readonly Problem[]): void;
  setPyright(info: { state?: string; files_open?: number } | null): void;
  toggleTier(tier: TierFilter): void;
  setTiers(tiers: readonly ProblemTier[]): void;
  reset(): void;
}

function indexByRef(problems: Problem[]): Record<string, Problem[]> {
  const map: Record<string, Problem[]> = {};
  for (const problem of problems) {
    const ref = problem.ref;
    if (!ref || !parseRef(ref)) continue;
    // A problem on `binding:x.property.y` also badges `binding:x`, so a component
    // card lights up without the UI having to re-derive the hierarchy.
    for (const key of new Set([ref, entityRef(ref) ?? ref])) {
      const bucket = map[key];
      if (bucket) bucket.push(problem);
      else map[key] = [problem];
    }
  }
  return map;
}

function indexByFile(problems: Problem[]): Record<string, Problem[]> {
  const map: Record<string, Problem[]> = {};
  for (const problem of problems) {
    const key = problem.file;
    if (!key) continue;
    const bucket = map[key];
    if (bucket) bucket.push(problem);
    else map[key] = [problem];
  }
  return map;
}

function tally(problems: Problem[]) {
  let errors = 0;
  let warnings = 0;
  let infos = 0;
  for (const problem of problems) {
    if (problem.severity === "error") errors += 1;
    else if (problem.severity === "warning") warnings += 1;
    else infos += 1;
  }
  return { errors, warnings, infos };
}

const bySeverityThenPosition = (a: Problem, b: Problem): number =>
  (SEVERITY_RANK[a.severity] ?? 2) - (SEVERITY_RANK[b.severity] ?? 2) ||
  (a.file ?? "").localeCompare(b.file ?? "") ||
  (a.line ?? 0) - (b.line ?? 0);

export const useProblemStore = create<ProblemState>((set, get) => ({
  problems: [],
  byRefIndex: {},
  byFile: {},
  counts: { errors: 0, warnings: 0, infos: 0 },
  activeTiers: ["types", "blueprint", "build", "document"],
  pyright: null,

  setProblems(problems) {
    const list = [...problems].sort(bySeverityThenPosition);
    set({
      problems: list,
      byRefIndex: indexByRef(list),
      byFile: indexByFile(list),
      counts: tally(list),
    });
  },

  setTierProblems(tiers, problems) {
    const owned = new Set<ProblemTier>(tiers);
    const kept = get().problems.filter((problem) => !owned.has(problem.tier));
    get().setProblems([...kept, ...problems]);
  },

  mergeProblems(problems) {
    const tiers = new Set(problems.map((problem) => problem.tier));
    const kept = get().problems.filter((problem) => !tiers.has(problem.tier));
    get().setProblems([...kept, ...problems]);
  },

  setPyright(info) {
    set({ pyright: info });
  },

  toggleTier(tier) {
    const current = get().activeTiers;
    set({
      activeTiers: current.includes(tier)
        ? current.filter((item) => item !== tier)
        : [...current, tier],
    });
  },

  setTiers(tiers) {
    set({ activeTiers: [...tiers] });
  },

  reset() {
    set({
      problems: [],
      byRefIndex: {},
      byFile: {},
      counts: { errors: 0, warnings: 0, infos: 0 },
      pyright: null,
    });
  },
}));

/* ---------------------------------------------------------------------- selectors */

/**
 * Every problem attached to a ref, including problems on parts inside it.
 * `byRef("component:site")` returns the whole subtree's problems, which is what a
 * badge on a component card must show.
 */
export const byRef = (ref: string | null | undefined) => (state: ProblemState): Problem[] =>
  ref ? (state.byRefIndex[ref] ?? []) : [];

/** Hook form: `const problems = useProblemsForRef(selectedRef)`. */
export function useProblemsForRef(ref: string | null | undefined): Problem[] {
  return useProblemStore((state) => (ref ? (state.byRefIndex[ref] ?? EMPTY) : EMPTY));
}

const EMPTY: Problem[] = [];

/** Problems grouped by the file they were reported against. */
export function problemsForFile(state: ProblemState, file: string | null): Problem[] {
  return file ? (state.byFile[file] ?? []) : [];
}

/** The list the problems panel shows for a given set of active tiers. */
export function visibleProblems(state: ProblemState): Problem[] {
  return state.problems.filter((problem) => state.activeTiers.includes(problem.tier));
}

/** The area a problem belongs to, so clicking it can switch tabs. */
export function areaForProblem(problem: Problem): TabArea | null {
  const parsed = parseRef(problem.ref);
  if (parsed) return AREA_FOR_REF_KIND[parsed.kind] ?? null;
  return problem.tier === "build" ? "plan" : null;
}

export function worstSeverity(problems: readonly Problem[]): ProblemSeverity | null {
  let worst: ProblemSeverity | null = null;
  let rank = Number.POSITIVE_INFINITY;
  for (const problem of problems) {
    const value = SEVERITY_RANK[problem.severity] ?? 2;
    if (value < rank) {
      rank = value;
      worst = problem.severity;
    }
  }
  return worst;
}

/** Problems relevant to one feature area, filtered the way the shell filters them. */
export function problemsForArea(state: ProblemState, area: TabArea): Problem[] {
  return state.problems.filter((problem) => areaForProblem(problem) === area);
}
