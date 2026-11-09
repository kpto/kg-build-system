"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpRight,
  Check,
  Copy,
  GitBranch,
  Info,
  Layers3,
  SlidersHorizontal,
  Waypoints,
  FileCode2,
} from "lucide-react";
import { AnnotationPopover } from "@/shared/ui/AnnotationPopover";
import { PanelHeader } from "@/shared/ui/PanelHeader";
import { Row } from "@/shared/ui/Row";
import { Section } from "@/shared/ui/Section";
import { cx } from "@/shared/ui/theme";
import type {
  PropertiesAnnotation,
  PropertiesBlock,
  PropertiesField,
  PropertiesModel,
  PropertiesRailId,
  PropertiesRow,
} from "@/properties/model/PropertiesModel";

type IconComponent = typeof Info;

const RAIL_ICONS: Record<PropertiesRailId, IconComponent> = {
  definition: Info,
  production: Waypoints,
  emission: FileCode2,
  dependencies: GitBranch,
  context: Layers3,
};

const KIND_DOT: Record<string, string> = {
  step: "bg-source",
  binding: "bg-binding",
  property: "bg-accent-strong",
  topology: "bg-transform",
  data: "bg-asset",
  asset: "bg-asset",
  field: "bg-secondary",
  "lineage-node": "bg-target",
};

function FieldCopy({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    [],
  );

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={() => void copy()}
      aria-label={`Copy ${label}`}
      title={copied ? "Copied" : `Copy ${label}`}
      className="ui-icon-button ui-focus-ring size-5 shrink-0"
    >
      {copied ? (
        <Check className="size-2.5" aria-hidden />
      ) : (
        <Copy className="size-2.5" aria-hidden />
      )}
    </button>
  );
}

function EvidenceField({ field }: { field: PropertiesField }) {
  return (
    <div
      data-level="field"
      className="group/field relative grid grid-cols-[88px_minmax(0,1fr)] items-baseline gap-2 px-2 py-0.5"
      title={field.title}
    >
      <span className="text-right text-[9px] leading-[1.4] text-faint">
        {field.label}
      </span>
      <span
        className={cx(
          "min-w-0 text-[10px] leading-[1.5] break-words text-text",
          field.mono === false ? "font-sans" : "font-mono",
          field.copy && "pr-5",
        )}
      >
        {field.value}
      </span>
      {field.copy ? (
        <span className="absolute top-1/2 right-1 -translate-y-1/2 opacity-0 transition-opacity group-hover/field:opacity-100 focus-within:opacity-100">
          <FieldCopy text={field.value} label={field.label} />
        </span>
      ) : null}
    </div>
  );
}

function Code({ label = "Text", text }: { label?: string; text: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    [],
  );

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="mt-1">
      <Row className="border-b-0">
        <span className="ui-section-title flex-1">{label}</span>
        <button
          type="button"
          data-testid="copy-code"
          onClick={() => void copy()}
          disabled={!text.trim()}
          aria-label={`Copy ${label.toLowerCase()} block`}
          title={copied ? "Copied" : `Copy ${label.toLowerCase()} block`}
          className={`ui-button ui-button-ghost min-h-0 gap-1 px-1.5 py-0.5 text-[9px] ${
            copied ? "text-accent-strong" : ""
          }`}
        >
          {copied ? (
            <Check className="size-2.5" aria-hidden />
          ) : (
            <Copy className="size-2.5" aria-hidden />
          )}
          {copied ? "Copied" : "Copy"}
        </button>
      </Row>
      <pre className="ui-inset thin-scrollbar mx-2 mb-1 max-h-64 overflow-auto p-2 font-mono text-[9px] leading-relaxed whitespace-pre-wrap text-ink-soft">
        {text}
      </pre>
    </div>
  );
}

