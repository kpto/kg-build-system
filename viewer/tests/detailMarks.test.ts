import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  DETAIL_MARK_BOX,
  DETAIL_SECTION_BY_TITLE,
  DETAIL_SECTION_KINDS,
  DetailMark,
  detailMarks,
  sectionForTitle,
} from "../detail/view/detailMarks";

const shape = (kind: (typeof DETAIL_SECTION_KINDS)[number]) =>
  renderToStaticMarkup(createElement("svg", null, detailMarks[kind].mark));

describe("detail section marks", () => {
  it("defines one mark for every section kind", () => {
    expect(Object.keys(detailMarks).sort()).toEqual(
      [...DETAIL_SECTION_KINDS].sort(),
    );
    for (const kind of DETAIL_SECTION_KINDS) {
      expect(detailMarks[kind].label.length).toBeGreaterThan(0);
      expect(detailMarks[kind].mark).toBeTruthy();
    }
  });

  it("gives every section a distinct label and silhouette", () => {
    const labels = DETAIL_SECTION_KINDS.map(
      (kind) => detailMarks[kind].label,
    );
    expect(new Set(labels).size).toBe(labels.length);
    const shapes = DETAIL_SECTION_KINDS.map(shape);
    expect(new Set(shapes).size).toBe(shapes.length);
  });

  it("normalises every section mark to one tight visual size", () => {
    for (const kind of DETAIL_SECTION_KINDS) {
      expect(detailMarks[kind].box).toBe(DETAIL_MARK_BOX);
      const [, , width = 24, height = 24] = DETAIL_MARK_BOX.split(" ").map(
        Number,
      );
      // The content square is square and sits inside the 24 px grid; the
      // tight viewBox excludes the empty margin that made some logos read
      // smaller than others.
      expect(width).toBeCloseTo(height);
      expect(width).toBeLessThan(21);
      expect(width).toBeGreaterThan(18);
      const boxMax = Math.max(width, height);
      const stroke = (1.6 * boxMax) / 24;
      const ratio = (boxMax - 2.4 + stroke) / boxMax;
      expect(ratio).toBeGreaterThan(0.8);
    }
  });

  it("maps every structural card title to its own section", () => {
    const kinds = Object.values(DETAIL_SECTION_BY_TITLE);
    expect(new Set(kinds).size).toBe(kinds.length);
    for (const [title, kind] of Object.entries(DETAIL_SECTION_BY_TITLE)) {
      expect(sectionForTitle(title)).toBe(kind);
      expect(detailMarks[kind]).toBeTruthy();
    }
    expect(sectionForTitle("Not a structural title")).toBe("items");
  });

  it("draws a section mark in the page header's colour", () => {
    const markup = renderToStaticMarkup(
      createElement(DetailMark, {
        kind: "connections",
        color: "var(--color-concept-node)",
      }),
    );
    expect(markup).toContain("color:var(--color-concept-node)");
    expect(markup).toContain("data-detail-mark=\"connections\"");
  });
});
