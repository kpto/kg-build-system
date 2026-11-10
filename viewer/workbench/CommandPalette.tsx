"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { CircleDot, FileText, Search, X } from "lucide-react";

import { searchIndex } from "@/lib/search";
import type { SearchKind, SearchRecord } from "@/lib/types";
import { useWorkbench } from "./store";
import type { WorkbenchSelection } from "./types";

export interface CommandPaletteProps {
  onClose(): void;
}

interface PaletteItem {
  id: string;
  group: "subject";
  label: string;
  detail: string;
  selection: WorkbenchSelection;
}

interface SubjectTarget {
  selection: WorkbenchSelection;
  tabLabel: string;
}

const DESIGN_SEARCH_KINDS = new Set<SearchKind>([
  "topology-node",
  "topology-edge",
  "property",
  "relation",
  "projection",
  "struct",
  "field",
  "asset",
]);


function subjectTarget(
  record: SearchRecord,
  indexSteps: Array<{ id: [string, string]; instruction: { kind: [string, string] } }>,
): SubjectTarget {
  const tabLabel = record.label || record.name;
  const base: WorkbenchSelection = {};

  switch (record.kind) {
    case "property":
      return {
        selection: {
          ...base,
          kind: "property",
          name: record.name,
          component: record.component ?? record.name,
          property: record.property,
          level: "property",
        },
        tabLabel,
      };
    case "topology-node":
    case "topology-edge":
      return {
        selection: {
          ...base,
          kind: record.kind === "topology-edge" ? "edge" : "node",
          name: record.name,
          component: record.name,
          level: record.kind === "topology-edge" ? "edge" : "node",
        },
        tabLabel,
      };
    case "relation":
    case "projection":
    case "struct":
      return {
        selection: {
          ...base,
          kind: record.kind === "projection" ? "projection" : "relation",
          name: record.name,
          component: record.name,
        },
        tabLabel,
      };
    case "field":
      return {
        selection: {
          ...base,
          kind: "field",
          name: record.name,
          component: record.component,
        },
        tabLabel,
      };
    case "asset":
      return {
        selection: { ...base, kind: "asset", name: record.name, component: record.name },
        tabLabel,
      };
    case "binding":
      return {
        selection: {
          ...base,
          kind: "binding",
          name: record.name,
          component: record.component,
        },
        tabLabel,
      };
    case "step":
      return {
        selection: {
          ...base,
          kind: "step",
          name: record.name,
          component: record.component,
          ...(record.stepId ? { stepId: record.stepId } : {}),
        },
        tabLabel,
      };
    case "instruction": {
      const step = indexSteps.find(
        (candidate) => candidate.instruction.kind.join(":") === record.name,
      );
      return {
        selection: {
          ...base,
          kind: "step",
          name: record.name,
          ...(step ? { component: step.id[0], stepId: step.id } : {}),
        },
        tabLabel,
      };
    }
    case "workflow-component": {
      const step = indexSteps.find((candidate) => candidate.id[0] === record.name);
      return {
        selection: {
          ...base,
          kind: "step",
          name: record.name,
          component: record.name,
          ...(step ? { stepId: step.id } : {}),
        },
        tabLabel,
      };
    }
    default:
      return {
        selection: { ...base, name: record.name },
        tabLabel,
      };
  }
}

export function CommandPalette({ onClose }: CommandPaletteProps) {
  const { state, actions } = useWorkbench();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const subjectItems = useMemo<PaletteItem[]>(() => {
    const trimmed = query.trim();
    if (!trimmed) return [];
    return searchIndex(state.index.searchRecords, trimmed, { limit: 18 })
      .filter((record) => DESIGN_SEARCH_KINDS.has(record.kind))
      .map((record) => {
        const target = subjectTarget(record, state.index.steps);
        return {
          id: `subject:${record.kind}:${record.id}`,
          group: "subject" as const,
          label: record.label || record.name,
          detail: `${record.kind.replaceAll("-", " ")} · ${record.detail}`,
          selection: target.selection,
        };
      },
    );
  }, [query, state.index]);

  const items = subjectItems;
  const boundedActive = items.length === 0 ? 0 : Math.min(active, items.length - 1);

  const choose = (item: PaletteItem | undefined) => {
    if (!item) return;
    actions.openTab({ selection: item.selection });
    onClose();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((current) => (items.length ? (current + 1) % items.length : 0));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((current) =>
        items.length ? (current - 1 + items.length) % items.length : 0,
      );
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(items[boundedActive]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    }
  };

  const renderItem = (item: PaletteItem, index: number) => {
    const Icon = CircleDot;
    const isActive = index === boundedActive;
    return (
      <button
        key={item.id}
        type="button"
        role="option"
        aria-selected={isActive}
        className="wb-palette-result"
        data-active={isActive ? "true" : undefined}
        onMouseEnter={() => setActive(index)}
        onClick={() => choose(item)}
      >
        <span className="wb-palette-result-icon">
          <Icon aria-hidden className="size-4" />
        </span>
        <span className="wb-palette-result-copy">
          <span className="wb-palette-result-label">{item.label}</span>
          <span className="wb-palette-result-detail">{item.detail}</span>
        </span>
        <span className="wb-palette-result-kind">
          {item.selection.kind ?? "document"}
        </span>
      </button>
    );
  };

  return (
    <div
      className="wb-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="wb-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onKeyDown={onKeyDown}
        data-testid="command-palette"
      >
        <div className="wb-palette-search">
          <Search aria-hidden className="size-4" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActive(0);
            }}
            placeholder="Search subjects"
            aria-label="Search subjects"
            autoComplete="off"
            spellCheck={false}
          />
          <button
            type="button"
            className="wb-icon-button"
            aria-label="Close command palette"
            title="Close command palette"
            onClick={onClose}
          >
            <X aria-hidden className="size-3.5" />
          </button>
        </div>

        <div className="wb-palette-results thin-scrollbar" role="listbox" aria-label="Results">
          {subjectItems.length > 0 ? (
            <div className="wb-palette-group">
              <p className="wb-palette-group-label">Subjects</p>
              {subjectItems.map((item, index) => renderItem(item, index))}
            </div>
          ) : null}
          {items.length === 0 ? (
            <div className="wb-palette-empty">
              <FileText aria-hidden className="size-5" />
              <p>
                {query.trim()
                  ? `No subject matches “${query.trim()}”.`
                  : "Type a subject to open its document."}
              </p>
            </div>
          ) : null}
        </div>

        <footer className="wb-palette-footer">
          <span>
            <kbd className="wb-kbd">↑</kbd>
            <kbd className="wb-kbd">↓</kbd> navigate
          </span>
          <span>
            <kbd className="wb-kbd">Enter</kbd> open
          </span>
          <span>
            <kbd className="wb-kbd">Esc</kbd> close
          </span>
          <span className="wb-palette-count">{items.length} results</span>
        </footer>
      </div>
    </div>
  );
}
