import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { emptyDocument, type ProjectDocument } from "@/lib/ir";
import type { Problem } from "@/lib/types";
import { COALESCE_MS, setPutTransport, useDocumentStore } from "./documentStore";
import { useConnectionStore } from "./connectionStore";
import { useProblemStore } from "./problemStore";

const doc = (name: string, revision = 3): ProjectDocument => ({
  ...emptyDocument(name, "kg_project"),
  revision,
});

/** A fetch stub that records calls and answers with whatever the test wants. */
interface FetchCall {
  url: string;
  method: string;
  body: { revision: number; document: ProjectDocument };
}

let calls: FetchCall[] = [];
let responder: (call: FetchCall) => { status: number; json: unknown } = () => ({
  status: 200,
  json: {},
});

const transport = async (request: { revision: number; document: ProjectDocument }) => {
  const call: FetchCall = {
    url: "http://backend/api/document",
    method: "PUT",
    body: { revision: request.revision, document: request.document },
  };
  calls.push(call);
  const { status, json } = responder(call);
  if (status === 409) {
    // The api layer surfaces 409 as an ApiError carrying the server document.
    const { ApiError } = await import("@/lib/api");
    throw new ApiError({
      status: 409,
      reason: "revision 3 is stale, current is 9",
      document: (json as { document: ProjectDocument }).document,
      revision: (json as { revision: number }).revision,
    });
  }
  if (status === 422) {
    const { ApiError } = await import("@/lib/api");
    throw new ApiError({ status: 422, reason: "validation failed", errors: [{ loc: "body.components", msg: "bad" }] });
  }
  return json as { revision: number; document: ProjectDocument; problems?: Problem[] };
};

beforeEach(() => {
  vi.useFakeTimers();
  calls = [];
  responder = () => ({
    status: 200,
    json: { revision: 4, document: doc("saved", 4) },
  });
  setPutTransport(transport);
  useDocumentStore.getState().reset(doc("local"));
  useConnectionStore.getState().clearNotices();
  useProblemStore.getState().reset();
});

afterEach(() => {
  vi.useRealTimers();
  setPutTransport(null);
});

const store = () => useDocumentStore.getState();

describe("documentStore.apply", () => {
  it("applies the mutation locally at once and marks the copy dirty", () => {
    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "renamed" } }));
    expect(store().document?.project.name).toBe("renamed");
    expect(store().dirty).toBe(true);
    expect(calls).toHaveLength(0);
  });

  it("coalesces a burst of edits into one PUT carrying the final document", async () => {
    for (const name of ["a", "ab", "abc"]) {
      store().apply((draft) => ({ ...draft, project: { ...draft.project, name } }));
      await vi.advanceTimersByTimeAsync(60);
    }
    expect(calls).toHaveLength(0);

    await vi.advanceTimersByTimeAsync(COALESCE_MS);
    expect(calls).toHaveLength(1);
    expect(calls[0]?.body.document.project.name).toBe("abc");
    // The PUT carries the revision the client last saw.
    expect(calls[0]?.body.revision).toBe(3);
  });

  it("adopts the server document and revision on 200 and clears dirty", async () => {
    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "edited" } }));
    await vi.advanceTimersByTimeAsync(COALESCE_MS);

    expect(store().revision).toBe(4);
    expect(store().document?.project.name).toBe("saved");
    expect(store().dirty).toBe(false);
    expect(store().error).toBeNull();
  });

  it("records problems returned with the acknowledgement", async () => {
    responder = () => ({
      status: 200,
      json: {
        revision: 5,
        document: doc("saved", 5),
        problems: [
          {
            id: "p1",
            tier: "types",
            severity: "error",
            message: "boom",
            ref: "binding:site_binding.property.city",
          },
        ],
      },
    });
    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "edited" } }));
    await vi.advanceTimersByTimeAsync(COALESCE_MS);

    expect(useProblemStore.getState().problems).toHaveLength(1);
    expect(useProblemStore.getState().byRefIndex["binding:site_binding.property.city"]).toHaveLength(1);
  });

  it("adopts the winner and warns on 409, without losing the notice", async () => {
    const theirs = doc("theirs", 9);
    responder = () => ({ status: 409, json: { revision: 9, document: theirs, reason: "stale revision" } });

    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "mine" } }));
    await vi.advanceTimersByTimeAsync(COALESCE_MS);

    expect(store().document?.project.name).toBe("theirs");
    expect(store().revision).toBe(9);
    expect(store().dirty).toBe(false);
    const notices = useConnectionStore.getState().notices;
    expect(notices.some((notice) => notice.level === "warn" && /stale/.test(notice.text))).toBe(true);
  });

  it("keeps the local edit and reports field errors on 422", async () => {
    responder = () => ({ status: 422, json: { reason: "validation failed", errors: [{ loc: "body.components", msg: "bad" }] } });

    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "invalid" } }));
    await vi.advanceTimersByTimeAsync(COALESCE_MS);

    expect(store().document?.project.name).toBe("invalid");
    expect(store().dirty).toBe(true);
    expect(store().error?.errors[0]?.msg).toBe("bad");
  });

  it("sends the newer edit again when something changed while the PUT was in flight", async () => {
    type Ack = { revision: number; document: ProjectDocument };
    // Held in an object so TypeScript does not narrow the unassigned local to `never`.
    const deferred: { resolve: ((value: Ack) => void) | null } = { resolve: null };
    responder = () => ({ status: 200, json: {} });
    setPutTransport(
      (request) =>
        new Promise((resolve) => {
          calls.push({ url: "", method: "PUT", body: { revision: request.revision, document: request.document } });
          deferred.resolve = resolve;
        }),
    );

    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "first" } }));
    await vi.advanceTimersByTimeAsync(COALESCE_MS);
    expect(calls).toHaveLength(1);

    // Typed while the request was outstanding: must not be swallowed by the ack.
    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "second" } }));
    deferred.resolve?.({
      revision: 4,
      document: { ...doc("first", 4), project: { ...emptyDocument().project, name: "first" } },
    });
    await vi.advanceTimersByTimeAsync(COALESCE_MS + 20);

    expect(calls).toHaveLength(2);
    expect(calls[1]?.body.document.project.name).toBe("second");
    expect(store().document?.project.name).toBe("second");
  });
});

