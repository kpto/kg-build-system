# Viewer screenshots

Captured at 1600×1000 from the current Open Targets 26.09 compile-only snapshot.
They are review aids, not golden images.

| File | What it shows |
| --- | --- |
| `01-topology.png` | **Control** and **Explorer** are collapsible side-bar headers; the pinned **Graph** and **Workflow** documents share one tab strip. The Graph owns its floating **Inspect** window. |
| `02-workflow-map.png` | The pinned **Workflow** document as a compositor-style component graph: node headers, sockets and aggregated links. Explorer keeps the whole design and the workflow step catalogue. |
| `03-step-detail.png` | A single click on a workflow step opened a step document tab with its instruction, openings, payload and connections. Explorer keeps the workflow list. |
| `04-inspect.png` | `target` inspected in the Graph document. The tab strip still has only Graph, Workflow and the current preview document. |
| `05-context-menu.png` | Right-clicking a node opens **Go to Detail**. |
| `06-both-sections.png` | **Control** and **Explorer** are open together with an adjustable separator; Explorer still states the whole design, including Workflow. |
| `07-preview-tab.png` | A single click in the graph Explorer opened one preview tab (`adverse_event`, italic). |
| `08-detail-property.png` | **Go to Detail** on a property opened a permanent document while the preview tab remained. |
| `09-explorer-menu.png` | Right-clicking an Explorer row offers **Go to Detail** and **Go to Graph**; workflow items offer **Go to Workflow**. |

A tab is a standalone document. It changes its editor and the applicable Control
body; Explorer always states the whole design. Middle-click closes a subject or
step tab; the pinned Graph and Workflow tabs cannot be closed.
