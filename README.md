# Cricket Pressure Performance Analytics — SupeRR Selector Season 2

This Windows-friendly project analyzes IPL 2022-2026 ball-by-ball data, reconstructs regulation-chase state, compares pressure and non-pressure performance, and creates an academic presentation. Original CSVs remain in `data/` and are never edited.

## Reproduce

From the project root in PowerShell:

```powershell
python -m venv .venv
& .venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

The complete run writes processed tables, reports, charts, rankings, an executable notebook and a PowerPoint into `outputs/`. The notebook calls the same pipeline rather than duplicating analytical logic.

## Method

- IPL competitions are isolated by their competition records; other T20/T20I data are not pooled into IPL estimates.
- Primary pressure states use eligible IPL regulation chases only. Abandoned/no-result matches, Super Overs, DLS/revised-resource matches and any match lacking innings 1 or 2 are excluded.
- Pre-delivery state uses only earlier deliveries. Target is reconstructed first-innings team runs + 1; required run rate is `runs_required * 6 / balls_remaining`.
- A delivery is marked as pressure when current required run rate exceeds the chase opening required rate. This is an observable pace deficit, not a psychological label or win probability.
- Batters need at least 30 pressure balls across 5 pressure innings. Bowlers need 60 classified pressure legal balls across 5 pressure innings. Rates shrink toward the cohort mean; composite components use equal-weight standardized values.
- Wides and `Overstep` are excluded from legal-ball counts. `other` is unresolved; the primary pressure state stops after its first occurrence in an innings, and alternate legality is tested. Bowling-runs outputs use confirmed extras only and include an alternate treatment for unknown extra labels.
- Death overs are the scheduled one-based `overid` 16-20, analyzed separately from pressure. Revised/shortened matches are excluded from that standard-innings comparison.
- No supervised ML is used because no auction-success or future-performance target exists. Exploratory K-Means profiles are reported only if silhouette separation is adequate.

## Important limits

No 2027 auction pool, RR retention/release state, purse, roster-slot constraints, player availability, or official 2027 auction regulations were supplied. The outputs are historical evidence and conditional role screens only; they do not assert that a player is available or recommend a price. See `outputs/reports/data_quality_report.md`, `analysis_summary.md` and `final_validation_report.md`.

## Structure

- `src/`: read-only pipeline, cricket state, ranking, reporting, charts, and presentation modules.
- `notebooks/cricket_pressure_analysis.ipynb`: executable notebook front-end.
- `outputs/processed/`: integrated deliveries, states, innings, player, team and coverage tables.
- `outputs/rankings/`: top-ten, complete eligible pressure rankings, and sensitivity tables.
- `outputs/charts/`: actual-data visualizations.
- `outputs/presentation/`: final PowerPoint.
- `outputs/reports/`: inspection, data-quality, analysis, progress and QA reports.