describe("documentStore undo/redo", () => {
  it("steps back over edits and forward again, sending each step", async () => {
    responder = () => ({ status: 200, json: { revision: 4, document: doc("server", 4) } });

    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "one" } }));
    await vi.advanceTimersByTimeAsync(COALESCE_MS);
    store().apply((draft) => ({ ...draft, project: { ...draft.project, name: "two" } }));
    await vi.advanceTimersByTimeAsync(COALESCE_MS);

    // The last acknowledgement replaced the document, so undo starts from there.
    const before = store().document;
    store().undo();
    expect(store().document).not.toBe(before);
    expect(store().future.length).toBeGreaterThan(0);
    const undone = store().document;
    store().redo();
    expect(store().document).not.toBe(undone);
    await vi.advanceTimersByTimeAsync(COALESCE_MS);
    expect(calls.length).toBeGreaterThan(2);
  });

  it("does nothing when there is no history", () => {
    store().undo();
    store().redo();
    expect(store().document?.project.name).toBe("local");
    expect(store().dirty).toBe(false);
  });
});

describe("problemStore indexing", () => {
  const problem = (overrides: Partial<Problem>): Problem => ({
    id: overrides.id ?? Math.random().toString(36).slice(2),
    tier: "types",
    severity: "error",
    message: "message",
    ...overrides,
  });

  it("indexes by ref and rolls part problems up to their entity", () => {
    useProblemStore.getState().setProblems([
      problem({ ref: "binding:site_binding.property.city" }),
      problem({ ref: "component:site", severity: "warning", tier: "blueprint" }),
      problem({ ref: null, tier: "build", severity: "info" }),
    ]);
    const state = useProblemStore.getState();

    expect(state.byRefIndex["binding:site_binding.property.city"]).toHaveLength(1);
    // The whole-binding ref sees the part's problem, which is what lights its badge.
    expect(state.byRefIndex["binding:site_binding"]).toHaveLength(1);
    expect(state.byRefIndex["component:site"]).toHaveLength(1);
    expect(state.problems).toHaveLength(3);
    expect(state.counts).toEqual({ errors: 1, warnings: 1, infos: 1 });
  });

  it("indexes by file and replaces only the tiers a merge brings", () => {
    useProblemStore.getState().setProblems([
      problem({ file: "kg_project/bindings/site/__init__.py", line: 12 }),
      problem({ file: "kg_project/bindings/site/__init__.py", line: 4 }),
      problem({ file: "kg_project/sources.py", tier: "blueprint" }),
    ]);
    expect(useProblemStore.getState().byFile["kg_project/bindings/site/__init__.py"]).toHaveLength(2);
    // Severity then line ordering, so the worst and earliest come first.
    expect(useProblemStore.getState().problems[1]?.line).toBe(12);

    useProblemStore.getState().mergeProblems([problem({ tier: "blueprint", message: "only blueprint" })]);
    const merged = useProblemStore.getState().problems;
    expect(merged.filter((item) => item.tier === "blueprint")).toHaveLength(1);
    expect(merged.filter((item) => item.tier === "types")).toHaveLength(2);
  });

  it("replaces a named tier even when the new list for it is empty", () => {
    useProblemStore.getState().setProblems([
      problem({ tier: "types", message: "pyright says" }),
      problem({ tier: "blueprint", message: "blueprint says" }),
      problem({ tier: "document", message: "document says" }),
    ]);

    // A clean blueprint pass: its tier empties, the rest survives.
    useProblemStore.getState().setTierProblems(["blueprint"], []);
    expect(useProblemStore.getState().problems.map((item) => item.tier)).toEqual([
      "types",
      "document",
    ]);

    // A document ack that carries nothing must not touch the types tier.
    useProblemStore.getState().setTierProblems(["document"], [
      problem({ tier: "document", message: "document says again" }),
    ]);
    const state = useProblemStore.getState();
    expect(state.problems).toHaveLength(2);
    expect(state.problems.find((item) => item.tier === "types")?.message).toBe("pyright says");
    expect(state.problems.filter((item) => item.tier === "document")).toHaveLength(1);
  });
});

describe("status light", () => {
  it("is red on any error, amber when the generation is dirty, green when clean", async () => {
    const { statusLight } = await import("./connectionStore");
    expect(
      statusLight({ types: { errors: 1, warnings: 0, state: "ready" }, generation: { state: "clean" } }).level,
    ).toBe("error");
    expect(
      statusLight({ types: { errors: 0, warnings: 0, state: "ready" }, generation: { state: "dirty" } }).level,
    ).toBe("warn");
    expect(
      statusLight({ types: { errors: 0, warnings: 0, state: "ready" }, generation: { state: "clean" } }).level,
    ).toBe("ok");
    expect(statusLight(null).level).toBe("unknown");
    expect(statusLight(null).lines[0]).toContain("no status");
  });
});
