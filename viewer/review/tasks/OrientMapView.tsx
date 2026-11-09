"use client";

import { TopologyView } from "@/topology/view/TopologyView";
import type { OrientTaskModel } from "@/review/model/buildAppModel";

interface OrientMapViewProps {
  model: OrientTaskModel;
}

/**
 * Orientation task: the topology model at full width. The map panel owns its
 * Navigator, so the task adds no Outliner or Properties panel.
 */
export function OrientMapView({ model }: OrientMapViewProps) {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
      <TopologyView model={model.topology} />
    </div>
  );
}
