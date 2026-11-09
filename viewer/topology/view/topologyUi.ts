/**
 * Shared view state for the topology function.
 *
 * The workbench shell owns selection and panel layout; the sidebar, editor and
 * bottom panel are mounted separately. Filters, detail switches, the pin switch,
 * saved positions and the fit/reset/zoom requests therefore live in one small
 * per-snapshot store instead of in any one panel.
 *
 * Only view state lives here. The graph model comes from `buildTopologyModel`;
 * no simulation or DOM object is stored.
 */

import type {
  TopologyDetailOptions,
  TopologyFilters,
} from "@/topology/model/TopologyGraphModel";
import {
  cloneTopologyDetail,
  cloneTopologyFilters,
  createTopologyDetail,
  createTopologyFilters,
} from "@/topology/model/TopologyGraphModel";

export interface TopologyPosition {
  x: number;
  y: number;
}

export interface TopologyUiState {
  filters: TopologyFilters;
  detail: TopologyDetailOptions;
  pinned: boolean;
  positions: Record<string, TopologyPosition>;
  fitToken: number;
  resetToken: number;
  zoomToken: number;
  zoomFactor: number;
  hydrated: boolean;
}

interface PersistedTopologyUi {
  filters?: Partial<TopologyFilters> & {
    kinds?: Partial<TopologyFilters["kinds"]>;
  };
  detail?: Partial<TopologyDetailOptions>;
  pinned?: boolean;
  positions?: Record<string, TopologyPosition>;
}

const STORAGE_PREFIX = "kg-viewer:topology:";

function defaultState(): TopologyUiState {
  return {
    filters: createTopologyFilters(),
    detail: createTopologyDetail(),
    pinned: false,
    positions: {},
    fitToken: 0,
    resetToken: 0,
    zoomToken: 0,
    zoomFactor: 1,
    hydrated: false,
  };
}

function sanitizePersisted(value: unknown): PersistedTopologyUi | undefined {
  if (!value || typeof value !== "object") return undefined;
  return value as PersistedTopologyUi;
}

function sanitizePositions(
  value: unknown,
): Record<string, TopologyPosition> {
  if (!value || typeof value !== "object") return {};
  const positions: Record<string, TopologyPosition> = {};
  for (const [key, raw] of Object.entries(value)) {
    if (!raw || typeof raw !== "object") continue;
    const candidate = raw as { x?: unknown; y?: unknown };
    if (typeof candidate.x !== "number" || typeof candidate.y !== "number") {
      continue;
    }
    if (!Number.isFinite(candidate.x) || !Number.isFinite(candidate.y)) continue;
    positions[key] = { x: candidate.x, y: candidate.y };
  }
  return positions;
}

function filtersFrom(
  persisted: PersistedTopologyUi["filters"],
  defaults: TopologyFilters,
): TopologyFilters {
  if (!persisted) return defaults;
  const abstract =
    persisted.abstract === "concrete" || persisted.abstract === "abstract"
      ? persisted.abstract
      : defaults.abstract;
  const semantics =
    persisted.semantics === "present" || persisted.semantics === "missing"
      ? persisted.semantics
      : defaults.semantics;
  return {
    kinds: {
      node: persisted.kinds?.node ?? defaults.kinds.node,
      edge: persisted.kinds?.edge ?? defaults.kinds.edge,
    },
    abstract,
    semantics,
  };
}

function detailFrom(
  persisted: PersistedTopologyUi["detail"],
  defaults: TopologyDetailOptions,
): TopologyDetailOptions {
  if (!persisted) return defaults;
  const labels =
    persisted.labels === "off" || persisted.labels === "all"
      ? persisted.labels
      : defaults.labels;
  return {
    labels,
    edgeLabels: persisted.edgeLabels ?? defaults.edgeLabels,
    containment: persisted.containment ?? defaults.containment,
    semantics: persisted.semantics ?? defaults.semantics,
    properties: persisted.properties ?? defaults.properties,
    edges: persisted.edges === "off" ? "off" : defaults.edges,
  };
}

export class TopologyUiStore {
  private state: TopologyUiState = defaultState();
  private readonly listeners = new Set<() => void>();
  private readonly storageKey: string;

  constructor(snapshotName: string) {
    this.storageKey = `${STORAGE_PREFIX}${snapshotName}`;
  }

  getState = (): TopologyUiState => this.state;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  private emit(next: TopologyUiState): void {
    this.state = next;
    for (const listener of this.listeners) listener();
  }

  private patch(patch: Partial<TopologyUiState>): void {
    this.emit({ ...this.state, ...patch });
    this.persist();
  }

  private persist(): void {
    if (typeof window === "undefined") return;
    try {
      const body: PersistedTopologyUi = {
        filters: this.state.filters,
        detail: this.state.detail,
        pinned: this.state.pinned,
        positions: this.state.positions,
      };
      window.localStorage.setItem(this.storageKey, JSON.stringify(body));
    } catch {
      // Storage can be unavailable (private mode, quota). The model and view
      // still work; only cross-refresh persistence is lost.
    }
  }

  /** Read persisted state once, after mount. */
  hydrate = (): void => {
    if (this.state.hydrated || typeof window === "undefined") return;
    let persisted: PersistedTopologyUi | undefined;
    try {
      const raw = window.localStorage.getItem(this.storageKey);
      if (raw) persisted = sanitizePersisted(JSON.parse(raw));
    } catch {
      persisted = undefined;
    }
    this.emit({
      ...this.state,
      filters: filtersFrom(persisted?.filters, createTopologyFilters()),
      detail: detailFrom(persisted?.detail, createTopologyDetail()),
      pinned: Boolean(persisted?.pinned),
      positions: sanitizePositions(persisted?.positions),
      hydrated: true,
    });
  };

  setFilters = (filters: TopologyFilters): void => {
    this.patch({ filters: cloneTopologyFilters(filters) });
  };

  setDetail = (detail: TopologyDetailOptions): void => {
    this.patch({ detail: cloneTopologyDetail(detail) });
  };

  setPinned = (pinned: boolean): void => {
    this.patch({ pinned });
  };

  setPosition = (id: string, position: TopologyPosition): void => {
    this.patch({
      positions: { ...this.state.positions, [id]: { ...position } },
    });
  };

  setPositions = (positions: Record<string, TopologyPosition>): void => {
    this.patch({ positions: { ...positions } });
  };

  clearPositions = (): void => {
    this.patch({ positions: {} });
  };

  requestFit = (): void => {
    this.emit({ ...this.state, fitToken: this.state.fitToken + 1 });
  };

  requestReset = (): void => {
    this.emit({
      ...this.state,
      filters: createTopologyFilters(),
      detail: createTopologyDetail(),
      pinned: false,
      positions: {},
      fitToken: this.state.fitToken + 1,
      resetToken: this.state.resetToken + 1,
      hydrated: true,
    });
    this.persist();
  };

  requestZoom = (factor: number): void => {
    this.emit({
      ...this.state,
      zoomToken: this.state.zoomToken + 1,
      zoomFactor: factor,
    });
  };
}

const stores = new Map<string, TopologyUiStore>();

export function getTopologyUiStore(snapshotName: string): TopologyUiStore {
  let store = stores.get(snapshotName);
  if (!store) {
    store = new TopologyUiStore(snapshotName);
    stores.set(snapshotName, store);
  }
  return store;
}
