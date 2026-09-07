// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SourcesFeature from "./Feature";
import { removeSourceCascade } from "./edit";
import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import type { ProjectDocument } from "@/lib/ir";
import { useDocumentStore } from "@/stores/documentStore";
import { useProblemStore } from "@/stores/problemStore";
import { useSelectionStore } from "@/stores/selectionStore";

/**
 * The Sources tab used to have no remove control at all: every other declaration could
 * be deleted, a `bind_source` could not. These tests pin the affordance down to the
 * selected source, the shared block-on-referrers rule, and the one edit it performs.
 */

const mount = (
  selectedRef: string | null,
  over: { apply?: (mutate: (draft: ProjectDocument) => ProjectDocument) => void; onSelectRef?: (ref: string | null) => void } = {},
) => {
  const apply = over.apply ?? vi.fn();
  const onSelectRef = over.onSelectRef ?? vi.fn();
  render(
    <SourcesFeature
      document={SAMPLE_DOCUMENT}
      index={null}
      problems={[]}
      selectedRef={selectedRef}
      onSelectRef={onSelectRef}
      apply={apply}
    />,
  );
  return { apply, onSelectRef };
};

const dialog = () => screen.getByRole("dialog");

beforeEach(() => {
  // The discovered-files list is a filesystem read; mock mode answers it from fixtures.
  useDocumentStore.getState().setMock(true);
  useProblemStore.getState().reset();
  useSelectionStore.getState().reset();
});

afterEach(() => {
  cleanup();
  useDocumentStore.getState().reset();
  useSelectionStore.getState().reset();
});

describe("the delete source affordance", () => {
  it("exists only for the selected source", () => {
    mount(null);
    expect(screen.queryByRole("button", { name: "delete source" })).toBeNull();

    cleanup();
    mount("source:equipment_source");
    expect(screen.getByRole("button", { name: "delete source" })).toBeDefined();
  });

  it("refuses a source a binding still reads, and names the stack that would break", () => {
    const { apply } = mount("source:sites_source");

    fireEvent.click(screen.getByRole("button", { name: "delete source" }));

    const panel = dialog();
    expect(panel.getAttribute("aria-label")).toBe("Cannot delete — still referenced");
    // Named by id, with the table it would leave without data — the thing to go repoint.
    expect(within(panel).getByText("site_binding.build_key reads sites")).toBeDefined();
    expect(within(panel).getByText("binding:site_binding.property.name")).toBeDefined();
    expect(within(panel).getByText("site_cities.field.site_id reads sites")).toBeDefined();
    // Blocked means blocked: the document has not been touched.
    expect(apply).not.toHaveBeenCalled();
  });

  it("keeps the source when the user dismisses the block", () => {
    const { apply } = mount("source:sites_source");

    fireEvent.click(screen.getByRole("button", { name: "delete source" }));
    fireEvent.click(within(dialog()).getByRole("button", { name: "keep it" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(apply).not.toHaveBeenCalled();
  });

  it("asks once when nothing reads what the source feeds, then applies the cascade", () => {
    const apply = vi.fn();
    const onSelectRef = vi.fn();
    // `readings_source` fans out over the readings group; no expression names any of it.
    mount("source:readings_source", { apply, onSelectRef });

    fireEvent.click(screen.getByRole("button", { name: "delete source" }));
    expect(dialog().getAttribute("aria-label")).toBe("Confirm delete");
    expect(apply).not.toHaveBeenCalled();

    fireEvent.click(within(dialog()).getByRole("button", { name: "delete" }));

    expect(apply).toHaveBeenCalledTimes(1);
    const mutate = apply.mock.calls[0]?.[0] as (draft: ProjectDocument) => ProjectDocument;
    expect(mutate(SAMPLE_DOCUMENT)).toEqual(removeSourceCascade(SAMPLE_DOCUMENT, "readings_source"));
    // The deleted declaration cannot stay selected.
    expect(onSelectRef).toHaveBeenCalledWith(null);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("selects a source from its card, which is how the control becomes available", () => {
    const onSelectRef = vi.fn();
    mount(null, { onSelectRef });

    fireEvent.click(screen.getByText("equipment_source"));

    expect(onSelectRef).toHaveBeenCalledWith("source:equipment_source");
  });
});
