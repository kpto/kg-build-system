"use client";

/**
 * Modules — which workflow modules the build composes, in what order.
 *
 * PROP CONTRACT (`FeatureProps`, see `src/lib/types.ts`):
 *   document      `document.modules` is the ordered configuration: `{id, configuration,
 *                 enabled}`. An id resolves through the backend module catalogue, and
 *                 `core` is always appended by `compile`, so it is never listed here.
 *                 Refs are `module:<id>`.
 *   index         Unused; the catalogue is the right source (see below).
 *   problems      Pre-filtered problems whose ref is `module:*`.
 *   selectedRef / onSelectRef   The standard global selection.
 *   apply         Reorder, enable/disable and configure; optimistic and undoable.
 *
 * Implemented as the picker it needs to be (DESIGN.md §5): the left column is
 * `/api/catalog → modules` (read from the installed framework, each with the JSON
 * Schema of its own `CONFIGURATION_TYPE`, so a form here can never drift from the
 * module), and the right column is the document's ordered list.
 */

import clsx from "clsx";

import { Button, Card, Chip, EmptyState, IconButton, Panel, ProblemBadge, Toggle } from "@/components/ui";
import { ChevronIcon, PlusIcon } from "@/components/ui";
import type { FeatureProps, ModuleEntry } from "@/lib/types";
import { sectionItems } from "@/lib/ir";
import type { Module } from "@/lib/ir";
import { useCatalogStore } from "@/stores/catalogStore";
import { useProblemStore } from "@/stores/problemStore";
import { useSelectionStore } from "@/stores/selectionStore";

export default function ModulesFeature({
  document,
  problems,
  selectedRef,
  onSelectRef,
  apply,
}: FeatureProps) {
  const catalog = useCatalogStore((state) => state.catalog);
  const byRefIndex = useProblemStore((state) => state.byRefIndex);
  const modules = sectionItems(document, "modules");
  const entries: readonly ModuleEntry[] = catalog?.modules ?? [];
  const configured = new Set(modules.map((module) => module.id));

  const write = (next: readonly Module[]) =>
    apply((draft) => ({ ...draft, modules: [...next] }));

  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= modules.length) return;
    const next = [...modules];
    const item = next[index];
    const other = next[target];
    if (!item || !other) return;
    next[index] = other;
    next[target] = item;
    write(next);
  };

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[minmax(15rem,20rem)_1fr] gap-px bg-edge">
      <Panel title="Available modules" subtitle={`${entries.length} in the framework`}>
        {entries.length === 0 ? (
          <EmptyState
            title="Catalogue not loaded"
            body="The module catalogue comes from GET /api/catalog; it is unreadable until the backend answers."
          />
        ) : (
          <ul className="flex flex-col gap-1">
            {entries.map((entry) => (
              <li key={entry.id} className="studio-card flex items-start gap-2 p-2">
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-x-1.5">
                    <span className="min-w-0 break-words text-[12px] leading-tight text-ink">
                      {entry.label}
                    </span>
                    <Chip tone={entry.role === "target" ? "relation" : "category"}>{entry.role}</Chip>
                    {configured.has(entry.id) && <Chip tone="ok">configured</Chip>}
                  </p>
                  {entry.summary && (
                    <p className="pt-0.5 text-[11px] leading-snug text-muted">{entry.summary}</p>
                  )}
                </div>
                <Button
                  size="sm"
                  disabled={configured.has(entry.id)}
                  icon={<PlusIcon />}
                  onClick={() => {
                    const next: Module = {
                      id: entry.id,
                      configuration: (entry.default_configuration as Module["configuration"]) ?? null,
                      enabled: true,
                    };
                    write([...modules, next]);
                    useSelectionStore.getState().selectAndReveal(`module:${entry.id}`);
                  }}
                >
                  add
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel
        title="Build composition"
        subtitle={`${modules.length} modules · core is always appended`}
        id="panel-modules"
        actions={<ProblemBadge problems={problems} />}
      >
        {modules.length === 0 ? (
          <EmptyState title="No modules configured" body="Add one from the catalogue on the left." />
        ) : (
          <ol className="flex flex-col gap-1">
            {modules.map((module, index) => {
              const ref = `module:${module.id}`;
              const selected = selectedRef === ref;
              const entry = entries.find((candidate) => candidate.id === module.id);
              return (
                <li key={module.id}>
                  <Card
                    selected={selected}
                    onSelect={() => onSelectRef(selected ? null : ref)}
                    className={clsx(module.enabled === false && "opacity-60")}
                    header={
                      <div className="flex items-center gap-2">
                        <span className="w-4 shrink-0 text-right font-mono text-[10px] text-faint">
                          {index + 1}
                        </span>
                        <span className="min-w-0 break-words text-[12px] leading-tight text-ink">
                          {entry?.label ?? module.id}
                        </span>
                        <span className="truncate font-mono text-[10px] text-faint">{module.id}</span>
                        {entry && <Chip tone={entry.role === "target" ? "relation" : "category"}>{entry.role}</Chip>}
                        <span className="ml-auto flex items-center gap-1">
                          <ProblemBadge problems={byRefIndex[ref] ?? []} ref={ref} compact />
                          <IconButton
                            size="sm"
                            label="Move earlier"
                            icon={<ChevronIcon size={12} className="-rotate-90" />}
                            disabled={index === 0}
                            onClick={(event) => {
                              event.stopPropagation();
                              move(index, -1);
                            }}
                          />
                          <IconButton
                            size="sm"
                            label="Move later"
                            icon={<ChevronIcon size={12} className="rotate-90" />}
                            disabled={index === modules.length - 1}
                            onClick={(event) => {
                              event.stopPropagation();
                              move(index, 1);
                            }}
                          />
                        </span>
                      </div>
                    }
                  >
                    <div className="flex items-center gap-3 pt-1">
                      <Toggle
                        label="enabled"
                        checked={module.enabled !== false}
                        onChange={(checked) =>
                          write(
                            modules.map((item) =>
                              item.id === module.id ? { ...item, enabled: checked } : item,
                            ),
                          )
                        }
                      />
                      <p className="min-w-0 flex-1 truncate font-mono text-[11px] text-faint">
                        {module.configuration && Object.keys(module.configuration).length > 0
                          ? JSON.stringify(module.configuration)
                          : "default configuration"}
                      </p>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={(event) => {
                          event.stopPropagation();
                          write(modules.filter((item) => item.id !== module.id));
                          if (selected) onSelectRef(null);
                        }}
                      >
                        remove
                      </Button>
                    </div>
                  </Card>
                </li>
              );
            })}
          </ol>
        )}
      </Panel>
    </div>
  );
}
