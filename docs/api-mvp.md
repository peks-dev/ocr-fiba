# API MVP

Guia practica para usar la API local del OCR engine.

## Levantar servidor

```bash
uvicorn api.main:create_app --factory --reload
```

La API queda disponible en:

```text
http://127.0.0.1:8000
```

## Health check

```bash
curl http://127.0.0.1:8000/health
```

## Smoke test

Con el servidor levantado, se puede validar el flujo principal de la API:

```bash
python scripts/smoke_api.py
```

Por default usa el stack configurado del MVP: cropper `openrouter` con `google/gemini-3-flash-preview` y extractor `docstrange` con `nanonets-ocr-3`. Tambien busca la primera imagen disponible en `dataset/sheet-*`, o se puede pasar una imagen explicita:

```bash
python scripts/smoke_api.py --image dataset/sheet-001/hoja.jpg
```

Opciones utiles:

```bash
python scripts/smoke_api.py \
  --base-url http://127.0.0.1:8000 \
  --runs-dir runs \
  --cleanup
```

## Ejecutar pipeline con upload

```bash
curl -X POST http://127.0.0.1:8000/v1/pipeline/full/upload \
  -F "file=@/ruta/a/hoja.jpg" \
  -F "run_id=run_demo" \
  -F "runs_dir=runs"
```

Respuesta esperada:

```json
{
  "success": true,
  "run_id": "run_demo",
  "step": "run_full_pipeline",
  "status": "completed",
  "data": {
    "result": {},
    "result_path": "runs/run_demo/result.json",
    "trace_path": "runs/run_demo/trace.json",
    "artifacts_dir": "runs/run_demo/artifacts"
  },
  "artifacts": []
}
```

Tambien se puede omitir `run_id`; el engine genera uno automaticamente.

## Ejecutar con opciones

El campo `options_json` acepta un objeto JSON serializado:

```bash
curl -X POST http://127.0.0.1:8000/v1/pipeline/full/upload \
  -F "file=@/ruta/a/hoja.jpg" \
  -F "run_id=run_demo" \
  -F 'options_json={"debug":true}'
```

## Listar runs

```bash
curl "http://127.0.0.1:8000/v1/runs?runs_dir=runs&limit=50"
```

Respuesta:

```json
{
  "runs_dir": "runs",
  "count": 1,
  "runs": [
    {
      "run_id": "run_demo",
      "run_dir": "runs/run_demo",
      "input_dir": "runs/run_demo/input",
      "artifacts_dir": "runs/run_demo/artifacts",
      "raw_dir": "runs/run_demo/raw",
      "trace_path": "runs/run_demo/trace.json",
      "result_path": "runs/run_demo/result.json",
      "has_trace": true,
      "has_result": true,
      "match_status": "success",
      "input_files": ["hoja.jpg"],
      "modified_at": 1710000000.0
    }
  ]
}
```

## Ver detalle de un run

```bash
curl "http://127.0.0.1:8000/v1/runs/run_demo?runs_dir=runs"
```

El detalle incluye el resumen del run, `input_files`, `match_status`, `artifacts_count` y una muestra de hasta 20 artefactos.

## Leer resultado

```bash
curl "http://127.0.0.1:8000/v1/runs/run_demo/result?runs_dir=runs"
```

Devuelve el contenido de:

```text
runs/run_demo/result.json
```

## Leer trace

```bash
curl "http://127.0.0.1:8000/v1/runs/run_demo/trace?runs_dir=runs"
```

Devuelve el contenido de:

```text
runs/run_demo/trace.json
```

## Listar artefactos

```bash
curl "http://127.0.0.1:8000/v1/runs/run_demo/artifacts?runs_dir=runs&limit=200"
```

Respuesta:

```json
{
  "run_id": "run_demo",
  "artifacts_dir": "/ruta/al/proyecto/runs/run_demo/artifacts",
  "count": 2,
  "artifacts": [
    {
      "name": "crops/team.png",
      "path": "/ruta/al/proyecto/runs/run_demo/artifacts/crops/team.png",
      "size_bytes": 12345,
      "modified_at": 1710000000.0
    }
  ]
}
```

## Descargar artefacto

```bash
curl -o team.png \
  "http://127.0.0.1:8000/v1/runs/run_demo/artifacts/crops/team.png?runs_dir=runs"
```

El nombre del artefacto debe ser relativo al directorio `artifacts` del run.

## Borrar run

```bash
curl -X DELETE "http://127.0.0.1:8000/v1/runs/run_demo?runs_dir=runs"
```

Respuesta:

```json
{
  "success": true,
  "run_id": "run_demo",
  "deleted": true
}
```

## Codigos de error comunes

| Codigo | Caso |
| --- | --- |
| `RUN_NOT_FOUND` | El run solicitado no existe. |
| `RUN_FILE_NOT_FOUND` | No existe `trace.json` o `result.json`. |
| `INVALID_RUN_ID` | El `run_id` contiene separadores o valores no permitidos. |
| `INVALID_RUN_DIR` | El path del run no es un directorio. |
| `INVALID_ARTIFACT_PATH` | El path del artefacto intenta salir de `artifacts`. |
| `ARTIFACT_NOT_FOUND` | El artefacto no existe o no es archivo. |
| `INVALID_OPTIONS_JSON` | `options_json` no es JSON valido. |
