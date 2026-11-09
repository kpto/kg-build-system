"use client";

import { useEffect, useRef, useState } from "react";
import {
  FileCode2,
  GitBranch,
  LayoutGrid,
  Maximize2,
  Workflow,
  ZoomIn,
} from "lucide-react";
import { PanelHeader } from "@/shared/ui/PanelHeader";
import { cx } from "@/shared/ui/theme";
import type { IconToken } from "@/shared/model/hierarchy";
import type {
  DiagnosisChildModel,
  DiagnosisModel,
} from "@/diagnosis/model/DiagnosisModel";
import type { SemanticsMode } from "@/diagnosis/semantics/model/SemanticsModel";
import { ExecutionGraphView } from "@/diagnosis/execution/view/ExecutionGraphView";
import { SemanticsGraphView } from "@/diagnosis/semantics/view/SemanticsGraphView";
import { ProvenanceGraphView } from "@/diagnosis/provenance/view/ProvenanceGraphView";

export interface ModelDiagnosisViewProps {
  model: DiagnosisModel;
}

interface RepresentationViewport {
  fitSignal: number;
  fitMode: "fit" | "read";
}

function RepresentationIcon({
  token,
  className,
}: {
  token: IconToken;
  className?: string;
}) {
  if (token === "blueprint") {
    return <FileCode2 className={className} aria-hidden />;
  }
  if (token === "lineage") {
    return <GitBranch className={className} aria-hidden />;
  }
  return <Workflow className={className} aria-hidden />;
}

function ActiveRepresentation({
  child,
  viewport,
  blueprintMode,
}: {
  child: DiagnosisChildModel;
  viewport: RepresentationViewport;
  blueprintMode: SemanticsMode;
}) {
  switch (child.id) {
    case "workflow":
      return <ExecutionGraphView model={child.model} viewport={viewport} />;
    case "blueprint":
      return (
        <SemanticsGraphView
          model={child.model}
          mode={blueprintMode}
          viewport={viewport}
        />
      );
    case "lineage":
      return <ProvenanceGraphView model={child.model} viewport={viewport} />;
  }
}

/**
 * The diagnosis panel view: one model header, the representation tabs and the
 * active representation's view.
 *
 * Fit/Read are view state. They are published through a view-local context so
 * every graph keeps the `{ model }` binding while still responding to the
 * shell's controls.
 */
export function ModelDiagnosisView({ model }: ModelDiagnosisViewProps) {
  const [fitMode, setFitMode] = useState<"fit" | "read">("fit");
  const [fitSignal, setFitSignal] = useState(0);
  const previousRepresentation = useRef(model.representation);
  const blueprintChild = model.child.id === "blueprint" ? model.child : undefined;
  const defaultBlueprintMode = blueprintChild?.model.overlay.defaultMode;
  const [blueprintMode, setBlueprintMode] = useState<SemanticsMode>(
    defaultBlueprintMode ?? "cards",
  );

  useEffect(() => {
    if (previousRepresentation.current === model.representation) return;
    previousRepresentation.current = model.representation;
    setFitMode("fit");
    // Each representation mounts its own canvas and applies its own opening
    // framing. Only an explicit Fit or Read press advances the fit signal.
  }, [model.representation]);

  useEffect(() => {
    if (defaultBlueprintMode) setBlueprintMode(defaultBlueprintMode);
  }, [defaultBlueprintMode]);

  const fit = () => {
    setFitMode("fit");
    setFitSignal((value) => value + 1);
  };

  const toggleReadable = () => {
    setFitMode((current) => (current === "read" ? "fit" : "read"));
    setFitSignal((value) => value + 1);
  };

  const modeOptions = blueprintChild
    ? [...blueprintChild.model.overlay.modes].sort((left, right) => {
        if (left.id === right.id) return 0;
        if (left.id === "cards") return -1;
        if (right.id === "cards") return 1;
        return 0;
      })
    : [];

  return (
    <section
      data-level="panel"
      aria-label={model.header.title}
      className="flex min-h-0 min-w-0 flex-1 flex-col bg-abyss"
    >
      <PanelHeader
        testId="editor-header"
        title={model.header.title}
        icon={
          <RepresentationIcon
            token={model.header.icon}
            className="size-3.5"
          />
        }
        meta={blueprintChild ? undefined : model.header.meta}
        actions={
          <>
            <button
              type="button"
              data-testid="fit-view"
              onClick={fit}
              aria-label="Fit the whole graph"
              title="Fit the whole graph in the canvas"
              className="ui-button ui-focus-ring h-6 min-h-0 px-1.5 text-[9px]"
            >
              <Maximize2 className="hidden size-3 2xl:inline" aria-hidden />
              <span>Fit</span>
            </button>
            <button
              type="button"
              data-testid="readable-view"
              onClick={toggleReadable}
              aria-pressed={fitMode === "read"}
              aria-label="Toggle readable zoom"
              title={
                fitMode === "read"
                  ? "Switch back to the whole-graph overview"
                  : "Zoom to a readable level; pan or use Fit for the whole graph"
              }
              className={cx(
                "ui-button ui-focus-ring h-6 min-h-0 px-1.5 text-[9px]",
                fitMode === "read" &&
                  "border-accent bg-accent-soft text-accent-strong",
              )}
            >
              <ZoomIn className="hidden size-3 2xl:inline" aria-hidden />
              <span>Read</span>
            </button>
          </>
        }
      >
        <nav aria-label="Representation" className="flex h-7 items-stretch">
          {model.tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              data-testid={`tab-${tab.id}`}
              onClick={tab.command}
              aria-current={tab.active ? "page" : undefined}
              title={tab.hint}
              className="ui-editor-tab ui-focus-ring"
            >
              <RepresentationIcon
                token={tab.icon}
                className={cx(
                  "size-3.5",
                  tab.active ? "text-accent-strong" : "text-faint",
                )}
              />
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
        {blueprintChild ? (
          <div
            data-testid="blueprint-mode-control"
            data-level="control"
            role="group"
            aria-label={blueprintChild.model.overlay.label}
            className="ml-1 inline-flex shrink-0 items-center rounded-[3px] border border-line bg-panel p-0.5"
          >
            {modeOptions.map((option) => {
              const Icon = option.id === "graph" ? GitBranch : LayoutGrid;
              const active = blueprintMode === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  data-testid={`blueprint-mode-${option.id}`}
                  aria-pressed={active}
                  onClick={() => setBlueprintMode(option.id)}
                  className={cx(
                    "inline-flex h-[22px] items-center gap-1 rounded-[2px] px-2 text-[9px]",
                    active
                      ? "bg-accent text-white"
                      : "text-muted hover:bg-panel-soft hover:text-text",
                  )}
                >
                  <Icon className="size-3" aria-hidden />
                  {option.label}
                </button>
              );
            })}
          </div>
        ) : null}
      </PanelHeader>
      <div className="relative min-h-0 flex-1">
        <ActiveRepresentation
          child={model.child}
          viewport={{ fitMode, fitSignal }}
          blueprintMode={blueprintMode}
        />
      </div>
    </section>
  );
}
