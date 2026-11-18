/**
 * Memoised access to the topology model for the mounted function.
 *
 * The shell keeps `snapshot` and `index` stable. Three panels ask for the same
 * model, so one cache entry per index keeps the graph key stable while
 * selection, filters and detail switches change.
 */

import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";
import type { TopologyGraphModel } from "./TopologyGraphModel";
import { buildTopologyModel } from "./buildTopologyModel";

interface CacheEntry {
  snapshot: ViewerSnapshot;
  model: TopologyGraphModel;
}

const cache = new WeakMap<ViewerIndex, CacheEntry>();

export function topologyModelFor(
  snapshot: ViewerSnapshot,
  index: ViewerIndex,
): TopologyGraphModel {
  const existing = cache.get(index);
  if (existing && existing.snapshot === snapshot) {
    return existing.model;
  }
  const model = buildTopologyModel(snapshot, index);
  cache.set(index, { snapshot, model });
  return model;
}
