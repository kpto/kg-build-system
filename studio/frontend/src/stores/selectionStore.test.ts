import { beforeEach, describe, expect, it } from "vitest";

import { areaForRef, useSelectionStore } from "./selectionStore";

beforeEach(() => {
  // The store is a module-level singleton; without this each test inherits the last
  // one's selection and intent.
  useSelectionStore.getState().reset();
});

const store = () => useSelectionStore.getState();

describe("cross-area intent", () => {
  it("hands the owning area the intent it asked for, once", () => {
    store().requestIntent("bindings", "new-binding", { source: "site_cities", field: "site_id" });

    const intent = store().takeIntent("bindings");
    expect(intent?.kind).toBe("new-binding");
    expect(intent?.seed).toEqual({ source: "site_cities", field: "site_id" });

    // Taken is spent: a second read must not re-open the composer on the next render.
    expect(store().takeIntent("bindings")).toBeNull();
    expect(store().pendingIntent).toBeNull();
  });

  it("leaves an intent for another area untouched and answers nothing to the passer-by", () => {
    store().requestIntent("bindings", "new-binding", { source: "site_cities" });

    expect(store().takeIntent("contracts")).toBeNull();
    expect(store().pendingIntent?.area).toBe("bindings");
    expect(store().takeIntent("bindings")?.seed).toEqual({ source: "site_cities" });
  });

  it("carries an empty seed when the caller knows nothing yet", () => {
    store().requestIntent("bindings", "new-binding");
    expect(store().takeIntent("bindings")?.seed).toEqual({});
  });

  it("replaces the pending intent, since only one flow can be requested at a time", () => {
    store().requestIntent("bindings", "new-binding", { source: "sites" });
    store().requestIntent("bindings", "new-binding", { source: "equipment" });

    expect(store().takeIntent("bindings")?.seed).toEqual({ source: "equipment" });
    expect(store().pendingIntent).toBeNull();
  });
});

describe("selection and reveal", () => {
  it("routes a ref to the area that owns it and asks that area to reveal it", () => {
    const before = store().revealToken;

    expect(store().selectAndReveal("binding:site_binding.property.city")).toBe("bindings");
    expect(store().area).toBe("bindings");
    expect(store().selectedRef).toBe("binding:site_binding.property.city");
    expect(store().revealToken).toBe(before + 1);

    expect(store().selectAndReveal("table:sites")).toBe("contracts");
    expect(store().area).toBe("contracts");
    expect(store().revealToken).toBe(before + 2);
  });

  it("keeps the current area and clears the selection for a ref nobody owns", () => {
    store().setArea("modules");

    expect(store().selectAndReveal("nonsense")).toBeNull();
    expect(store().area).toBe("modules");
    expect(store().selectedRef).toBeNull();
    expect(areaForRef("nonsense")).toBeNull();
  });

  it("keeps a part-level ref addressable instead of collapsing onto its entity", () => {
    store().select("table:sites.field.site_id");
    expect(store().selectedRef).toBe("table:sites.field.site_id");

    store().select("not a ref");
    expect(store().selectedRef).toBeNull();
  });

  it("keeps each tab's local selection out of the other tabs", () => {
    store().setLocalSelection("bindings", "binding:site_binding.build_key");
    expect(store().localSelection("bindings")).toBe("binding:site_binding.build_key");
    expect(store().localSelection("sources")).toBeNull();
  });
});

describe("reset", () => {
  it("clears the pending intent along with the selection", () => {
    store().select("binding:site_binding");
    store().setArea("bindings");
    store().setLocalSelection("bindings", "binding:site_binding.build_key");
    store().requestIntent("bindings", "new-binding", { source: "site_cities" });

    store().reset();

    const state = store();
    expect(state.selectedRef).toBeNull();
    expect(state.area).toBe("topology");
    expect(state.local).toEqual({});
    expect(state.pendingIntent).toBeNull();
    expect(state.takeIntent("bindings")).toBeNull();
  });
});
