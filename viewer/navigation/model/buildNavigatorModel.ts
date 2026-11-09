import type { CampaignView } from "@/shared/model/campaign";
import type { NavigatorInput } from "@/shared/model/builders";
import type { ActionModel, IconToken } from "@/shared/model/hierarchy";
import type { InspectorSelection } from "@/shared/types/selection";
import type { EntityKind, WorkflowStep } from "@/lib/types";
import { stepKey } from "@/lib/indexes";
import type {
  NavigatorModel,
  NavigatorRow,
  NavigatorRowKind,
  NavigatorSection,
  NavigatorSlice,
} from "./NavigatorModel";

const SECTION_QUESTIONS: Record<string, string> = {
  Workflow: "Which workflow steps can I inspect?",
  Topology: "Which topology subjects can I inspect?",
  Provenance: "Which properties can I trace to their source?",
  "Source model":
    "Which source-model assets, data entities and bindings are available?",
};

function typeLabel(type: { name?: string; kind?: string } | undefined): string {
  if (!type) return "";
  return type.name ?? type.kind ?? "";
}

function searchText(...values: Array<string | number | null | undefined>): string {
  return values
    .filter((value) => value !== undefined && value !== null)
    .map(String)
    .join(" ")
    .toLowerCase();
}

function action(
  id: string,
  label: string,
  icon: IconToken,
  run: () => void,
  title?: string,
): ActionModel {
  return { id, label, icon, title, run };
}

function countRows(rows: readonly NavigatorRow[] | undefined, kinds: readonly NavigatorRowKind[]): number {
  if (!rows?.length) return 0;
  let count = 0;
  for (const row of rows) {
    if (kinds.includes(row.kind)) count += 1;
    count += countRows(row.children, kinds);
  }
  return count;
}

function sliceFor(campaign: CampaignView): NavigatorSlice {
  return campaign.representation === "workflow"
    ? "workflow"
    : campaign.representation === "blueprint"
      ? "blueprint"
      : "lineage";
}

function section(
  id: string,
  title: string,
  icon: IconToken,
  rows: NavigatorRow[],
  tally: NavigatorRowKind[],
  total: number,
  empty?: string,
): NavigatorSection {
  return {
    id,
    title,
    question: SECTION_QUESTIONS[title] ?? `Which ${title.toLowerCase()} entries can I inspect?`,
    icon,
    rows,
    count: countRows(rows, tally),
    total,
    tally,
    empty,
  };
}

function selectionMatchesStep(
  selection: InspectorSelection | null,
  step: WorkflowStep,
): boolean {
  return selection?.kind === "step" && stepKey(selection.step.id) === stepKey(step.id);
}

/**
 * Build the Outliner model.
 *
 * The builder owns the whole tree: section questions, counts, grouping,
 * selected state, search haystacks and the actions that change the campaign.
 * The view only owns the filter text and the expansion of a group.
 */
