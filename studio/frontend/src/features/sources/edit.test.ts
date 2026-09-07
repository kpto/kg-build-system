import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import { sectionItems, type ProjectDocument } from "@/lib/ir";
import { setPutTransport, useDocumentStore } from "@/stores/documentStore";
import { referrersForDeletion } from "@/features/contracts/logic";

import { removeSourceCascade } from "./edit";

/**
 * The delete itself: what the document looks like afterwards, what it refuses to
 * touch, and the undo the store gives an ordinary edit for free.
 */

const ids = (document: ProjectDocument, section: "sources" | "tables" | "bindings" | "projections") =>
  sectionItems(document, section).map((item) => item.id);

/** A source's canvas position, i.e. the one stored thing keyed by `source:<id>`. */
const withView = (document: ProjectDocument): ProjectDocument => ({
  ...document,
  views: {
    ...document.views,
    topology: { ...(document.views?.topology ?? {}), "source:sites_source": { x: 40, y: 90 } },
  },
});

describe("removeSourceCascade", () => {
  it("removes exactly the named source", () => {
    const next = removeSourceCascade(SAMPLE_DOCUMENT, "readings_source");

    expect(ids(next, "sources")).toEqual(["sites_source", "equipment_source"]);
    // The expected document, stated in full: this and nothing else.
    expect(next).toEqual({
      ...SAMPLE_DOCUMENT,
      sources: (SAMPLE_DOCUMENT.sources ?? []).filter((item) => item.id !== "readings_source"),
    });
  });

  it("changes nothing else in the document", () => {
    const next = removeSourceCascade(SAMPLE_DOCUMENT, "sites_source");

    // The table the source fed stays declared, with its columns; so do the stacks that
    // read it. Deleting the feed is not the same as deleting the shape, and the user
    // never asked for either.
    expect(next.tables).toBe(SAMPLE_DOCUMENT.tables);
    expect(next.bindings).toBe(SAMPLE_DOCUMENT.bindings);
    expect(next.projections).toBe(SAMPLE_DOCUMENT.projections);
    expect(next.structs).toBe(SAMPLE_DOCUMENT.structs);
    expect(next.components).toBe(SAMPLE_DOCUMENT.components);
    expect(next.project).toBe(SAMPLE_DOCUMENT.project);
    expect(next.revision).toBe(SAMPLE_DOCUMENT.revision);
    expect(ids(next, "tables")).toContain("sites");
  });

  it("clears the deleted source's stored canvas position and nobody else's", () => {
    const document = withView(SAMPLE_DOCUMENT);

    const next = removeSourceCascade(document, "sites_source");

    // The canvas position is keyed by the source's own ref, so it is the one reference
    // that would outlive the declaration.
    expect(next.views?.topology?.["source:sites_source"]).toBeUndefined();
    expect(next.views?.topology).toEqual({ "component:site": { x: 120, y: 80 } });
  });

  it("leaves an absent source's document alone rather than rebuilding it", () => {
    const next = removeSourceCascade(SAMPLE_DOCUMENT, "gone_source");

    expect(next.sources).toEqual(SAMPLE_DOCUMENT.sources);
    expect(next).not.toBe(SAMPLE_DOCUMENT);
  });
});

describe("deleting a source, blocked or allowed", () => {
  it("refuses while a stack still reads a table the source fed", () => {
    const referrers = referrersForDeletion(SAMPLE_DOCUMENT, "source", "sites_source");

    expect(referrers.length).toBeGreaterThan(0);
    // The guard is the caller's, and the cascade never repairs around it: had this run,
    // `site_binding` would read a table with no data behind it.
    expect(referrers.map((item) => item.ref)).toContain("binding:site_binding.build_key");
  });
});

describe("undo", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // The store PUTs on a timer; nothing here is about the write path.
    setPutTransport(() => Promise.resolve({ revision: 1, document: SAMPLE_DOCUMENT }));
    useDocumentStore.getState().reset(SAMPLE_DOCUMENT);
  });

  afterEach(() => {
    useDocumentStore.getState().reset();
    setPutTransport(null);
    vi.useRealTimers();
  });

  it("steps a deleted source back as an ordinary document edit", () => {
    const store = () => useDocumentStore.getState();

    store().apply((draft) => removeSourceCascade(draft, "readings_source"));
    expect(ids(store().document as ProjectDocument, "sources")).toEqual(["sites_source", "equipment_source"]);

    store().undo();
    expect(store().document).toEqual(SAMPLE_DOCUMENT);

    store().redo();
    expect(ids(store().document as ProjectDocument, "sources")).toEqual(["sites_source", "equipment_source"]);
  });
});
