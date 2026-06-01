# Project structure

This repository is organized as a Python monorepo with independent packages.

```text
packages/
  core-engine/  # OCR domain library: pipeline, providers, validation, prompts, schemas, utils
  api/          # FastAPI HTTP adapter; depends on core-engine
  cli/          # command-line tools; depends on core-engine
  mcp/          # MCP server/client adapter; talks to the OCR API
```

Dependency direction:

```text
ocr-engine-core <- ocr-engine-api <- ocr-engine-mcp
ocr-engine-core <- ocr-engine-cli
```

Rules:

- `ocr_engine_core` must not import `ocr_engine_api`, `ocr_engine_cli`, or `ocr_engine_mcp`.
- API, CLI, and MCP are adapters around the core engine.
- The MCP package is API-client based by default, so it can run separately from the OCR process.
- Runtime outputs stay outside package source directories (`runs/`, `outputs/`, `dataset/results/`).

Local test command:

```bash
PYTHONPATH=packages/core-engine/src:packages/api/src:packages/cli/src:packages/mcp/src \
  python -m unittest discover -s tests -p 'test_*.py'
```

Console scripts after installing the workspace:

```bash
ocr-api
ocr-run
ocr-dataset
ocr-binarize
ocr-progressive-score
ocr-mcp
```
