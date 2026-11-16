import { describe, expect, it } from "vitest";

import {
  componentMeaning,
  graphMeaning,
  meaningCount,
  meaningLimitations,
  propertyMeaning,
} from "../shared/design/meaning";
import { contractIndex } from "./fixtures";

describe("design meaning", () => {
  it("reads the graph purpose, limitations and claims", () => {
    const meaning = graphMeaning(contractIndex);
    expect(meaning.purpose).toBe(
      "Exercise the viewer data contract without loading a release.",
    );
    expect(meaning.claims.map((claim) => claim.text)).toContain(
      "The fixture graph contains one observed estate.",
    );
    expect(meaning.limitations).toHaveLength(2);
    expect(meaningCount(meaning)).toBe(4);
    expect(meaningLimitations(meaning)).toHaveLength(2);
  });

  it("reads the meaning attached to a component", () => {
    const meaning = componentMeaning(contractIndex, "node", "defect");
    expect(meaning.claims.map((claim) => claim.text)).toEqual([
      "A defect is observed on an estate survey.",
    ]);
    expect(meaning.limitations).toHaveLength(0);
  });

  it("reads the meaning attached to one property", () => {
    const meaning = propertyMeaning(contractIndex, "node", "defect", "title");
    expect(meaning.claims.map((claim) => claim.text)).toEqual([
      "The title is the defect's display name.",
    ]);
  });

  it("returns empty meaning for a subject without meaning", () => {
    expect(componentMeaning(contractIndex, "node", "missing").claims).toEqual([]);
    expect(componentMeaning(contractIndex, "node", "missing").limitations).toEqual(
      [],
    );
  });
});
