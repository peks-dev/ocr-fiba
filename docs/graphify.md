# Graphify: versioned repository knowledge

Graphify is pinned to `0.9.26`. Install it from the hash-locked dependency set:

```bash
./scripts/setup-graphify
```

Start architecture and dependency work with `graphify query`, `graphify path`,
or `graphify explain`, then confirm details against source files.

After a logical change:

```bash
./scripts/graphify-update
./scripts/graphify-check
git diff -- graphify-out/ .graphifyignore
```

Canonical outputs (`graph.json`, `graph.html`, `GRAPH_REPORT.md`, and
`manifest.json`) are versioned. Local caches, interpreter/root markers, internal
labels, costs, and backups are ignored. Graphify hooks are forbidden; no setup,
update, or check script stages or commits files. Semantic documentation changes
also require `$graphify . --update`.
