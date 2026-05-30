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

## Autenticacion

La API puede ejecutarse en modo local abierto o con API key simple.

Variables relevantes:

```bash
OCR_ENV=development        # default
OCR_ENGINE_API_KEY=...     # requerido si OCR_ENV=production
OCR_RUNS_DIR=runs          # directorio server-side para runs
```

Si `OCR_ENGINE_API_KEY` no esta configurada en development, la API no exige autenticacion. Esto es util para desarrollo local.

Si `OCR_ENGINE_API_KEY` esta configurada, todas las rutas excepto `/health` requieren:

```text
Authorization: Bearer <OCR_ENGINE_API_KEY>
```

Ejemplo:

```bash
curl "http://127.0.0.1:8000/v1/runs" \
  -H "Authorization: Bearer $OCR_ENGINE_API_KEY"
```

En `OCR_ENV=production`, `OCR_ENGINE_API_KEY` es obligatorio al arrancar la app. Tambien se ignora cualquier `runs_dir` recibido del cliente y se usa siempre `OCR_RUNS_DIR`.

En produccion, las respuestas publicas tambien ocultan paths locales del filesystem como `run_dir`, `input_dir`, `artifacts_dir`, `raw_dir`, `trace_path`, `result_path` y `artifact.path`. En su lugar, cuando aplica, se agregan links relativos:

