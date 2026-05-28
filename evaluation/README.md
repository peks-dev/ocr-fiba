# Evaluation

Scripts para comparar `dataset/results` contra los `ground_truth.json` del dataset.

Uso principal:

```bash
python evaluation/evaluate_dataset.py
```

Para evaluar un directorio de resultados experimental:

```bash
python evaluation/evaluate_dataset.py --results-dir dataset/results-experiment
```

Evaluadores especificos:

```bash
python evaluation/evaluate_progressive_score.py --results-dir dataset/results
python evaluation/evaluate_player_fouls.py --results-dir dataset/results
python evaluation/evaluate_entry_marks.py --results-dir dataset/results
python evaluation/evaluate_team_identity.py --results-dir dataset/results
python evaluation/evaluate_player_points.py --results-dir dataset/results
python evaluation/evaluate_header.py --results-dir dataset/results
```

Todos aceptan `--sheet sheet-XXX` para evaluar una sola hoja.