export function buildNavigatorModel(
  campaign: CampaignView,
  input: NavigatorInput,
): NavigatorModel {
  const index = campaign.record.index;
  const selection = campaign.selection;
  const slice = sliceFor(campaign);
  const groupingLabel = input.grouping === "component" ? "component" : "instruction";
  const groupPrefix = input.grouping === "component" ? "component" : "emitter";

  const selectedStepKey =
    selection?.kind === "step" ? stepKey(selection.step.id) : null;
  const selectedEntity =
    selection?.kind === "topology" ? selection : null;
  const selectedProperty =
    selection?.kind === "property" ? selection.selection : null;

  const entitySelected = (kind: EntityKind, name: string) =>
    selectedEntity?.entityKind === kind && selectedEntity.name === name;
  const propertySelected = (kind: EntityKind, name: string, property: string) =>
    selectedProperty?.kind === kind &&
    selectedProperty.component === name &&
    selectedProperty.property === property;

  const workflowGroups = new Map<string, WorkflowStep[]>();
  for (const step of index.steps) {
    const group =
      input.grouping === "component"
        ? step.id[0]
        : step.instruction.kind.join(":");
    const existing = workflowGroups.get(group) ?? [];
    existing.push(step);
    workflowGroups.set(group, existing);
  }

  const workflowRows: NavigatorRow[] = [...workflowGroups.entries()].map(
    ([group, steps]) => {
      const groupKey = `${groupPrefix}:${group}`;
      const collapsed = input.collapsedGroups.has(groupKey);
      return {
        id: `workflow-group:${groupKey}`,
        kind: "group",
        label: group,
        meta: String(steps.length),
        metaFromChildren: true,
        tally: ["step"],
        collapsed,
        search: searchText(group),
        openOnSelection: true,
        icon: "outliner",
        actions: [
          action(
            "toggle-group",
            collapsed ? "Expand" : "Collapse",
            collapsed ? "expand" : "collapse",
            () => input.onToggleGroup(groupKey),
            `${collapsed ? "Expand" : "Collapse"} ${group}`,
          ),
        ],
        children: steps.map((step) => {
          const emitter = step.instruction.kind.join(":");
          return {
            id: `step:${stepKey(step.id)}`,
            kind: "step",
            label: step.id[1],
            meta: `${step.id[0]} · ${emitter}`,
            title: `Inspect workflow step ${step.id.join(" / ")}`,
            icon: "branch",
            selected: selectedStepKey === stepKey(step.id),
            countsAs: "step",
            search: searchText(group, step.id[0], step.id[1], emitter),
            actions: [
              action(
                "select-step",
                step.id[1],
                "branch",
                () => campaign.commands.selectStep(step),
                `Inspect workflow step ${step.id.join(" / ")}`,
              ),
            ],
          } satisfies NavigatorRow;
        }),
      } satisfies NavigatorRow;
    },
  );

  const workflowCount = countRows(workflowRows, ["step"]);
  const workflowSection = section(
    "workflow",
    "Workflow",
    "workflow",
    workflowRows,
    ["step"],
    index.steps.length,
    "No workflow steps match.",
  );

  const topologyGroups = new Map<
    string,
    Array<{
      entityKind: EntityKind;
      name: string;
      properties: NonNullable<(typeof index.topologyNodes)[number]["properties"]>;
    }>
  >();
  const addEntity = (entityKind: EntityKind, entity: (typeof index.topologyNodes)[number]) => {
    const parent = entity.parent?.at(-1)?.trim() || "uncategorized";
    const group = topologyGroups.get(parent) ?? [];
    group.push({
      entityKind,
      name: entity.name,
      properties: entity.properties ?? [],
    });
    topologyGroups.set(parent, group);
  };
  for (const node of index.topologyNodes) addEntity("node", node);
  for (const edge of index.topologyEdges) addEntity("edge", edge);

  const topologyRows: NavigatorRow[] = [...topologyGroups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([parent, items]) => {
      const sortedItems = [...items].sort(
        (left, right) =>
          left.name.localeCompare(right.name) ||
          left.entityKind.localeCompare(right.entityKind),
      );
      return {
        id: `topology-group:${parent}`,
        kind: "group",
        label: parent,
        meta: String(sortedItems.length),
        metaFromChildren: true,
        tally: ["entity"],
        icon: "outliner",
        openOnSelection: true,
        children: sortedItems.map((item) => {
          const entity = entitySelected(item.entityKind, item.name);
          return {
            id: `entity:${item.entityKind}:${item.name}`,
            kind: "entity",
            label: item.name,
            meta: String(item.properties.length),
            metaFromChildren: true,
            icon: item.entityKind === "node" ? "navigator" : "branch",
            entityKind: item.entityKind,
            selected: entity,
            countsAs: "entity",
            openOnSelection: true,
            search: searchText(
              item.name,
              item.properties.map((property) => property.name).join(" "),
            ),
            actions: [
              action(
                "select-entity",
                item.name,
                item.entityKind === "node" ? "navigator" : "branch",
                () =>
                  campaign.commands.select({
                    kind: "topology",
                    entityKind: item.entityKind,
                    name: item.name,
                  }),
                `Inspect ${item.name}`,
              ),
            ],
            children: item.properties.map((property) => ({
              id: `property:${item.entityKind}:${item.name}.${property.name}`,
              kind: "property",
              label: property.name,
              meta: typeLabel(property.logical_type),
              typeLabel: typeLabel(property.logical_type),
              title: `Trace ${item.name}.${property.name} to lineage`,
              entityKind: item.entityKind,
              selected: propertySelected(
                item.entityKind,
                item.name,
                property.name,
              ),
              search: searchText(
                item.name,
                property.name,
                typeLabel(property.logical_type),
                property.description,
              ),
              actions: [
                action(
                  "select-property",
                  property.name,
                  "trace",
                  () =>
                    campaign.commands.selectProperty(
                      item.entityKind,
                      item.name,
                      property.name,
                    ),
                  `Trace ${item.name}.${property.name} to lineage`,
                ),
              ],
            } satisfies NavigatorRow)),
          } satisfies NavigatorRow;
        }),
      } satisfies NavigatorRow;
    });

  const topologyCount = countRows(topologyRows, ["entity"]);
  const rootTitle =
    slice === "workflow"
      ? "Workflow"
      : slice === "blueprint"
        ? "Topology"
        : "Provenance";
  const rootIcon: IconToken =
    slice === "workflow"
      ? "workflow"
      : slice === "blueprint"
        ? "navigator"
        : "branch";
  const topologySection = section(
    slice,
    rootTitle,
    rootIcon,
    topologyRows,
    ["entity"],
    index.topologyNodes.length + index.topologyEdges.length,
    `No ${rootTitle.toLowerCase()} subjects match.`,
  );

  const assetRows: NavigatorRow[] = index.assets.map((asset) => {
    const members = Object.keys(asset.layout?.members ?? {});
    return {
      id: `asset:${asset.name}`,
      kind: "asset",
      label: asset.name,
      meta: asset.version ?? "—",
      icon: "asset",
      countsAs: "asset",
      search: searchText(
        asset.name,
        asset.version,
        asset.semantics?.subject,
        asset.semantics?.description,
        members.map((member) => `${member} ${asset.layout?.members?.[member] ?? ""}`).join(" "),
      ),
      actions: [
        action(
          "select-asset",
          asset.name,
          "open",
          () => campaign.commands.select({ kind: "asset", name: asset.name }),
          `Inspect asset ${asset.name}`,
        ),
      ],
      children: [
        {
          id: `asset-subject:${asset.name}`,
          kind: "member",
          label: asset.semantics?.subject ?? "no subject",
          search: searchText(asset.semantics?.subject),
        },
        ...members.map((member) => ({
          id: `asset-member:${asset.name}.${member}`,
          kind: "member",
          label: member,
          detail: `${member} → ${asset.layout?.members?.[member] ?? ""}`,
          title: `${member} → ${asset.layout?.members?.[member] ?? ""}`,
          search: searchText(member, asset.layout?.members?.[member]),
        } satisfies NavigatorRow)),
      ],
    } satisfies NavigatorRow;
  });

  const dataOwner = (
    owner: { name: string; description?: string; columns: Array<{ name: string; logical_type: { name?: string; kind?: string }; description?: string }> },
    entityType: "relation" | "projection" | "struct",
    meta: string,
    icon: IconToken,
    index: number,
  ): NavigatorRow => {
    const ownerId = `data:${entityType}:${index}:${owner.name}`;
    return {
      id: ownerId,
      kind: "owner",
      label: owner.name,
      meta,
      icon,
      countsAs: "owner",
      search: searchText(owner.name, owner.description),
      actions: [
        action(
          "select-data",
          owner.name,
          "open",
          () =>
            campaign.commands.select({
              kind: "data",
              entityType,
              name: owner.name,
            }),
          `Inspect ${entityType} ${owner.name}`,
        ),
      ],
      children: owner.columns.map((column) => {
        const fieldKey = `${owner.name}.${column.name}`;
        return {
          id: `field:${ownerId}:${column.name}`,
          kind: "field",
          label: column.name,
          meta: typeLabel(column.logical_type),
          typeLabel: typeLabel(column.logical_type),
          title: `Inspect field ${fieldKey}`,
          selected: selection?.kind === "field" && selection.fieldKey === fieldKey,
          search: searchText(
            owner.name,
            column.name,
            typeLabel(column.logical_type),
            column.description,
          ),
          actions: [
            action(
              "select-field",
              fieldKey,
              "field",
              () =>
                campaign.commands.select({
                  kind: "field",
                  fieldKey,
                }),
              `Inspect field ${fieldKey}`,
            ),
          ],
        } satisfies NavigatorRow;
      }),
    } satisfies NavigatorRow;
  };

  const relationRows = index.relations.map((relation, index) =>
    dataOwner(relation, "relation", "rel", "layers", index),
  );
  const projectionRows = index.projections.map((projection, index) =>
    dataOwner(projection, "projection", "proj", "layers", index),
  );
  const structRows = index.structs.map((struct, index) =>
    dataOwner(struct, "struct", "struct", "layers", index),
  );

  const bindingRows: NavigatorRow[] = [...index.bindingByComponent.entries()].map(
    ([component, bindings]) => ({
      id: `bindings:${component}`,
      kind: "group",
      label: component,
      meta: String(bindings.length),
      metaFromChildren: true,
      tally: ["binding"],
      icon: "binding",
      search: searchText(component),
      children: bindings.map((binding) => {
        const propertyNames = Object.keys(binding.binding.properties ?? {}).join(", ");
        const label = `#${binding.index} ${binding.kind} · ${propertyNames}`;
        return {
          id: `binding:${binding.component}:${binding.index}`,
          kind: "binding",
          label,
          title: `Inspect binding ${label}`,
          countsAs: "binding",
          selected:
            selection?.kind === "binding" &&
            selection.binding.component === binding.component &&
            selection.binding.index === binding.index,
          search: searchText(
            component,
            binding.kind,
            binding.outputArtifact.join("."),
            propertyNames,
          ),
          actions: [
            action(
              "select-binding",
              label,
              "binding",
              () => campaign.commands.select({ kind: "binding", binding }),
              `Inspect binding ${label}`,
            ),
          ],
        } satisfies NavigatorRow;
      }),
    }),
  );

  const dataTotal = index.relations.length + index.projections.length + index.structs.length;
  const assetLabel: NavigatorRow = {
    id: "source-assets",
    kind: "label",
    label: "Assets",
    fixed: true,
    tally: ["asset"],
    total: index.assets.length,
    count: countRows(assetRows, ["asset"]),
    children: assetRows,
    empty: "No assets match.",
  };
  const dataLabel: NavigatorRow = {
    id: "source-data",
    kind: "label",
    label: "Data",
    fixed: true,
    tally: ["owner"],
    total: dataTotal,
    count: countRows([...relationRows, ...projectionRows, ...structRows], ["owner"]),
    children: [...relationRows, ...projectionRows, ...structRows],
    empty: "No data entities match.",
  };
  const bindingLabel: NavigatorRow = {
    id: "source-bindings",
    kind: "label",
    label: "Bindings",
    fixed: true,
    tally: ["binding"],
    total: index.bindings.length,
    count: countRows(bindingRows, ["binding"]),
    children: bindingRows,
    empty: "No bindings match.",
  };

  const sourceSection = section(
    "source-model",
    "Source model",
    "asset",
    [assetLabel, dataLabel, bindingLabel],
    ["asset", "owner", "binding"],
    index.assets.length + dataTotal + index.bindings.length,
  );

  const showSourceModel = slice !== "workflow";
  const sections = showSourceModel
    ? [topologySection, sourceSection]
    : [workflowSection];
  const activeCount = showSourceModel ? topologyCount : workflowCount;
  const activeTotal = showSourceModel
    ? index.topologyNodes.length + index.topologyEdges.length
    : index.steps.length;
  const sourceCount = countRows(sourceSection.rows, sourceSection.tally);

  return {
    id: "outliner",
    title: "Outliner",
    icon: "outliner",
    meta:
      slice === "workflow"
        ? `${activeCount} steps`
        : `${activeCount} subjects`,
    slice,
    grouping: input.grouping,
    groupingLabel,
    filterPlaceholder: "Filter this tree…",
    filterLabel: "Filter the active outliner tree",
    filterTitle: "Filter the active model slice by name, type or member",
    clearFilterLabel: "Clear explorer filter",
    collapseAllLabel: "Collapse all outliner collections",
    expandAllLabel: "Expand all outliner collections",
    sections,
    activeCount,
    activeTotal,
    sourceCount,
    sourceTotal: sourceSection.total,
    showSourceModel,
    empty: false,
  };
}