function PropertiesRowView({ row }: { row: PropertiesRow }) {
  const action = row.actions?.[0];
  const direction =
    row.direction === "in" ? (
      <span className="inline-flex shrink-0 items-center gap-1 text-[8.5px] text-muted">
        <span className="size-1.5 rounded-full bg-source" aria-hidden />
        in
      </span>
    ) : row.direction === "out" ? (
      <span className="inline-flex shrink-0 items-center gap-1 text-[8.5px] text-muted">
        <span className="size-1.5 rounded-full bg-target" aria-hidden />
        out
      </span>
    ) : null;

  const header = action ? (
    <Row
      as="button"
      interactive
      selected={row.selected}
      onClick={() => action.run()}
      title={row.title ?? action.title}
      className="group/row w-full justify-start"
    >
      {direction}
      <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-ink-soft">
        {row.label}
      </span>
      {row.meta ? <span className="ui-row-meta max-w-[6rem] truncate">{row.meta}</span> : null}
      <ArrowUpRight
        className="size-3 shrink-0 text-faint opacity-0 transition-opacity group-hover/row:opacity-100 group-focus-within/row:opacity-100"
        aria-hidden
      />
    </Row>
  ) : (
    <Row>
      {direction}
      <span className="min-w-0 flex-1 truncate font-mono text-[10px]">
        {row.label}
      </span>
      {row.meta ? <span className="ui-row-meta max-w-[6rem] truncate">{row.meta}</span> : null}
    </Row>
  );

  if (!row.blocks?.length) return header;
  return (
    <div
      className={cx(
        row.kind === "branch" && "border-b border-line-soft last:border-b-0",
      )}
    >
      {header}
      {row.blocks.map((block, position) => (
        <PropertiesBlockView key={`${row.id}:${position}`} block={block} />
      ))}
    </div>
  );
}

function PropertiesBlockView({ block }: { block: PropertiesBlock }) {
  switch (block.kind) {
    case "field":
      return <EvidenceField field={block.field} />;
    case "row":
      return <PropertiesRowView row={block.row} />;
    case "pills":
      return (
        <div className="flex flex-wrap gap-1 px-2 py-1">
          {block.values.map((value) => (
            <span key={value} className="ui-chip text-[9px] text-ink-soft">
              {value}
            </span>
          ))}
          {!block.values.length && block.empty ? (
            <p className="ui-hint">{block.empty}</p>
          ) : null}
        </div>
      );
    case "code":
      return <Code label={block.label} text={block.text} />;
    case "text":
      return (
        <p
          className={cx(
            "text-muted",
            block.mono ? "font-mono text-[9px]" : "text-[10px] leading-relaxed",
            block.breakAll ? "break-all px-2 py-1" : "px-2 py-1 text-pretty",
          )}
        >
          {block.text}
        </p>
      );
    case "empty":
      return <p className="ui-hint px-2 py-1">{block.text}</p>;
  }
}

function SectionAnnotation({
  value,
  model,
}: {
  value?: PropertiesAnnotation;
  model: PropertiesModel;
}) {
  if (!value) return null;
  return (
    <AnnotationPopover
      annotations={value.annotations}
      context={value.context}
      metaGraph={model.metaGraph}
      compact
    />
  );
}

function PropertiesRail({
  model,
  active,
  onSelect,
}: {
  model: PropertiesModel;
  active: PropertiesRailId;
  onSelect: (id: PropertiesRailId) => void;
}) {
  const visible = model.rails.filter((rail) => model.sectionsFor[rail.id].length > 0);
  return (
    <div
      data-testid="properties-rail"
      className="ui-properties-rail"
      aria-label="Property sections"
      role="toolbar"
    >
      {visible.map((rail) => {
        const Icon = RAIL_ICONS[rail.id];
        const current = active === rail.id;
        return (
          <button
            key={rail.id}
            type="button"
            data-testid={`properties-rail-${rail.id}`}
            onClick={() => onSelect(rail.id)}
            aria-pressed={current}
            aria-label={`${rail.label}: ${rail.question}`}
            title={`${rail.label}: ${rail.question}`}
            className={cx(
              "ui-icon-button ui-properties-rail-tab ui-focus-ring",
            )}
          >
            <Icon className="size-3.5" aria-hidden />
          </button>
        );
      })}
    </div>
  );
}

