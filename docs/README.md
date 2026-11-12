# Documentation site

The Quartz site for `kg-build-system`. The content is in [`content/`](content/);
the specifications, reference and review appendices are part of that content.

## Serve

```console
cd docs
./serve.sh
```

Open <http://localhost:8080>.

## Check and build

```console
./check.sh      # structure, links, specs and generated blocks
./build.sh      # static output in public/
./verify.sh     # diagrams, generation, check and build
```

`./serve.sh` is the preview. Do not use `python -m http.server`: Quartz routes
are extensionless and a plain static file server returns 404 for them.
