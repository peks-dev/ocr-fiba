# Evaluation

Scripts for comparing `dataset/results*` outputs against ground-truth `ground_truth.json` files under `dataset/`.

For full documentation of flags and scoring behavior, see [docs/EVALUATION.md](../docs/EVALUATION.md).

## Quick usage

```bash
python evaluation/evaluate_dataset.py
python evaluation/evaluate_dataset.py --results-dir dataset/results-experiment
python evaluation/evaluate_dataset.py --sheet sheet-004 --verbose
```

## Focused evaluators

```bash
python evaluation/evaluate_header.py --results-dir dataset/results
python evaluation/evaluate_team_identity.py --results-dir dataset/results
python evaluation/evaluate_entry_marks.py --results-dir dataset/results
python evaluation/evaluate_player_points.py --results-dir dataset/results
python evaluation/evaluate_player_fouls.py --results-dir dataset/results
python evaluation/evaluate_progressive_score.py --results-dir dataset/results
```

All scripts accept `--sheet <sheet-XXX>`, `--results-dir <dir>`, `--verbose` (`-v`), and `--json`.
