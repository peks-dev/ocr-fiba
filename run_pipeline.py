"""
Entry point for running the FIBA OCR pipeline with model selection.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from helpers.image_utils import load_dotenv
from config.pipeline_config import PipelineConfig, SectionOverride
from core.pipeline import FibaOcrPipeline
from core.exceptions import OcrEngineError


def _output_success(result: dict, as_json: bool) -> None:
    """Output a successful pipeline result."""
    if as_json:
        response = {
            "success": True,
            "data": result,
        }
        print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        # Human-readable summary
        print(f"\nEstado: {result.get('match_status')}")
        warnings = result.get("validation_warnings", [])
        if warnings:
            print(f"Warnings ({len(warnings)}):")
            for w in warnings:
                print(f"  [{w.get('severity', '?')}] {w.get('plugin', '?')}: {w.get('message')}")
        print(f"Total tokens: {result.get('meta', {}).get('total_tokens', 0)}")


def _output_error(exc: OcrEngineError, as_json: bool) -> None:
    """Output a pipeline error in standardized format."""
    if as_json:
        response = {
            "success": False,
            "error": exc.to_dict(),
        }
        print(json.dumps(response, indent=2, ensure_ascii=False), file=sys.stderr)
    else:
        print(f"\nError: {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="FIBA Scoresheet OCR Pipeline (Model-Agnostic)"
    )
    parser.add_argument(
        "image",
        help="Imagen de hoja FIBA ya preprocesada (ej. outputs/test-3-recortada.jpg)",
    )
    parser.add_argument(
        "--output-dir",
        help="Directorio donde se guardarán los recortes y resultado",
    )
    parser.add_argument(
        "--cropper",
        choices=["interfaze", "gemini", "glm", "docstrange", "qubrid", "openrouter"],
        default="gemini",
        help="Proveedor para detección de secciones (default: gemini)",
    )
    parser.add_argument(
        "--cropper-model",
        default="gemini-3-flash-preview",
        help="Modelo del cropper (default: gemini-3-flash-preview)",
    )
    parser.add_argument(
        "--extractor",
        choices=["interfaze", "gemini", "glm", "docstrange", "qubrid", "openrouter"],
        default="docstrange",
        help="Proveedor para extracción de datos (default: docstrange)",
    )
    parser.add_argument(
        "--extractor-model",
        default="nanonets-ocr-3",
        help="Modelo del extractor (default: nanonets-ocr-3)",
    )
    parser.add_argument(
        "--extractor-reasoning-effort",
        default=None,
        choices=["xhigh", "high", "medium", "low", "minimal", "none"],
        help="Reasoning effort for the global extractor (OpenRouter only). Default: no reasoning.",
    )
    parser.add_argument(
        "--extractor-max-workers",
        type=int,
        default=7,
        help="Número máximo de workers paralelos para la extracción (default: 7)",
    )
    parser.add_argument(
        "--validation",
        nargs="*",
        default=None,
        help="Plugins de validación (default: core). Usa 'all' para todos. "
             "Ej: --validation core_quarter_sums fiba_player_fouls",
    )
    parser.add_argument(
        "--override-section",
        action="append",
        default=[],
        metavar="SECTION:PROVIDER:MODEL",
        help="Override extractor for a section. Ej: --override-section progressive_score:openrouter:google/gemini-3.5-flash",
    )
    parser.add_argument(
        "--override-reasoning-effort",
        default=None,
        choices=["xhigh", "high", "medium", "low", "minimal", "none"],
        help="Reasoning effort for override sections (OpenRouter only). Default: no reasoning.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emitir resultado en formato JSON estandarizado (para API / ocr-interface)",
    )
    parser.add_argument(
        "--grid-removal",
        choices=["inpaint", "handwriting"],
        default=None,
        help="Enable grid line removal on progressive_score section. "
             "'inpaint': morphological + cv2.inpaint. "
             "'handwriting': grid removal + restore handwritten marks.",
    )

    args = parser.parse_args()

    # Load .env
    load_dotenv(Path(__file__).resolve().parent / ".env")

    # Resolve image path
    image_arg = Path(args.image)
    image_path = image_arg if image_arg.is_absolute() else Path(__file__).resolve().parent / image_arg
    if not image_path.exists():
        exc = OcrEngineError(
            f"No existe la imagen: {image_path}",
            code="INPUT_IMAGE_NOT_FOUND",
            phase="input",
            retryable=False,
        )
        _output_error(exc, args.json_output)
        sys.exit(1)

    # Resolve output dir
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = Path(__file__).resolve().parent / output_dir

    # Build config
    validation_plugins: list[str] | str | None = None
    if args.validation is not None:
        if len(args.validation) == 1 and args.validation[0] == "all":
            validation_plugins = "all"
        else:
            validation_plugins = args.validation

    # Parse section overrides
    section_overrides = {}
    for override_spec in args.override_section:
        parts = override_spec.split(":", 2)
        if len(parts) != 3:
            print(f"Error: override-section format is SECTION:PROVIDER:MODEL, got: {override_spec}", file=sys.stderr)
            sys.exit(1)
        section_name, provider, model = parts
        reasoning = None
        if args.override_reasoning_effort:
            reasoning = {"effort": args.override_reasoning_effort, "exclude": True}
        section_overrides[section_name] = SectionOverride(
            provider=provider, model=model, reasoning=reasoning,
        )

    config = PipelineConfig(
        cropper_provider=args.cropper,
        cropper_model=args.cropper_model,
        extractor_provider=args.extractor,
        extractor_model=args.extractor_model,
        extractor_reasoning=(
            {"effort": args.extractor_reasoning_effort, "exclude": True}
            if args.extractor_reasoning_effort and args.extractor_reasoning_effort != "none"
            else None
        ),
        extractor_max_workers=args.extractor_max_workers,
        section_overrides=section_overrides,
        validation_plugins=validation_plugins,
        grid_removal=args.grid_removal or False,
    )

    # Run pipeline
    try:
        pipeline = FibaOcrPipeline(config)
        result = pipeline.process(image_path, output_dir=output_dir)

        # Save result
        if output_dir is None:
            output_dir = Path("outputs") / f"{image_path.stem}-sections"
        result_path = output_dir / "result.json"
        pipeline.save_result(result, result_path)

        _output_success(result, args.json_output)

    except OcrEngineError as exc:
        _output_error(exc, args.json_output)
        sys.exit(1)


if __name__ == "__main__":
    main()
