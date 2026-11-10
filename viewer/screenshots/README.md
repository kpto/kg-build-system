# Viewer screenshots

Captured at 1600×1000 from the current Open Targets 26.09 compile-only snapshot.
They are review aids, not golden images.

| File | What it shows |
| --- | --- |
| `01-topology.png` | **Control** and **Detail** are collapsible side-bar headers; the pinned **Graph** and **Workflow** documents share one tab strip. The Graph owns its floating **Inspect** window. |
| `02-workflow.png` | The pinned **Workflow** document: step catalogue grouped by component, selected step instruction, payload, openings and connections. Control shows workflow filters. |
| `03-inspect.png` | `target` inspected in the Graph document. The tab strip still has only **Graph** and **Workflow**. |
| `04-context-menu.png` | Right-clicking a node opens **Go to Detail**. |
| `05-both-sections.png` | **Control** and **Detail** are open together with an adjustable separator; every Detail tree group is collapsed. |
| `06-preview-tab.png` | A single click in the Detail tree opened one preview tab (`adverse_event`, italic). Control states that the subject document has no view controls. |
| `07-detail-property.png` | **Go to Detail** on a property opened a permanent document while the preview tab remained. |

A tab is a standalone document. It changes its editor and the applicable Control
body; it never opens, closes or switches the side bar. Middle-click closes a
subject tab; the pinned Graph and Workflow tabs cannot be closed.
