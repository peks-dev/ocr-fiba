[← Back to README](../README.md) | [← Codebase Guide](CODEBASE-GUIDE.md)

# Dataset Evaluation

**Use `evaluation/` scripts to measure OCR extraction accuracy against labeled `ground_truth.json` files under `dataset/`.**

Evaluation scripts live outside `packages/` and operate strictly on saved output JSON directories (by default `dataset/results/` compared against `dataset/sheet-001` through `dataset/sheet-010`).

## Main full-sheet evaluator

```bash
python evaluation/evaluate_dataset.py
```

Evaluate an experimental results directory or a single sheet:

```bash
python evaluation/evaluate_dataset.py --results-dir dataset/results-experiment
python evaluation/evaluate_dataset.py --sheet sheet-004 --verbose
python evaluation/evaluate_dataset.py --json
```

Note on scoring: in `evaluate_dataset.py`, extra keys present in `result.json` that do not exist in `ground_truth.json` are logged as `extra_in_result` but do **not** count as mismatches in accuracy calculation.

## Focused domain evaluators

All evaluators share `--sheet <sheet_id>`, `--results-dir <dir>`, `--verbose` (`-v`), and `--json`:

| Script | Scope | What it measures |
|---|---|---|
| `evaluation/evaluate_dataset.py` | Full scoresheet (`sheet-001`..`sheet-010`) | Per-field matches/mismatches, per-section accuracy %, and global summary. |
| `evaluation/evaluate_header.py` | `header` | Match info fields against ground truth. |
| `evaluation/evaluate_team_identity.py` | `team_a`, `team_b` | `team.name`, `captain`, `players[].name`, and `players[].number`. |
| `evaluation/evaluate_entry_marks.py` | `players[]` | Player `entered` and `started` marks against ground truth. |
| `evaluation/evaluate_player_points.py` | `players[]` | Per-player total points and shot breakdown accuracy. |
| `evaluation/evaluate_player_fouls.py` | `players[].fouls` | Separates exact code mismatches (`P` vs `P1`), family mismatches, and list alignment/length mismatches. |
| `evaluation/evaluate_progressive_score.py` | `progressive_score` | Set accuracy on `running_score` and `player_number` accuracy for matched scores (avoids index-cascade noise). |

Examples:

```bash
python evaluation/evaluate_progressive_score.py --results-dir dataset/results --sheet sheet-007 --verbose
python evaluation/evaluate_player_fouls.py --results-dir dataset/results --sheet sheet-004
python evaluation/evaluate_entry_marks.py --results-dir dataset/results
python evaluation/evaluate_team_identity.py --results-dir dataset/results
python evaluation/evaluate_player_points.py --results-dir dataset/results
python evaluation/evaluate_header.py --results-dir dataset/results
```

## Generating results to evaluate

Use the CLI dataset runner (`ocr-dataset`, implemented in `packages/cli/src/ocr_engine_cli/run_dataset.py`) to produce batch outputs, then score them with the evaluators above. Never commit runtime results under `dataset/results*`.

---

[← Core Pipeline](codebase/core-pipeline.md) | [Codebase Guide →](CODEBASE-GUIDE.md)
