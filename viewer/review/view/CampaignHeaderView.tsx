"use client";

import { useRef } from "react";
import {
  ClipboardCheck,
  Download,
  Orbit,
  PanelsTopLeft,
  Search,
  Upload,
  X,
  type LucideIcon,
} from "lucide-react";
import type { IconToken } from "@/shared/model/hierarchy";
import type { SearchKind } from "@/lib/types";
import type { CampaignHeaderModel } from "@/review/model/CampaignModel";

interface CampaignHeaderViewProps {
  model: CampaignHeaderModel;
}

const tabIcons: Partial<Record<IconToken, LucideIcon>> = {
  map: Orbit,
  explore: PanelsTopLeft,
  review: ClipboardCheck,
  search: Search,
  import: Upload,
};

const kindTone: Partial<Record<SearchKind, string>> = {
  property: "border-accent/40 bg-accent/15 text-accent-strong",
  step: "border-source/30 bg-source/10 text-source",
  asset: "border-asset/30 bg-asset/10 text-asset",
  binding: "border-binding/30 bg-binding/10 text-binding",
  relation: "border-transform/30 bg-transform/10 text-transform",
  projection: "border-transform/30 bg-transform/10 text-transform",
  instruction: "border-post/30 bg-post/10 text-post",
};

/**
 * Application header: brand, task switch, search and import.
 *
 * The view owns only the file-input element and search focus. Task, query,
 * results and import error are read from the injected campaign header model.
 */
