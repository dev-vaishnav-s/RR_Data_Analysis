"""Markdown reporting for data quality and analytical results."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)) or pd.isna(value):
        return "—"
    if isinstance(value, (float, np.floating)):
        return f"{value:,.{digits}f}"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    return str(value)


def _md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    rows = [[_fmt(v, digits) for v in row] for row in df.itertuples(index=False, name=None)]
    return "| " + " | ".join(map(str, cols)) + " |\n| " + " | ".join(["---"]*len(cols)) + " |\n" + "\n".join("| " + " | ".join(row) + " |" for row in rows)


def write_data_quality_report(path: Path, raw: dict[str, pd.DataFrame], clean: dict[str, pd.DataFrame],
                              audit: dict, roster: pd.DataFrame, prep: dict,
                              integrated_rows: int) -> None:
    total_rows = sum(len(v) for v in raw.values())
    groups = audit["roster_duplicate_resolution"]["groups_by_status"]
    details = pd.DataFrame(audit["roster_duplicate_resolution"]["group_details"])
    dup_group = details.drop_duplicates(["match_id", "team_id", "player_id"])
    mapping = pd.DataFrame(audit["mapping_exceptions"])
    missing = pd.DataFrame(audit["missing_delivery_matches"])
    paths_table = []
    for name, df in raw.items():
        paths_table.append(f"| `{name}` | {len(df):,} | {len(df.columns)} | {int(df.duplicated().sum())} | {int(df.isna().sum().sum()):,} |")
    dup_table = []
    for _, row in dup_group.iterrows():
        cand = ", ".join(str(int(x)) for x in row.candidate_orders)
        obs = ", ".join(str(int(x)) for x in row.striker_observed_orders)
        dup_table.append(f"| {int(row.match_id)} | {int(row.team_id)} | {int(row.player_id)} | {cand} | {obs} | {row.resolution_status} |")
    match_table = []
    if not missing.empty:
        for _, r in missing.sort_values(["comp_name", "match_date"]).iterrows():
            match_table.append(f"| {int(r.match_id)} | {r.match_date} | {r.comp_name} | {r.home_team} vs {r.away_team} | {r.result} |")
    mapping_table = [f"| {int(r.match_id)} | {int(r.comp_id)} | {int(r.team_id)} | {int(r.player_id)} |" for r in mapping.itertuples()]
    text = f'''# Data Quality and Exception Handling Report

**Inspection source:** `outputs/reports/dataset_inspection_report.md` (initial and second-stage investigation)  
**Execution:** Reproducible Python pipeline; source CSVs were read-only.  
**Purpose:** Record implementation-time checks, treatment, and coverage limits. This report supplements rather than replaces the inspection report.

## Source inventory and before/after row counts

| Source table | Source rows | Source columns | Exact duplicate rows | Null cells |
|---|---:|---:|---:|---:|
{chr(10).join(paths_table)}

**Total raw rows:** {total_rows:,}. Cleaning is performed on in-memory copies. No source rows are removed. Text values are whitespace-trimmed only in analytical copies; categories/spelling variants are retained. Date/timestamp parsing adds derived columns rather than overwriting source strings. No exact duplicate rows were found, so no rows were dropped. Integrated deliveries: {integrated_rows:,}, equal to source delivery rows: {len(raw['ball_by_ball']):,}; validated match and competition joins did not multiply rows.

## Keys, relationships, and cleaning treatment

- Unique keys validated: `competitions.comp_id`, `matches.match_id`, `teams(comp_id, team_id)`, `competition_team_player_mapping(comp_id, team_id, player_id)`, and `ball_by_ball_updated(match_id, innings, innings_ball_num)`.
- Candidate delivery key `(match_id, innings, overid, over_ball_num)` is also unique in the source. The sequence field `innings_ball_num` counts recorded deliveries, not confirmed legal balls.
- Missing foreign references: `{json.dumps(audit['foreign_keys'], ensure_ascii=False)}`. Delivery integration is many-to-one to matches and competitions and many-to-one to competition-team labels. Player rosters were **not** joined onto delivery rows, avoiding row multiplication from the 35 repeated candidate keys.
- No invalid match or team-side references were found in source checks. Five roster-to-player-mapping misses are listed below and preserved.

## Playing-eleven duplicate groups

There are {audit['keys']['pe_duplicate_key_groups']} repeated `(match_id, team_id, player_id)` groups and {audit['keys']['pe_duplicate_excess_rows']} excess source rows. A striker-only delivery check is critical: in this feed, `ball_by_ball_updated.batting_order` tracks the striker's order; values seen while a player was the non-striker belong to the other batter and must not be used to resolve that player's roster row.

For **all {groups.get('order_corrob_by_striker_delivery', 0)} groups**, one unique observed striker order matched exactly one of that player's conflicting roster `batting_order` candidates. The pipeline therefore flags one corroborated roster row per group as the analytical selection and marks the other {audit['keys']['pe_duplicate_excess_rows']} rows `include_in_unique_roster_view=False`. All {len(details):,} duplicate-group source records remain in `playing_eleven_analytical.csv`, with source row numbers, candidate orders, observed striker orders, resolution status and selection flag. This is a transparent analytical view, not a destructive source correction; batting performance is calculated from deliveries, not from this roster selection.

The groups are exclusively in matches 13613, 21176 and 28962 (non-IPL T20Is). One-row-per-player roster views may use the striker-corroborated record for those groups. Original ambiguity remains documented because the delivery feed is corroboration, not an independent provider correction.

| Match | Team ID | Player ID | Roster candidate orders | Unique striker order | Treatment |
|---:|---:|---:|---|---|---|
{chr(10).join(dup_table)}

## Player mapping exceptions

All five rows are player 29833 (Bashir Ahmad), team 4444 (Afghanistan A), competition 2670 (Mens T20 Emerging Teams Asia Cup 2024), with `is_played=False` and null batting order/captain/wicketkeeper fields. His identity occurs under Afghanistan in other competitions. Preserve these as missing competition-team mapping rows; do not infer five appearances or reject the person ID.

| Match | Competition | Team | Player |
|---:|---:|---:|---:|
{chr(10).join(mapping_table)}

## Match coverage and exclusions

- All 16 matches with no ball-by-ball rows are marked `Match Abandoned`, with null winner. They remain in schedule coverage and do not contribute player delivery observations.
- IPL schedule: {audit['coverage']['ipl_match_records']} matches; delivery records in {audit['coverage']['ipl_matches_with_deliveries']}; no-delivery abandoned matches: {audit['coverage']['ipl_matches_without_deliveries']}.
- For primary pressure analysis, eligible regulation IPL matches: {prep['eligible_primary_matches']}; primary chase-state rows with valid pre-delivery state: {prep['state_valid_chase_deliveries']:,}; identified pressure deliveries (RRR above opening requirement): {prep['primary_pressure_deliveries']:,}.
- Competition-by-season coverage is saved separately. Non-IPL T20/T20I rows are not pooled into IPL performance or pressure rates.
- Primary exclusions are applied at match level: missing innings 1/2, no-result/abandoned, any revised overs or target, DLS result, or any Super Over. These conditions can overlap; the reason counts in the JSON below are not additive.
- There are four IPL matches without any delivery rows; exclusions with partial ball data are separately counted above.

### All matches without deliveries

| Match | Date | Competition | Fixture | Result |
|---:|---|---|---|---|
{chr(10).join(match_table)}

## Cricket-specific treatment and unresolved semantics

- Team total on a recorded delivery is `runs + extras1_runs + extras_2_runs`; it reproduces the stated margin in 399/399 observed non-DLS wins by runs. Player batting runs use `runs`.
- Batter balls faced exclude `wide` rows and include no-ball/`Overstep` rows. Bowler legal balls exclude `wide` and `Overstep`. `extras_type=other` is an unknown legality case: the primary chase-state path stops after its first occurrence in an innings, while a sensitivity path treats `other` as illegal. This prevents unverified legal-ball state from silently propagating.
- Bowler-conceded runs in the primary tables use batter runs plus known wide and `Overstep` extras. Byes/leg-byes and `extras_2_runs` are not charged. The 123 IPL `other` rows are excluded from bowler pressure-run/delivery rates; separate sensitivity totals include their `extras1_runs` and the second extras field. This is a provisional provider-dependent convention, not a verified definition.
- Bowler wickets use dismissal type (`Caught`, `Bowled`, `LBW`, `Stump`, `Hit Wicket`); `RunOut`, `Retire Out`, and obstruction are not credited. `is_wicket` is retained for wickets lost. One wicket row lacks a dismissed-player ID; 12 non-wicket rows contain a dismissed-player ID without a dismissal type.
- Revised-over values are preserved in original units; all are multiples of six and are strongly consistent with ball allocations. Revised/DLS matches are excluded from primary chase states. Six matches with innings 3/4 are identified as Super Overs and excluded from regulation rates.

## Primary pressure and ranking rules

- Population: IPL 2022-2026 only; regulation second innings with complete state; excludes abandoned/no-result, revised/DLS, and Super Overs. Other T20/T20I competitions are never pooled into IPL tables.
- State before delivery uses only prior records in the innings. Target is verified first-innings team total + 1. Standard allocation is 120 legal balls. `runs_required = target - score_before`; `RRR = runs_required * 6 / balls_remaining`; wickets remaining is ten less wickets lost.
- Pressure condition: `current RRR > opening RRR` (positive pressure margin). It means the chase is behind its opening required pace; it is a descriptive state, not win probability or a claim of psychological pressure.
- Batters: minimum 30 pressure balls and five pressure innings. Composite is an equal-weight mean of z-scores for shrinkage-adjusted strike rate, boundary-run share and dot avoidance. Rates shrink toward the eligible cohort average with 30 prior balls; published raw rates and workloads remain beside the composite.
- Bowlers: minimum 60 classified pressure legal balls and five pressure innings. Equal-weight z-score composite for lower shrinkage-adjusted economy, higher wicket rate per 100 balls and higher legal dot rate; rates shrink toward cohort average with 60 prior legal balls. Unknown `other` extras are excluded from pressure bowling rates.
- Sensitivity compares margin >0, margin >=2 runs/over, top-quartile positive margin, alternate `other` legality, and alternative metric weights. The rank is a cohort-relative academic summary, not an objective estimate of player quality.

## Before/after treatment summary

| Issue | Before | Analytical treatment | After / retained |
|---|---:|---|---:|
| Exact duplicate rows | 0 in six files | None removed | All source rows retained |
| Playing-eleven duplicate key groups | 35 groups / 40 excess rows | Add striker-order corroboration and explicit selection flag | All rows retained in analytical roster; one selected candidate per group |
| Mapping exceptions | 5 roster rows | Keep and flag as missing mapping | 5 retained |
| Matches without deliveries | 16 | Schedule-only coverage; no delivery metrics | 16 retained in match coverage table |
| IPL schedule matches | 371 | Separate IPL competition cohort | 367 have deliveries; 4 abandoned without deliveries |
| Integrated delivery rows | 200,999 | `m:1` validated context joins | 200,999 |
| IPL primary pressure cohort | 371 scheduled IPL matches | Exclude no-result/abandoned, revisions/DLS, super overs, and matches lacking innings 1/2 | {prep['eligible_primary_matches']} eligible matches |

## Run metadata

```json
{json.dumps({'audit_keys': audit['keys'], 'foreign_keys': audit['foreign_keys'], 'coverage': audit['coverage'], 'primary_exclusions': prep['excluded_primary_matches']}, indent=2, ensure_ascii=False, default=str)}
```
'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_analysis_report(path: Path, prep: dict, bat_ranks: pd.DataFrame, bowl_ranks: pd.DataFrame,
                          bat_sens: pd.DataFrame, bowl_sens: pd.DataFrame, ml_report: dict,
                          season: pd.DataFrame, rr_summary: pd.DataFrame, auction_text: str,
                          death_bat: pd.DataFrame, death_bowl: pd.DataFrame,
                          pressure_death_bat: pd.DataFrame, pressure_death_bowl: pd.DataFrame,
                          batter_consistency: pd.DataFrame, bowler_consistency: pd.DataFrame) -> None:
    def rank_table(df: pd.DataFrame, cols: list[str]) -> str:
        if df.empty: return "No player met the pre-registered minimum sample threshold."
        return _md_table(df.head(10)[cols])
    batcols=["rank","player_name","pressure_score","pressure_runs","pressure_balls","pressure_innings","pressure_dismissals","pressure_strike_rate","pressure_average","pressure_dot_pct"]
    bowlcols=["rank","player_name","pressure_score","pressure_legal_balls","pressure_innings","pressure_economy","pressure_wickets","pressure_wickets_per_100_balls","pressure_dot_pct"]
    text=f'''# Cricket Pressure Performance Analytics — Results Summary

## Scope and cautions

Historical IPL 2022-2026 data only. Primary pressure cohort has {prep['eligible_primary_matches']} regulation matches and {prep['primary_pressure_deliveries']:,} pre-delivery states labelled pressure. Other T20/T20I competitions are reported separately, not pooled into these rankings. The pressure condition is current required run rate above the opening required run rate. It measures a chase falling behind its initial pace, not psychological state or win probability.

The player composite is cohort-relative. Batters require at least 30 pressure balls across five pressure innings; bowlers require at least 60 classified pressure legal balls across five pressure innings. Batter strike rate and dot rate shrink to the eligible cohort mean using 30 prior balls; boundary-run share uses 300 prior batter runs. Bowler economy, wicket rate and dot rate use 60 prior legal balls. The components receive equal one-third weights after standardization. Bowler runs are provisional where `other` extras remain unresolved; see sensitivity and limitations below. Historical performance does not guarantee future results.

## Top pressure-performing batters

{rank_table(bat_ranks,batcols)}

## Top pressure-performing bowlers

{rank_table(bowl_ranks,bowlcols)}

## Sensitivity

Pressure threshold and legality variation are compared with the primary top ten. Low overlap indicates that a leaderboard should be interpreted as a screen, not a stable ordering. The complete scenario leaderboard and rank correlations are saved under `outputs/rankings/`.

**Batter scenarios:**

{_md_table(bat_sens) if not bat_sens.empty else "No sensitivity output."}

**Bowler scenarios:**

{_md_table(bowl_sens) if not bowl_sens.empty else "No sensitivity output."}

## Death-over performance (separate from pressure)

Death overs are scheduled one-based overs 16-20. Overall death leader screens require at least 30 balls across five death-over innings; the pressure-only screens require at least 20 batter balls or 30 bowler legal balls across three pressure-death innings.

**Overall death-over batters (by strike rate):**

{_md_table(death_bat.head(10)[["player_name","runs","balls","innings","strike_rate","boundary_run_share_pct","dot_pct"]]) if not death_bat.empty else "No batter met the death-over sample gate."}

**Overall death-over bowlers (by economy):**

{_md_table(death_bowl.head(10)[["player_name","legal_balls","innings","runs_conceded","wickets","economy","dot_pct"]]) if not death_bowl.empty else "No bowler met the death-over sample gate."}

**Death-over batting under identified pressure:**

{_md_table(pressure_death_bat.head(10)[["player_name","runs","balls","innings","strike_rate"]]) if not pressure_death_bat.empty else "No batter met the pressure-death sample gate."}

**Death-over bowling under identified pressure:**

{_md_table(pressure_death_bowl.head(10)[["player_name","legal_balls","innings","runs","wickets","economy"]]) if not pressure_death_bowl.empty else "No bowler met the pressure-death sample gate."}

## Consistency screens

These descriptive screens sort players by lower standard deviation in innings strike rate (batters) or innings economy (bowlers), after at least ten IPL innings. Low variance is not automatically high quality; read it with the mean rate and opportunity.

**Batters:**

{_md_table(batter_consistency.head(10)[["player_name","innings","balls","mean_strike_rate","sd_strike_rate","runs_cv_pct"]]) if not batter_consistency.empty else "No batter met the consistency gate."}

**Bowlers:**

{_md_table(bowler_consistency.head(10)[["player_name","innings","legal_balls","mean_economy","sd_economy"]]) if not bowler_consistency.empty else "No bowler met the consistency gate."}

## Season-level context

{_md_table(season) if not season.empty else "No season summary available."}

## Rajasthan Royals context and conditional recommendation

{_md_table(rr_summary) if not rr_summary.empty else "No Rajasthan Royals historical summary available."}

{auction_text}

## Machine learning

K-Means was tested only as an exploratory player-profile tool, separately for batters and bowlers, using scaled IPL performance rates and a minimum overall workload (150 batter balls / 120 bowler legal balls). The candidate cluster count was selected by silhouette score over k=2..5. No supervised model is used: the files contain no auction success or future performance target, and an auction recommendation target would be leakage-prone / unobserved.

```json
{json.dumps(ml_report, indent=2, ensure_ascii=False, default=str)}
```

## Limitations

- No verified 2027 auction pool, RR retention/squad state, purse, role-slot constraints, or player availability was supplied. No player is described as available for auction.
- No 2027 auction prices or budget recommendations are produced.
- `extras_type=other` and `extras_2_runs` semantics are not supplied. Some bowling rates are explicitly provisional and tested with alternate treatment.
- DLS/revised-target matches and Super Overs are excluded from primary pressure analysis; revised-over units appear to be balls but are not used.
- Minimum samples reduce small-opportunity noise but do not eliminate selection bias, role/venue/opposition differences, or historical-to-future uncertainty.
- The ranking composite is descriptive; weights, pressure cutoffs and cohort selection materially affect ranks.
'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

