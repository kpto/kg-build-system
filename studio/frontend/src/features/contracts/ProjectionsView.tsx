"use client";

/**
 * Projections — named row plans over ONE driving source.
 *
 * Each output is a named row whose expression is shown as a read-only summary chain
 * (`pathways.steps ▸ expand ▸ struct_field(role)`); expression stacks are edited in the
 * bindings composer, reachable through a deep link. The framework rule (§6) that a
 * projection has one driving source is derived from the outputs' field references and
 * shown in the header; adding an output that reads a second source is blocked with the
 * reason.
 */

import { useMemo, useState } from "react";
import clsx from "clsx";

import {
  Button,
  Card,
  Chip,
  EmptyState,
  IconButton,
  Panel,
  PlusIcon,
  ProblemBadge,
  SearchIcon,
  Select,
  TextInput,
  CloseIcon,
} from "@/components/ui";
import { buildRef } from "@/lib/ids";
import {
  expressionSummary,
  typeLabel,
  type Expression,
  type LogicalType,
  type ProjectDocument,
  type Projection,
} from "@/lib/ir";
import type { FeatureProps, SelectableEntry } from "@/lib/types";
import { notify } from "@/stores/connectionStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { chainSummary, canAddOutput, drivingSource, referrersOfProjection } from "@/features/contracts/logic";
import { deleteEntity, makeProjection, patchProjection } from "@/features/contracts/edit";

export function ProjectionsView({ document, index, problems, selectedRef, onSelectRef, apply }: FeatureProps) {
  const projections = document.projections ?? [];
  const selected = useMemo(
    () => projections.find((item) => selectedRef === buildRef("projection", item.id)) ?? null,
    [projections, selectedRef],
  );

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[minmax(14rem,18rem)_1fr] gap-px bg-edge">
      <ProjectionList
        projections={projections}
        problems={problems}
        selectedId={selected?.id ?? null}
        onSelect={(id) => onSelectRef(id ? buildRef("projection", id) : null)}
        onCreate={(label) => {
          const { projection, document: next } = makeProjection(label, document);
          apply(() => next);
          useSelectionStore.getState().selectAndReveal(buildRef("projection", projection.id));
        }}
      />
      {selected ? (
        <ProjectionDetail document={document} index={index} projection={selected} apply={apply} />
      ) : (
        <Panel title="Projection">
          <EmptyState
            title="No projection selected"
            body="A projection is a named logical data product over one driving source. Create one, then add outputs; the expression stack is authored in the bindings composer."
          />
        </Panel>
      )}
    </div>
  );
}

function ProjectionList({
  projections,
  problems,
  selectedId,
  onSelect,
  onCreate,
}: {
  projections: readonly Projection[];
  problems: FeatureProps["problems"];
  selectedId: string | null;
  onSelect(id: string | null): void;
  onCreate(label: string): void;
}) {
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [label, setLabel] = useState("");
  const filtered = projections.filter(
    (item) => !query || item.name.includes(query.toLowerCase()) || item.declaration_name.toLowerCase().includes(query.toLowerCase()),
  );
  const errors = problems.filter((problem) => problem.severity === "error").length;

  return (
    <Panel
      title="Projections"
      subtitle={`${projections.length}${query ? ` · ${filtered.length}` : ""}`}
      padded={false}
      actions={
        <Button size="sm" icon={<PlusIcon />} onClick={() => setCreating((value) => !value)}>
          new
        </Button>
      }
    >
      <div className="flex flex-col gap-1 p-2">
        <label className="flex items-center gap-1.5 rounded-md border border-edge bg-raised px-2">
          <SearchIcon />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="search projections…"
            aria-label="search projections"
            className="h-6 min-w-0 flex-1 bg-transparent text-[12px] text-ink outline-none placeholder:text-faint"
          />
        </label>
        {creating && (
          <div className="flex items-center gap-1">
            <TextInput
              autoFocus
              mono
              placeholder="projection name"
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && label.trim()) {
                  onCreate(label);
                  setLabel("");
                  setCreating(false);
                }
              }}
            />
            <IconButton
              size="sm"
              label="Create projection"
              icon={<PlusIcon />}
              disabled={!label.trim()}
              onClick={() => {
                onCreate(label);
                setLabel("");
                setCreating(false);
              }}
            />
          </div>
        )}
        <ul className="flex flex-col gap-px">
          {filtered.map((projection) => {
            const driving = drivingSource(projection);
            return (
              <li key={projection.id}>
                <button
                  type="button"
                  onClick={() => onSelect(projection.id)}
                  aria-current={selectedId === projection.id ? "true" : undefined}
                  className={clsx(
                    "flex w-full items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-raised",
                    selectedId === projection.id && "bg-raised",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate font-mono text-[12px] text-ink">{projection.name}</span>
                  <Chip tone={driving.conflict ? "danger" : driving.driving ? "relation" : "neutral"} title={driving.conflict ? "reads more than one source" : `driving source: ${driving.driving ?? "none yet"}`}>
                    {driving.conflict ? "multi-source" : driving.driving ?? "—"}
                  </Chip>
                  <span className="font-mono text-[10px] text-faint">{(projection.fields ?? []).length}</span>
                </button>
              </li>
            );
          })}
          {filtered.length === 0 && (
            <li className="px-1.5 py-2 text-[11px] text-faint">{projections.length === 0 ? "no projections yet" : "no match"}</li>
          )}
        </ul>
        {errors > 0 && <p className="px-1.5 pt-1 text-[11px] text-danger">{errors} error{errors === 1 ? "" : "s"} in projections</p>}
      </div>
    </Panel>
  );
}

