/**
 * Memoised access to the topology model for the mounted function.
 *
 * The shell keeps `snapshot`, `index` and `review` stable. Three panels ask for
 * the same model, so one cache entry per index prevents three audit/decision
 * passes and keeps the graph key stable while selection changes.
 */

import type { ReviewSidecar } from "@/lib/reviewTypes";
import type { ViewerIndex, ViewerSnapshot } from "@/lib/types";
import type { TopologyGraphModel } from "./TopologyGraphModel";
import { buildTopologyModel } from "./buildTopologyModel";

interface CacheEntry {
  snapshot: ViewerSnapshot;
  review: ReviewSidecar | undefined;
  model: TopologyGraphModel;
}

const cache = new WeakMap<ViewerIndex, CacheEntry>();

export function topologyModelFor(
  snapshot: ViewerSnapshot,
  index: ViewerIndex,
  review: ReviewSidecar | undefined,
): TopologyGraphModel {
  const existing = cache.get(index);
  if (
    existing &&
    existing.snapshot === snapshot &&
    existing.review === review
  ) {
    return existing.model;
  }
  const model = buildTopologyModel(snapshot, index, { review });
  cache.set(index, { snapshot, review, model });
  return model;
}
