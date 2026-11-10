# Viewer screenshots

Captured at 1600×1000 from the current Open Targets 26.09 compile-only snapshot.
They are review aids, not golden images.

| File | What it shows |
| --- | --- |
| `01-topology.png` | **Control** and **Explorer** are collapsible side-bar headers; the pinned **Graph** and **Workflow** documents share one tab strip. The Graph owns its floating **Inspect** window, and the graph overview states the effective CC0 licence. |
| `02-workflow-map.png` | The pinned **Workflow** document as a compositor-style component graph with no title banner; zoom and expansion controls float over the canvas. Explorer keeps the whole design, including explicit **Tables** and **Projections** groups, and the workflow step catalogue. |
| `03-step-detail.png` | A single click on a workflow step opened a step document tab; its banner leads with a large step logo, and each section header carries its concept mark. Explorer keeps the workflow list. |
| `04-inspect.png` | `target` inspected in the Graph document with its effective licence in Inspect. The tab strip still has only the pinned Graph and Workflow documents. |
| `05-context-menu.png` | Right-clicking a node opens **Go to Detail**. |
| `06-both-sections.png` | **Control** and **Explorer** are open together with an adjustable separator; Explorer still states the whole design, including Workflow. |
| `07-preview-tab.png` | A single click in the graph Explorer opened one preview tab (`adverse_event`, italic). |
| `08-detail-property.png` | A property document opens with provenance, a pannable and zoomable **Workflow** graph of the steps that produce it, an expression tree from the provenance assets to the property, then its meaning and type chain. The effective licence sits in the banner; provenance group headers carry their concept marks and the property tab and banner share the property concept. |
| `09-explorer-menu.png` | Right-clicking an Explorer row offers **Go to Detail** and **Go to Graph**; workflow items offer **Go to Workflow**. |
| `10-workflow-step-graph.png` | A selected workflow component opened with **Open step group**, showing its step-level flow graph inside the Workflow tab. The selected step highlights its incident boundary links and dims the other steps; **Open step** opens its detail document. Steps fill columns top-to-bottom without row wrapping. |
| `11-workflow-selected-component.png` | Left-clicking a workflow component selects it without opening the step graph; its aggregated links highlight, the rest dim, and **Open step group** in the canvas toolbar is the explicit expansion control. |
| `12-detail-node.png` | A node document opens with provenance, a pannable and zoomable narrowed workflow graph, an expression tree from provenance assets to the node, then meaning and properties. The effective licence sits in the banner. Provenance group headers carry the asset, table and projection marks; asset references open assets and table/projection references open their own documents. |
| `13-detail-edge.png` | An edge with no declared properties states provenance from its binding identity and source/target expressions, names its source and target nodes as navigable banner references, shows the effective licence in the banner, and shows the narrowed workflow graph and expression tree below. |
| `14-table-detail.png` | A table opens its own Table document: concept banner with the effective licence, owning asset reference, columns, expression tree from asset through the table to its fields, and attached semantics. |
| `16-projection-detail.png` | A projection opens its own Projection document with its owning asset, columns, row source, expression tree from asset through the projection to its fields, and the effective licence in the banner. |
| `15-other-workflow.png` | The title-bar folder button loaded another workflow JSON; the frame stayed and the Workflow document now shows the loaded component and its step catalogue. |

A tab is a standalone document. It changes its editor and the applicable Control
body; Explorer always states the whole design. Middle-click closes a subject or
step tab; the pinned Graph and Workflow tabs cannot be closed.