function ProjectionDetail({
  document,
  index,
  projection,
  apply,
}: {
  document: ProjectDocument;
  index: FeatureProps["index"];
  projection: Projection;
  apply: FeatureProps["apply"];
}) {
  const ref = buildRef("projection", projection.id);
  const driving = drivingSource(projection);
  const [showAdd, setShowAdd] = useState(false);
  const selectAndReveal = useSelectionStore((state) => state.selectAndReveal);

  // Selectable sources the outputs may read, filtered to the driving source once set.
  const selectable = useMemo(() => index?.selectable ?? [], [index]);
  const available = useMemo(() => {
    if (driving.count <= 1) return selectable;
    return selectable.filter((entry) => entry.name === driving.driving);
  }, [selectable, driving]);

  const addOutput = (sourceName: string, path: readonly string[], logicalType: LogicalType) => {
    const expression: Expression = { kind: "field", source: sourceName, path: [...path], logical_type: logicalType };
    const guard = canAddOutput(document, projection, expression);
    if (!guard.ok) {
      notify({ level: "warn", text: guard.reason ?? "a projection may read only one driving source" });
      return;
    }
    const name = path[path.length - 1] ?? sourceName;
    const fields = [...(projection.fields ?? [])];
    let dedupe = name;
    for (let n = 2; fields.some((field) => field.name === dedupe); n += 1) dedupe = `${name}_${n}`;
    apply((draft) =>
      patchProjection(draft, projection.id, {
        fields: [...fields, { name: dedupe, expression, description: null }],
      }),
    );
    setShowAdd(false);
  };

  const removeOutput = (name: string) =>
    apply((draft) =>
      patchProjection(draft, projection.id, {
        fields: (projection.fields ?? []).filter((field) => field.name !== name),
      }),
    );

  const consumers = referrersOfProjection(document, projection);

  const goToBindings = () => {
    // The bindings tab owns `binding:*` refs; `setArea` routes there even when no
    // binding consumes the projection yet (the user is off to compose the first one).
    const first = consumers[0];
    if (first) selectAndReveal(first.ref);
    else notify({ level: "info", text: `No binding reads ${projection.name} yet — opening the bindings tab to compose one.` });
    useSelectionStore.getState().setArea("bindings");
  };

  return (
    <Panel
      title={projection.name}
      subtitle={`${(projection.fields ?? []).length} outputs`}
      actions={<ProblemBadge problems={[]} />}
      id="panel-projection-detail"
    >
      <div className="flex flex-col gap-2.5">
        {/* header: the derived single driving source */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] uppercase tracking-[0.06em] text-muted">driving source</span>
          {driving.conflict ? (
            <Chip tone="danger" title={driving.sources.join(", ")}>
              {`⚠ ${driving.count} sources: ${driving.sources.join(", ")}`}
            </Chip>
          ) : (
            <Chip tone={driving.driving ? "relation" : "neutral"}>{driving.driving ?? "no outputs yet"}</Chip>
          )}
          <input
            className="ml-auto w-56 rounded-md border border-edge bg-raised px-2 py-1 text-[12px] text-ink focus:border-info"
            value={projection.description ?? ""}
            placeholder="add a description…"
            aria-label="projection description"
            onChange={(event) => apply((draft) => patchProjection(draft, projection.id, { description: event.target.value || null }))}
          />
        </div>
        {driving.conflict && (
          <p className="rounded-md border border-danger/50 bg-danger/10 p-2 text-[12px] leading-snug text-ink">
            A projection has one driving logical source (§6); this one reads {driving.sources.join(" and ")}. Split it, or bring the
            second source in through its own projection and read that.
          </p>
        )}

        {/* outputs: named rows with a read-only chain summary */}
        <div className="flex flex-col gap-1.5">
          {(projection.fields ?? []).length === 0 && (
            <p className="rounded border border-dashed border-edge px-2 py-2 text-center text-[11px] text-faint">no outputs yet</p>
          )}
          {(projection.fields ?? []).map((field) => (
            <Card key={field.name}>
              <div className="flex min-w-0 items-center gap-2">
                <span className="shrink-0 font-mono text-[12px] text-ink">{field.name}</span>
                <Chip tone="relation" title={expressionSummary(field.expression)}>
                  <span className="max-w-[34rem] truncate">{chainSummary(field.expression)}</span>
                </Chip>
                <div className="ml-auto flex shrink-0 items-center gap-1">
                  <Button size="sm" variant="ghost" onClick={goToBindings} title="Open the binding that consumes this projection">
                    edit in Bindings composer
                  </Button>
                  <IconButton size="sm" label={`Remove output ${field.name}`} icon={<CloseIcon size={12} />} onClick={() => removeOutput(field.name)} />
                </div>
              </div>
              {field.description && <p className="pl-0.5 text-[11px] text-muted">{field.description}</p>}
            </Card>
          ))}
        </div>

        {/* add output: pick a source + path from the derived index */}
        {showAdd ? (
          <AddOutput
            selectable={available}
            driving={driving.driving}
            onPick={addOutput}
            onCancel={() => setShowAdd(false)}
          />
        ) : (
          <div>
            <Button size="sm" icon={<PlusIcon />} onClick={() => setShowAdd(true)}>
              add output
            </Button>
            {driving.driving && (
              <span className="ml-2 text-[11px] text-faint">new outputs must read <span className="font-mono text-info">{driving.driving}</span></span>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}

function AddOutput({
  selectable,
  driving,
  onPick,
  onCancel,
}: {
  selectable: readonly SelectableEntry[];
  driving: string | null;
  onPick(source: string, path: readonly string[], type: LogicalType): void;
  onCancel(): void;
}) {
  const sourceOptions = selectable.map((entry) => ({ value: entry.name, label: `${entry.kind === "projection" ? "◇ " : ""}${entry.name}` }));
  const [source, setSource] = useState(driving ?? sourceOptions[0]?.value ?? "");
  const entry = selectable.find((item) => item.name === source);
  const leafPaths = (entry?.paths ?? []).filter((path) => (path.path ?? []).length > 0);
  const [pathKey, setPathKey] = useState("");
  const chosen = leafPaths.find((path) => path.path.join(".") === pathKey) ?? null;

  return (
    <div className="flex flex-wrap items-end gap-2 rounded-md border border-edge bg-raised p-2">
      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-[11px] uppercase tracking-[0.06em] text-muted">source</span>
        <Select aria-label="output source" className="w-44" value={source} options={sourceOptions} onChange={(event) => { setSource(event.target.value); setPathKey(""); }} />
      </label>
      <label className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-[11px] uppercase tracking-[0.06em] text-muted">field path</span>
        <Select
          aria-label="output path"
          placeholder="choose a path…"
          value={pathKey}
          options={leafPaths.map((path) => ({ value: path.path.join("."), label: `${path.path.join(".")} : ${typeLabel(path.logical_type)}` }))}
          onChange={(event) => setPathKey(event.target.value)}
        />
      </label>
      <Button
        size="sm"
        variant="primary"
        disabled={!chosen}
        onClick={() => chosen && onPick(source, chosen.path, chosen.logical_type)}
      >
        add output
      </Button>
      <IconButton size="sm" label="Cancel" icon={<CloseIcon size={12} />} onClick={onCancel} />
    </div>
  );
}
