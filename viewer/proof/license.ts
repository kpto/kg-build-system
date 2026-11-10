import type { AssetLicense, ViewerIndex } from "@/lib/types";
import type { ProofModel } from "./model";
import { provenanceReferences } from "./references";

export interface EffectiveLicense {
  value: string;
  licenses: string[];
  source: "declared" | "mixed" | "unknown";
}

function licenseLabel(value: AssetLicense | string | null | undefined): string | undefined {
  if (typeof value === "string") return value.trim() || undefined;
  if (!value || typeof value !== "object") return undefined;
  const identifier =
    typeof value.identifier === "string" ? value.identifier.trim() : "";
  const attribution =
    typeof value.attribution === "string" ? value.attribution.trim() : "";
  if (!identifier) return undefined;
  return attribution ? `${identifier} · ${attribution}` : identifier;
}

/** The licence declared by the assets that back a set of provenance references. */
export function effectiveLicense(
  index: ViewerIndex,
  assetNames: Iterable<string>,
): EffectiveLicense {
  const licenses = [
    ...new Set(
      [...assetNames]
        .map((name) => licenseLabel(index.assetsByName.get(name)?.governance?.license))
        .filter((license): license is string => Boolean(license)),
    ),
  ].sort((left, right) => left.localeCompare(right));

  if (!licenses.length) {
    return { value: "Not declared", licenses, source: "unknown" };
  }
  if (licenses.length === 1) {
    return { value: licenses[0], licenses, source: "declared" };
  }
  return {
    value: `Mixed · ${licenses.join(" · ")}`,
    licenses,
    source: "mixed",
  };
}

/** The effective licence for a node, edge or property document. */
export function effectiveLicenseForModel(
  index: ViewerIndex,
  model: ProofModel,
): EffectiveLicense {
  return effectiveLicense(
    index,
    provenanceReferences(index, model).assets.map((reference) => reference.name),
  );
}

/** The effective licence for the whole graph. */
export function effectiveLicenseForGraph(index: ViewerIndex): EffectiveLicense {
  return effectiveLicense(index, index.assets.map((asset) => asset.name));
}