/**
 * Apply the view's filter to the already-built tree.
 *
 * The filter is a pure model transform: a matching group keeps all its
 * children, a matching label keeps itself but filters its children, and a
 * section/label tally is recomputed from the visible rows. The view owns only
 * the query string.
 */
export function filterNavigatorModel(
  model: NavigatorModel,
  query: string,
): NavigatorModel {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return { ...model, empty: false, noMatches: undefined };

  const filterRow = (row: NavigatorRow): NavigatorRow | undefined => {
    const self =
      Boolean(row.fixed) ||
      (row.search ? row.search.includes(normalized) : false);
    const filteredChildren = row.children
      ?.map(filterRow)
      .filter((child): child is NavigatorRow => Boolean(child));
    const visibleChildren = self && !row.fixed ? row.children : filteredChildren;

    if (!self && !visibleChildren?.length) return undefined;

    const next: NavigatorRow = {
      ...row,
      children: visibleChildren,
    };
    if (next.tally) {
      next.count = countRows(next.children, next.tally);
    }
    if (next.metaFromChildren) {
      next.meta = String(next.children?.length ?? 0);
    }
    return next;
  };

  const sections = model.sections.map((entry) => {
    const rows = entry.rows
      .map(filterRow)
      .filter((row): row is NavigatorRow => Boolean(row));
    return {
      ...entry,
      rows,
      count: countRows(rows, entry.tally),
    } satisfies NavigatorSection;
  });

  const active =
    sections.find((entry) => entry.id === model.slice) ??
    sections.find((entry) => entry.id === "workflow");
  const source = sections.find((entry) => entry.id === "source-model");
  const activeCount = active?.count ?? 0;
  const sourceCount = source?.count ?? 0;
  const empty =
    activeCount === 0 && (!model.showSourceModel || sourceCount === 0);

  return {
    ...model,
    sections,
    activeCount,
    sourceCount,
    empty,
    noMatches: empty
      ? {
          title: "No matches",
          hint: `No subjects match “${query.trim()}”.`,
        }
      : undefined,
  };
}
