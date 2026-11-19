# @kbs/design

The shared design language for the viewer surfaces.

- `tokens.css` — the Tailwind `@theme` tokens, the role scale and the base
  element behaviour. Both apps import it; no app declares a local palette.
- `theme.ts` — the same tokens as JavaScript names for SVG, canvas and inline
  styles.
- `primitives/` — the shared `Panel`, `PanelHeader`, `Label`, `Meta`, `Row`,
  `RowButton`, `Field`, `Control`, `Input`, `Select`, `Empty`, `Hint` and `Kbd`.

`viewer/design` and `viewer/console` are npm workspaces here. Import the package
as `@kbs/design`; do not copy a token or a primitive into an app.

```console
cd viewer
npm install
```