export interface PropertiesViewProps {
  model: PropertiesModel;
}

/**
 * The Properties panel binds to an injected `PropertiesModel`.
 *
 * The active rail and the scroll position are view state. The rail list, the
 * sections each rail answers and every field/row are model data.
 */
export function PropertiesView({ model }: PropertiesViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeRail, setActiveRail] = useState<PropertiesRailId>("definition");
  const availableRails = useMemo(
    () => model.rails.filter((rail) => model.sectionsFor[rail.id].length > 0),
    [model],
  );

  useEffect(() => {
    const first = availableRails[0]?.id;
    if (first) setActiveRail(first);
    scrollRef.current?.scrollTo({ top: 0 });
  }, [model, availableRails]);

  const active =
    model.rails.find((rail) => rail.id === activeRail) ?? model.rails[0];
  const sections = model.sectionsFor[active.id] ?? [];
  const focusSearch = () => {
    document.querySelector<HTMLInputElement>('[data-testid="search-input"]')?.focus();
  };

  if (model.empty) {
    return (
      <aside
        data-testid="inspector"
        data-level="panel"
        className="ui-properties flex h-full w-[22rem] shrink-0 flex-col overflow-hidden"
      >
        <PanelHeader
          title={model.title}
          icon={<SlidersHorizontal className="size-3.5" />}
          meta="empty"
        />
        <div className="flex min-h-0 flex-1">
          <div
            ref={scrollRef}
            className="thin-scrollbar min-h-0 flex-1 overflow-y-auto"
          >
            <div
              className="px-3 py-4"
              data-level="section"
              aria-label="Why is no evidence shown?"
            >
              <p className="ui-section-title">
                {model.emptyState?.title ?? "Nothing selected"}
              </p>
              <p className="ui-hint mt-1.5 max-w-[22rem]">
                {model.emptyState?.hint}
              </p>
              <button
                type="button"
                onClick={focusSearch}
                className="ui-button ui-button-primary ui-focus-ring mt-2"
              >
                {model.emptyState?.actionLabel ?? "Search subjects"}
              </button>
            </div>
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside
      data-testid="inspector"
      data-level="panel"
      className="ui-properties flex h-full w-[22rem] shrink-0 flex-col overflow-hidden"
    >
      <PanelHeader
        title={model.title}
        icon={<SlidersHorizontal className="size-3.5" />}
        meta={model.subjectTitle}
        actions={
          model.kind && model.kindLabel ? (
            <span
              data-testid="inspector-kind"
              className="inline-flex shrink-0 items-center gap-1.5 text-[9px] text-muted"
            >
              <span
                aria-hidden
                className={cx(
                  "size-1.5 rounded-full",
                  KIND_DOT[model.kind] ?? "bg-faint",
                )}
              />
              {model.kindLabel}
            </span>
          ) : null
        }
      />
      <div className="flex min-h-0 flex-1">
        <PropertiesRail model={model} active={active.id} onSelect={setActiveRail} />
        <div
          ref={scrollRef}
          className="thin-scrollbar min-h-0 flex-1 overflow-y-auto"
        >
          {sections.map((entry) => (
            <div key={entry.id} data-section={entry.id}>
              <Section
                title={entry.title}
                question={entry.question}
                count={entry.count}
                actions={
                  <SectionAnnotation value={entry.annotations} model={model} />
                }
                collapsible
                bodyClassName="py-1"
              >
                {entry.blocks.map((block, position) => (
                  <PropertiesBlockView
                    key={`${entry.id}:${position}`}
                    block={block}
                  />
                ))}
              </Section>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
