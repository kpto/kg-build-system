/**
 * View types for the plan canvas.
 *
 * The wire shape lives in `src/lib/types.ts`; a real compiled plan carries a few
 * fields the mirror does not model yet (`order`, `relation`, `action`,
 * `payload_keys` on a step, `role` on a connection, and the `table`/`publish`/
 * `step` kinds), so the feature reads them through these widened types rather
 * than editing the shared mirror. Every field stays optional: a half-built backend
 * payload must still render.
 */

import type { Plan, PlanEdge, PlanModule, PlanNode, PlanNodeKind, PlanSlot } from "@/lib/types";

/** Kinds a real plan emits that `PlanNodeKind` does not list yet. */
export type StepKind = PlanNodeKind | "table" | "publish" | "step";

/** A plan step plus the payload fields the compiled contract actually carries. */
export interface StepNode extends Omit<PlanNode, "kind"> {
  readonly kind: StepKind;
  /** Declaration order in the contract; the tie-break that keeps layout stable. */
  readonly order?: number;
  /** The DuckDB relation the step materialises (`kg_binding_3`, `kg_graph_site`). */
  readonly relation?: string | null;
  /** The core action the step lowers to (`source_relation`, `aggregate`, …). */
  readonly action?: string | null;
  /** Names of the step payload keys, without their values. */
  readonly payload_keys?: readonly string[];
  /** Forward-compatible full payload, should the projection start sending it. */
  readonly payload?: Record<string, unknown> | null;
}

/** A plan connection; `role` is the producing output slot's artifact role. */
export interface StepEdge extends PlanEdge {
  readonly role?: string | null;
}

/** A plan widened the same way, so `GET /api/plan` can be read directly. */
export interface StepPlan extends Omit<Plan, "nodes" | "edges"> {
  readonly modules?: readonly PlanModule[];
  readonly nodes?: readonly StepNode[];
  readonly edges?: readonly StepEdge[];
}

/** One socket: a slot with the label the canvas shows next to the handle. */
export interface Socket {
  /** Handle id; slot ids are already step-qualified and unique. */
  readonly id: string;
  readonly slotId: string;
  /** Role name shown beside the handle (`table.sites`, `bindings`). */
  readonly label: string;
  /** Full artifact role for output sockets, `null` for inputs. */
  readonly role: string | null;
  readonly ref: string | null;
}

/** A fact line rendered in a node body; `null` fields are simply not shown. */
export interface NodeFact {
  readonly text: string;
  readonly tone?: "neutral" | "relation" | "template" | "info" | "warn";
  readonly title?: string;
}

/** Everything the node body shows that is derived from the step payload. */
export interface StepDetail {
  readonly kindLabel: string;
  /** `what it does`, one short line (operator meaning, aggregate semantics…). */
  readonly summary: string | null;
  readonly facts: readonly NodeFact[];
  /** Chips: `UNION ALL`, `materialized`, `→ graph.jsonl`, build keys… */
  readonly badges: readonly NodeFact[];
  readonly hasSql: boolean;
  readonly relation: string | null;
  readonly location: string | null;
  readonly target: string | null;
}

/** One socket group, as the compositor body renders it. */
export interface SocketGroup {
  readonly inputs: readonly Socket[];
  readonly outputs: readonly Socket[];
}

export type ModuleRole = "core" | "operator" | "target";

/** A lane: one module drawn as a horizontal band, spanning its own layer range. */
export interface Lane {
  readonly moduleId: string;
  readonly label: string;
  readonly role: ModuleRole;
  /** Left edge of the band — the grid offset of the module's shallowest layer. */
  readonly x: number;
  /** Top edge of the band; lanes stack downwards in `groupLanes` order. */
  readonly y: number;
  readonly width: number;
  readonly height: number;
  readonly stepCount: number;
}

/** A step placed by `layout.ts`, in canvas coordinates. */
export interface PlacedStep {
  readonly id: string;
  /** Global evaluation depth — comparable across every lane. */
  readonly x: number;
  /** Position within the lane's band. */
  readonly y: number;
  readonly width: number;
  readonly height: number;
  readonly lane: string;
  readonly layer: number;
  readonly column: number;
}

export interface LayoutSpacing {
  /** Gap between two global columns. */
  readonly columnGap: number;
  /** Gap between two stacked lane bands. */
  readonly laneGap: number;
  /** Vertical gap between two steps in one lane and column. */
  readonly rowGap: number;
}

export interface PlanLayout {
  readonly placed: readonly PlacedStep[];
  readonly lanes: readonly Lane[];
  readonly width: number;
  readonly height: number;
  readonly layers: ReadonlyMap<string, number>;
  readonly crossings: number;
  /** Connections dropped to break an unexpected cycle; empty for a sane DAG. */
  readonly cycleBroken: readonly string[];
}

/** The filters the strip owns; predicates live in `filters.ts`. */
export interface PlanFilters {
  readonly modules: readonly string[];
  readonly kinds: readonly StepKind[];
  readonly query: string;
  readonly onlySelected: boolean;
}

export interface PlanCounts {
  readonly steps: number;
  readonly connections: number;
  readonly materialised: number;
  readonly withSql: number;
  readonly components: number;
}

export type { PlanModule, PlanNode, PlanNodeKind, PlanSlot, Plan };