export function CampaignHeaderView({ model }: CampaignHeaderViewProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const activeTab =
    model.task === "map" ? "map" : model.task === "review" ? "review" : "explorer";

  return (
    <header
      data-testid="topbar"
      data-level="window"
      className="relative z-30 flex h-8 shrink-0 items-center gap-2 border-b border-line-soft bg-inset px-3"
    >
      <div
        className="flex min-w-0 shrink-0 items-center gap-1.5"
        title={model.snapshot}
      >
        <span className="flex size-5 items-center justify-center text-accent" aria-hidden>
          <WaypointsMark />
        </span>
        <h1 className="max-w-[22rem] truncate text-[12.5px] font-semibold tracking-tight text-ink">
          {model.title || "kg-build-system viewer"}
        </h1>
        <span className="sr-only">{model.snapshot}</span>
      </div>

      <span aria-hidden className="h-4 w-px shrink-0 bg-line" />

      <nav aria-label="Workspaces" className="flex h-full shrink-0 items-stretch">
        {model.tabs.map((tab) => {
          const current = activeTab === tab.id;
          const Icon = tabIcons[tab.icon] ?? Orbit;
          return (
            <button
              key={tab.id}
              type="button"
              data-testid={`tab-${tab.id}`}
              onClick={() => model.onTask(tab.task)}
              aria-current={current ? "page" : undefined}
              title={tab.hint}
              className="ui-workspace-tab ui-focus-ring"
            >
              <Icon
                className={current ? "size-3.5 text-accent-strong" : "size-3.5 text-faint"}
                aria-hidden
              />
              <span>{tab.label}</span>
              {tab.id === "review" && model.review.total ? (
                <span
                  className="ui-chip tnum"
                  title={`${model.review.open} open of ${model.review.total} findings`}
                >
                  {model.review.open} open
                </span>
              ) : null}
            </button>
          );
        })}
      </nav>

      <span aria-hidden className="h-4 w-px shrink-0 bg-line" />

      <div className="relative min-w-0 flex-1">
        <Search
          className="pointer-events-none absolute top-1/2 left-2 size-3 -translate-y-1/2 text-faint"
          aria-hidden
        />
        <input
          data-testid="search-input"
          value={model.search.query}
          onChange={(event) => model.search.onQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              model.search.onQuery("");
              event.currentTarget.blur();
            }
            if (event.key === "Enter" && model.search.results[0]) {
              model.search.onSelect(model.search.results[0]);
            }
          }}
          aria-label="Search components, properties, steps, relations and assets"
          title="Search the snapshot. Press / to focus. Enter opens the first result."
          placeholder="Search entities, properties, steps, relations…"
          className="ui-input h-6 pr-7 pl-7 text-[11px] tracking-tight"
        />
        {model.search.query ? (
          <button
            type="button"
            onClick={() => model.search.onQuery("")}
            aria-label="Clear search"
            title="Clear search"
            className="ui-icon-button ui-focus-ring absolute top-1/2 right-0.5 size-5 -translate-y-1/2"
          >
            <X className="size-3" aria-hidden />
          </button>
        ) : (
          <kbd
            aria-hidden
            className="ui-kbd pointer-events-none absolute top-1/2 right-1.5 -translate-y-1/2"
          >
            /
          </kbd>
        )}
        {model.search.query ? (
          <div
            data-testid="search-results"
            className="ui-panel thin-scrollbar absolute top-full right-0 left-0 mt-1 max-h-80 overflow-y-auto"
          >
            <div className="ui-panel-header px-2.5 py-1.5">
              <span className="ui-section-label text-faint">Results</span>
              <span className="tnum font-mono text-[9px] text-faint">
                {model.search.results.length}
              </span>
            </div>
            {model.search.results.length ? (
              model.search.results.map((result) => (
                <button
                  key={result.id}
                  type="button"
                  data-testid={`search-result-${result.kind}`}
                  onClick={() => model.search.onSelect(result)}
                  title={`Open ${result.kind} ${result.name}`}
                  className="ui-outliner-row w-full justify-start gap-2.5 border-b border-line-soft px-2.5 py-1.5 text-left text-[11px] last:border-b-0 hover:bg-panel-soft"
                >
                  <span
                    className={`ui-chip w-[4.75rem] shrink-0 uppercase tracking-wider ${kindTone[result.kind] ?? "text-faint"}`}
                  >
                    {result.kind}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[11px] text-ink-soft">
                      {result.name}
                    </span>
                    <span className="block truncate text-[9px] text-faint">
                      {result.detail}
                    </span>
                  </span>
                  <span className="tnum font-mono text-[9px] text-faint">
                    {Math.round(result.score)}
                  </span>
                </button>
              ))
            ) : (
              <div className="px-3 py-5 text-center">
                <p className="text-[11px] text-muted">No matching entities.</p>
                <p className="mt-1 text-[9px] text-faint">
                  Try a component, property, step or relation name.
                </p>
              </div>
            )}
          </div>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <button
          type="button"
          data-testid="import-snapshot"
          onClick={() => fileInput.current?.click()}
          title="Import a snapshot, blueprint or workflow plan JSON"
          className="ui-button ui-button-primary ui-focus-ring h-6 min-h-0 px-2"
        >
          <Upload className="size-3" aria-hidden />
          <span className="hidden xl:inline">Import</span>
        </button>
        <input
          ref={fileInput}
          data-testid="import-file"
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) model.import.onFile(file);
            event.target.value = "";
          }}
        />
      </div>

      {model.import.error ? (
        <div
          role="alert"
          className="ui-card absolute top-full right-2 mt-1 flex max-w-sm items-center gap-2 border-critical/50 px-3 py-2 text-[10px] text-critical"
        >
          <Download className="size-3 shrink-0" aria-hidden />
          {model.import.error}
        </div>
      ) : null}
    </header>
  );
}

function WaypointsMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-4 text-accent" fill="none" aria-hidden>
      <path d="M5 6.5h4.5M14.5 6.5H19M5 17.5h4.5M14.5 17.5H19M9.5 6.5 12 12l-2.5 5.5M14.5 6.5 12 12l2.5 5.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="5" cy="6.5" r="1.6" fill="currentColor" />
      <circle cx="19" cy="6.5" r="1.6" fill="currentColor" />
      <circle cx="5" cy="17.5" r="1.6" fill="currentColor" />
      <circle cx="19" cy="17.5" r="1.6" fill="currentColor" />
    </svg>
  );
}
