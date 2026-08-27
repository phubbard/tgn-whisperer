# Documentation

## Architecture map

[`architecture.html`](architecture.html) is an interactive system map of TGN Whisperer —
the RSS → transcribe → attribute → markdown → build → deploy pipeline, its Prefect
orchestration, and the external services it depends on (FluidAudio on the Mac Studio,
Anthropic Claude, Caddy). Open it in a browser: it's a single self-contained file with
pan/zoom, light/dark themes, node search, relationship tracing, and source links back to
the code at the revision it was generated from.

It was produced with [**archify**](https://github.com/tt-a1i/archify), which compiles a
small typed JSON spec into the validated HTML. The spec lives beside it:

- [`architecture.architecture.json`](architecture.architecture.json) — the source spec
  (edit this, not the HTML). It pins `meta.repository.revision` so the diagram's source
  links resolve to a specific commit.

### Regenerating

With the archify skill available (`npx skills add tt-a1i/archify -g`, or a local checkout),
from the archify skill package directory:

```bash
# validate the spec (showcase quality, verifying source-evidence paths)
node bin/archify.mjs validate architecture <path>/architecture.architecture.json \
  --quality showcase --repo-root <repo-root> --json

# render the final HTML
node bin/archify.mjs deliver architecture <path>/architecture.architecture.json \
  <repo-root>/docs/architecture.html --quality showcase --repo-root <repo-root> --json
```

When the code or topology changes, update `architecture.architecture.json` (and bump
`meta.repository.revision` to the new HEAD), then re-run `deliver`.

## Plans

[`plans/`](plans/) holds point-in-time design documents.