```json
{
  "links": {
    "run": "/v1/runs/run_demo",
    "result": "/v1/runs/run_demo/result",
    "trace": "/v1/runs/run_demo/trace",
    "artifacts": "/v1/runs/run_demo/artifacts"
  }
}
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

## Contrato MVP

Esta API esta pensada para uso local/confiable durante el MVP. El parametro `runs_dir` permite apuntar a directorios locales, por lo que no debe exponerse sin una capa adicional de autorizacion, aislamiento y politica de paths permitidos.

### Formato de error

Los errores esperados usan este formato:

```json
{
  "detail": {
    "success": false,
    "error": {
      "code": "RUN_NOT_FOUND",
      "message": "Run not found",
      "retryable": false
    }
  }
}
```

Los errores inesperados usan:

```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "Internal server error",
    "retryable": false
  }
}
```

### Endpoints

| Metodo | Path | Uso |
| --- | --- | --- |
| `GET` | `/health` | Verifica que la API responde. |
| `POST` | `/v1/pipeline/full` | Ejecuta pipeline con una imagen ya existente en disco. |
| `POST` | `/v1/pipeline/full/upload` | Sube una imagen y ejecuta pipeline completo. |
| `GET` | `/v1/runs` | Lista runs existentes. |
| `GET` | `/v1/runs/{run_id}` | Devuelve detalle resumido de un run. |
| `DELETE` | `/v1/runs/{run_id}` | Borra un run completo. |
| `GET` | `/v1/runs/{run_id}/result` | Devuelve `result.json`. |
| `GET` | `/v1/runs/{run_id}/trace` | Devuelve `trace.json`. |
| `GET` | `/v1/runs/{run_id}/artifacts` | Lista artefactos del run. |
| `GET` | `/v1/runs/{run_id}/artifacts/{name}` | Descarga un artefacto. |

### `POST /v1/pipeline/full`

Body JSON:

| Campo | Tipo | Requerido | Default | Descripcion |
| --- | --- | --- | --- | --- |
| `image_path` | `string` | si | - | Ruta local de la imagen a procesar. |
| `run_id` | `string \| null` | no | `null` | ID opcional del run. |
| `runs_dir` | `string` | no | `runs` | Directorio base para guardar runs. |
| `options` | `object` | no | defaults MVP | Opciones del pipeline. |

Errores principales: `INPUT_IMAGE_NOT_FOUND`, `INPUT_IMAGE_INVALID`, `INVALID_PIPELINE_REQUEST`.

### `POST /v1/pipeline/full/upload`

Form data:

| Campo | Tipo | Requerido | Default | Descripcion |
| --- | --- | --- | --- | --- |
| `file` | archivo | si | - | Imagen `.jpg`, `.jpeg`, `.png` o `.webp`. |
| `run_id` | `string \| null` | no | `null` | ID opcional del run. |
| `runs_dir` | `string` | no | `runs` | Directorio base para guardar runs. |
| `options_json` | `string \| null` | no | `null` | JSON serializado con opciones del pipeline. |

Errores principales: `UNSUPPORTED_UPLOAD_TYPE`, `EMPTY_UPLOAD`, `INVALID_OPTIONS_JSON`, `INVALID_PIPELINE_OPTIONS`, errores de proveedor.

### Opciones del pipeline

Defaults del MVP:

```json
{
  "cropper_provider": "openrouter",
  "cropper_model": "google/gemini-3-flash-preview",
  "extractor_provider": "docstrange",
  "extractor_model": "nanonets-ocr-3",
  "extractor_max_workers": 7,
  "validation_plugins": null,
  "grid_removal": false,
  "gamma": 0.7
}
```

Providers permitidos: `interfaze`, `gemini`, `glm`, `docstrange`, `qubrid`, `openrouter`.

### `GET /v1/runs`

Query params:

| Parametro | Tipo | Default | Rango |
| --- | --- | --- | --- |
| `runs_dir` | `string` | `runs` | - |
| `limit` | `integer` | `50` | `1..200` |

Respuesta: `{ runs_dir, count, runs }`, donde cada item de `runs` contiene rutas canonicas, `has_trace`, `has_result`, `match_status`, `input_files` y `modified_at`.

Errores principales: `INVALID_RUNS_DIR`.

### `GET /v1/runs/{run_id}`

Query params:

| Parametro | Tipo | Default |
| --- | --- | --- |
| `runs_dir` | `string` | `runs` |

Respuesta: resumen del run, `artifacts_count` y una muestra de hasta 20 artefactos.

Errores principales: `INVALID_RUN_ID`, `RUN_NOT_FOUND`.

### `DELETE /v1/runs/{run_id}`

Query params:

| Parametro | Tipo | Default |
| --- | --- | --- |
| `runs_dir` | `string` | `runs` |

Respuesta:

```json
{
  "success": true,
  "run_id": "run_demo",
  "deleted": true
}
```

Errores principales: `INVALID_RUN_ID`, `RUN_NOT_FOUND`, `INVALID_RUN_DIR`.

### `GET /v1/runs/{run_id}/result`

Query params:

| Parametro | Tipo | Default |
| --- | --- | --- |
| `runs_dir` | `string` | `runs` |

Respuesta: contenido JSON de `result.json`.

Errores principales: `INVALID_RUN_ID`, `RUN_FILE_NOT_FOUND`, `INVALID_RUN_JSON`.

### `GET /v1/runs/{run_id}/trace`

Query params:

| Parametro | Tipo | Default |
| --- | --- | --- |
| `runs_dir` | `string` | `runs` |

Respuesta: contenido JSON de `trace.json`.

Errores principales: `INVALID_RUN_ID`, `RUN_FILE_NOT_FOUND`, `INVALID_RUN_JSON`.

### `GET /v1/runs/{run_id}/artifacts`

Query params:

| Parametro | Tipo | Default | Rango |
| --- | --- | --- | --- |
| `runs_dir` | `string` | `runs` | - |
| `limit` | `integer` | `200` | `1..500` |

Respuesta: `{ run_id, artifacts_dir, count, artifacts }`, donde cada artefacto contiene `name`, `path`, `size_bytes` y `modified_at`.

Errores principales: `INVALID_RUN_ID`, `RUN_NOT_FOUND`, `INVALID_ARTIFACTS_DIR`.

### `GET /v1/runs/{run_id}/artifacts/{name}`

Query params:

| Parametro | Tipo | Default |
| --- | --- | --- |
| `runs_dir` | `string` | `runs` |

`name` debe ser relativo a `artifacts/`. Ejemplo: `crops/team.png`.

Respuesta: archivo binario.

Errores principales: `INVALID_RUN_ID`, `INVALID_ARTIFACT_PATH`, `ARTIFACT_NOT_FOUND`.

### Flujo recomendado para clientes

1. Ejecutar `POST /v1/pipeline/full/upload`.
2. Guardar `run_id`.
3. Consultar `GET /v1/runs/{run_id}` para estado y resumen.
4. Consultar `GET /v1/runs/{run_id}/result` para datos extraidos.
5. Consultar `GET /v1/runs/{run_id}/trace` para auditoria.
6. Consultar `GET /v1/runs/{run_id}/artifacts` para inspeccion visual.
7. Descargar artefactos puntuales con `GET /v1/runs/{run_id}/artifacts/{name}`.
8. Borrar runs temporales con `DELETE /v1/runs/{run_id}` cuando ya no se necesiten.
