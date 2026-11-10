import { describe, expect, it } from "vitest";

import type { ViewerIndex } from "../lib/types";
import { effectiveLicense } from "../proof/license";

function indexWith(licenses: Record<string, string | null>): ViewerIndex {
  return {
    assetsByName: new Map(
      Object.entries(licenses).map(([name, license]) => [
        name,
        { name, governance: { license } },
      ]),
    ),
  } as unknown as ViewerIndex;
}

describe("effective licence", () => {
  it("uses the one licence declared by the provenance assets", () => {
    const index = indexWith({ open_target: "CC BY 4.0" });
    expect(effectiveLicense(index, ["open_target"])).toMatchObject({
      value: "CC BY 4.0",
      source: "declared",
    });
  });

  it("states an unknown licence when no asset declares one", () => {
    const index = indexWith({ open_target: null });
    expect(effectiveLicense(index, ["open_target"])).toMatchObject({
      value: "Not declared",
      source: "unknown",
    });
  });

  it("states every distinct licence when provenance is mixed", () => {
    const index = indexWith({
      open_target: "CC BY 4.0",
      survey: "ODbL",
    });
    expect(effectiveLicense(index, ["open_target", "survey"])).toMatchObject({
      value: "Mixed · CC BY 4.0 · ODbL",
      source: "mixed",
      licenses: ["CC BY 4.0", "ODbL"],
    });
  });
});
