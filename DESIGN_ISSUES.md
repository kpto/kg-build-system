# Design limits

The toolchain kernel and the distribution are implemented. These are the
current choices, not compatibility promises.

The canonical, classified table is [docs/content/appendix/review/limits.md](docs/content/appendix/review/limits.md),
published at `/review/limits`. Every row there is one of six kinds: model rule,
replaceable default, current algorithm, not implemented, interface limit or
empirical; most name the object that replaces them.

The model rules — the boundaries no composition removes:

- **Composition.** A `Toolchain` is the only composition unit. There is no
  registry; a language, planner or executor is a value passed to a `Toolchain`,
  and a provider is added to the runtime.
- **Asset layout.** `AssetLayout` is descriptive metadata, not an access
  contract; a planner may interpret it.
- **Struct keys.** A repeated struct graph name takes its qualified Python name
  as an extra key segment; the blueprint still names the struct by its graph
  role.
- **Exact instruction kinds.** `execute` builds the exact-kind map before the
  first step and refuses a kind no executor claims; another executor claims
  another exact kind.
- **Directed edges.** The topology carries directed `Edge[Source, Target]`
  only; an undirected assertion is reified or added as a language declaration
  kind, which is a model change.
