"use client";

/**
 * Contracts — tables, structs, table groups (the `contracts` tab) and projections (the
 * `projections` tab). Both tabs render this feature (`FEATURE_FOR_TAB`), switching on the
 * shell's current area.
 *
 * PROP CONTRACT (`FeatureProps`, see `src/lib/types.ts`):
 *   document      `document.tables` (incl. groups via `members`/`group`), `document.structs`
 *                 and `document.projections` are the rows. A field is `table:sites.field.site_id`,
 *                 a struct member `struct:premises.field.contact`, a projection output
 *                 `projection:site_cities.field.score`.
 *   index         `selectable[]` supplies the flattened paths a projection output may read
 *                 (never a hardcoded list); the editor offers only what the backend derives.
 *   problems      Pre-filtered for this area; badges hang off the addressed row or field.
 *   selectedRef / onSelectRef   The global selection; the inspector dock follows it.
 *   apply         Rebuild-and-return, optimistic, coalesced, undoable, 409-safe — the only
 *                 way this feature changes the document. It never writes an expression's
 *                 `logical_type` from a computation of its own; it reads `logical_type` off
 *                 the index and the document, and the backend re-derives on save.
 *
 * The feature owns the field table (never JSON), the nested struct drill-in, the group
 * catalogue, the data-shape importer, and the projection list/detail with its read-only
 * summary chain and single-driving-source rule.
 */

import { useEffect } from "react";

import type { FeatureProps, TabArea } from "@/lib/types";
import { useSelectionStore } from "@/stores/selectionStore";
import { ContractsView } from "./ContractsView";
import { ProjectionsView } from "./ProjectionsView";
import { registerContractInspectors } from "./inspectors";

/** The shell keeps the current area in the selection store; both tabs render this feature. */
function useCurrentArea(): TabArea {
  return useSelectionStore((state) => state.area);
}

export default function ContractsFeature(props: FeatureProps) {
  const area = useCurrentArea();

  // Inspectors live in the dock regardless of which tab is showing, so register once.
  useEffect(() => registerContractInspectors(), []);

  return area === "projections" ? <ProjectionsView {...props} /> : <ContractsView {...props} />;
}
