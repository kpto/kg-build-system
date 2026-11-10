import { useSyncExternalStore } from "react";

import {
  DEFAULT_WORKFLOW_FILTERS,
  type WorkflowFilters,
} from "@/workflow/model/WorkflowViewModel";

export interface WorkflowUiState {
  filters: WorkflowFilters;
  selectedStepKey?: string;
}

const defaultState = (): WorkflowUiState => ({
  filters: { ...DEFAULT_WORKFLOW_FILTERS },
});

class WorkflowUiStore {
  private state: WorkflowUiState = defaultState();
  private readonly listeners = new Set<() => void>();

  getState = (): WorkflowUiState => this.state;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  private emit(next: WorkflowUiState): void {
    this.state = next;
    for (const listener of this.listeners) listener();
  }

  private patch(patch: Partial<WorkflowUiState>): void {
    this.emit({ ...this.state, ...patch });
  }

  setQuery = (query: string): void => {
    this.patch({ filters: { ...this.state.filters, query } });
  };

  setComponent = (component: string): void => {
    this.patch({ filters: { ...this.state.filters, component } });
  };

  setKind = (kind: string): void => {
    this.patch({ filters: { ...this.state.filters, kind } });
  };

  resetFilters = (): void => {
    this.patch({ filters: { ...DEFAULT_WORKFLOW_FILTERS } });
  };

  selectStep = (key: string | undefined): void => {
    this.patch({ selectedStepKey: key });
  };
}

const stores = new Map<string, WorkflowUiStore>();

export function getWorkflowUiStore(snapshotName: string): WorkflowUiStore {
  let store = stores.get(snapshotName);
  if (!store) {
    store = new WorkflowUiStore();
    stores.set(snapshotName, store);
  }
  return store;
}

export function useWorkflowUi(snapshotName: string): {
  state: WorkflowUiState;
  store: WorkflowUiStore;
} {
  const store = getWorkflowUiStore(snapshotName);
  const state = useSyncExternalStore(
    store.subscribe,
    store.getState,
    store.getState,
  );
  return { state, store };
}
