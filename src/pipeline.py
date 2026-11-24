"""End-to-end reproducible project build."""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .data_pipeline import (
    ROOT, OUT, audit_data, clean_analytical_copies, integrate_deliveries,
    load_inputs, resolve_playing_eleven, sha256,
)
from .cricket_analysis import (
    batting_summaries, bowling_summaries, prepare_analysis, pressure_events,
    summarize_ipl,
)
from .ml_profiles import cluster_profiles
from .ranking_analysis import rank_batters, rank_bowlers, rank_sensitivity
from .reporting import write_analysis_report, write_data_quality_report
from .visualization import create_charts, create_team_chart
from .presentation import create_deck


def _safe_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _name_mode(s: pd.Series) -> str:
    v=s.dropna().mode()
    return str(v.iloc[0]) if len(v) else "Unknown"


def _make_summaries(tables: dict, d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    # Innings accounting includes the Super Over rows in a separate marked table.
    innings = d.groupby(["match_id", "comp_name", "season", "match_date", "innings", "batting_team_id", "batting_team_name"], dropna=False).agg(
        delivery_rows=("match_id", "size"), team_runs=("delivery_total_runs", "sum"),
        wickets_lost=("is_wicket", "sum"), legal_balls_candidate=("legal_ball_base", "sum"),
        legal_balls_other_illegal=("legal_ball_alt_other_illegal", "sum"),
        unknown_other_rows=("is_unknown_extra_type", "sum"),
    ).reset_index()
    innings["overs_candidate"] = innings.legal_balls_candidate/6
    innings["runs_per_over"] = np.where(innings.legal_balls_candidate.gt(0), innings.team_runs*6/innings.legal_balls_candidate, np.nan)
    innings["is_super_over"] = innings.innings.ge(3)
    normal = innings[~innings.is_super_over]
    season = normal.groupby("season").agg(
        innings=("match_id", "size"), matches=("match_id", "nunique"),
        mean_innings_runs=("team_runs", "mean"), median_innings_runs=("team_runs", "median"),
        mean_runs_per_over=("runs_per_over", "mean"), mean_wickets_lost=("wickets_lost", "mean"),
    ).reset_index().sort_values("season")
    match_flags=d[["match_id","comp_name","season","result","primary_match_eligible","primary_exclusion_reason"]].drop_duplicates("match_id")
    # Team-level performance excludes Super Overs so a two-over tie-breaker cannot distort rates.
    regular = d[d.innings.le(2)]
    team = regular.groupby(["batting_team_id","batting_team_name"]).agg(
        delivery_rows=("match_id","size"), matches=("match_id","nunique"), runs=("team_runs","sum"),
        wickets_lost=("is_wicket","sum"), legal_balls=("legal_ball_base","sum"),
    ).reset_index()
    team_innings=regular[["batting_team_id","match_id","innings"]].drop_duplicates().groupby("batting_team_id").size()
    team["innings"]=team.batting_team_id.map(team_innings)
    team["runs_per_wicket"] = np.where(team.wickets_lost.gt(0), team.runs/team.wickets_lost, np.nan)
    team["runs_per_over"] = np.where(team.legal_balls.gt(0), team.runs*6/team.legal_balls, np.nan)
    team=team.sort_values("runs_per_wicket",ascending=False)
    phase=regular.groupby(["season","scheduled_over_phase"]).agg(
        deliveries=("match_id","size"), runs=("team_runs","sum"), legal_balls=("legal_ball_base","sum"),
        wickets=("is_wicket","sum"), fours=("is_four","sum"), sixes=("is_six","sum"),
    ).reset_index()
    phase["boundaries"]=phase.fours+phase.sixes
    phase["runs_per_over"] = np.where(phase.legal_balls.gt(0),phase.runs*6/phase.legal_balls,np.nan)
    phase["wickets_per_120_balls"] = np.where(phase.legal_balls.gt(0),phase.wickets*120/phase.legal_balls,np.nan)
    # RR historical pressure exposure (not a current-squad gap assessment).
    p=d[d.pressure_primary]
    rr_b=p[p.batting_team_name.eq("Rajasthan Royals")]
    rr_w=p[p.bowling_team_name.eq("Rajasthan Royals") & ~p.extras_type.eq("other")]
    rr_summary=pd.DataFrame([
        {"view":"RR batting in eligible chases","pressure_events":len(rr_b),"matches":rr_b.match_id.nunique(),"runs_or_conceded":int(rr_b.runs.sum()),"balls_or_legal_balls":int((~rr_b.is_wide).sum()),"rate_per_100_or_economy":100*rr_b.runs.sum()/max(1,(~rr_b.is_wide).sum()),"wickets":int(rr_b.dismissed_player_id.notna().sum())},
        {"view":"RR bowling in eligible chases","pressure_events":len(rr_w),"matches":rr_w.match_id.nunique(),"runs_or_conceded":int(rr_w.bowler_runs_primary.sum()),"balls_or_legal_balls":int(rr_w.legal_ball_base.sum()),"rate_per_100_or_economy":6*rr_w.bowler_runs_primary.sum()/max(1,int(rr_w.legal_ball_base.sum())),"wickets":int(rr_w.bowler_wicket.sum())},
    ])
    return {"innings":innings,"season":season,"teams":team,"phase":phase,"match_flags":match_flags,"rr_summary":rr_summary}


def _death_metrics(death: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    bat=death[~death.is_wide].copy()
    db=bat.groupby(["striker_id","striker_name"]).agg(
        runs=("runs","sum"),balls=("batter_ball","sum"),boundary_runs=("batter_boundary_runs","sum"),
        dots=("team_dot","sum"),deliveries=("match_id","size"),
    ).reset_index().rename(columns={"striker_id":"player_id","striker_name":"player_name"})
    db["innings"]=db.player_id.map(bat[["striker_id","match_id","innings"]].drop_duplicates().groupby("striker_id").size())
    db["strike_rate"]=np.where(db.balls.gt(0),100*db.runs/db.balls,np.nan)
    db["boundary_run_share_pct"]=np.where(db.runs.gt(0),100*db.boundary_runs/db.runs,np.nan)
    db["dot_pct"]=np.where(db.balls.gt(0),100*db.dots/db.balls,np.nan)
    db= db.sort_values("strike_rate",ascending=False)
    legaldot=death.legal_ball_base & death.team_runs.eq(0)
    d=death.assign(legal_dot=legaldot)
    dw=d.groupby(["bowler_id","bowler_name"]).agg(
        legal_balls=("legal_ball_base","sum"),runs_conceded=("bowler_runs_primary","sum"),
        wickets=("bowler_wicket","sum"),dots=("legal_dot","sum"),deliveries=("match_id","size"),
    ).reset_index().rename(columns={"bowler_id":"player_id","bowler_name":"player_name"})
    dw["innings"]=dw.player_id.map(d[["bowler_id","match_id","innings"]].drop_duplicates().groupby("bowler_id").size())
    dw["overs"]=dw.legal_balls/6
    dw["economy"]=np.where(dw.legal_balls.gt(0),dw.runs_conceded*6/dw.legal_balls,np.nan)
    dw["strike_rate"]=np.where(dw.wickets.gt(0),dw.legal_balls/dw.wickets,np.nan)
    dw["dot_pct"]=np.where(dw.legal_balls.gt(0),100*dw.dots/dw.legal_balls,np.nan)
    dw=dw.sort_values("economy")
    press=death[death.pressure_primary]
    pb=press[~press.is_wide].groupby(["striker_id","striker_name"]).agg(runs=("runs","sum"),balls=("batter_ball","sum")).reset_index().rename(columns={"striker_id":"player_id","striker_name":"player_name"})
    pb["innings"]=pb.player_id.map(press.loc[~press.is_wide,["striker_id","match_id","innings"]].drop_duplicates().groupby("striker_id").size())
    pb["strike_rate"]=np.where(pb.balls.gt(0),100*pb.runs/pb.balls,np.nan)
    pressb=press[~press.extras_type.eq("other")]
    pw=pressb.groupby(["bowler_id","bowler_name"]).agg(legal_balls=("legal_ball_base","sum"),runs=("bowler_runs_primary","sum"),wickets=("bowler_wicket","sum")).reset_index().rename(columns={"bowler_id":"player_id","bowler_name":"bowler_name"})
    pw=pw.rename(columns={"bowler_name":"player_name"})
    pw["innings"]=pw.player_id.map(pressb[["bowler_id","match_id","innings"]].drop_duplicates().groupby("bowler_id").size())
    pw["economy"]=np.where(pw.legal_balls.gt(0),pw.runs*6/pw.legal_balls,np.nan)
    return db,dw,pb,pw


def _consistency_tables(d: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    x=d[d.is_ipl & d.innings.le(2)]
    bat=x[~x.is_wide].groupby(["striker_id","striker_name","match_id","innings"]).agg(
        runs=("runs","sum"),balls=("batter_ball","sum")
    ).reset_index()
    bat["innings_sr"]=np.where(bat.balls.gt(0),100*bat.runs/bat.balls,np.nan)
    bs=bat.groupby(["striker_id","striker_name"]).agg(
        innings=("innings","size"),balls=("balls","sum"),mean_runs=("runs","mean"),sd_runs=("runs","std"),
        mean_strike_rate=("innings_sr","mean"),sd_strike_rate=("innings_sr","std"),
    ).reset_index().rename(columns={"striker_id":"player_id","striker_name":"player_name"})
    bs["runs_cv_pct"]=np.where(bs.mean_runs.gt(0),100*bs.sd_runs/bs.mean_runs,np.nan)
    bs=bs[bs.innings.ge(10)].sort_values(["sd_strike_rate","innings"],ascending=[True,False])
    bowl=x.groupby(["bowler_id","bowler_name","match_id","innings"]).agg(
        legal_balls=("legal_ball_base","sum"),runs=("bowler_runs_primary","sum"),
    ).reset_index()
    bowl=bowl[bowl.legal_balls.gt(0)]
    bowl["innings_economy"]=6*bowl.runs/bowl.legal_balls
    ws=bowl.groupby(["bowler_id","bowler_name"]).agg(
        innings=("innings","size"),legal_balls=("legal_balls","sum"),mean_economy=("innings_economy","mean"),
        sd_economy=("innings_economy","std"),
    ).reset_index().rename(columns={"bowler_id":"player_id","bowler_name":"player_name"})
    ws=ws[ws.innings.ge(10)].sort_values(["sd_economy","innings"],ascending=[True,False])
    return bs,ws


def _category_tables(raw: dict[str,pd.DataFrame]) -> tuple[pd.DataFrame,pd.DataFrame]:
    profile=[]; values=[]
    for table,df in raw.items():
        for col in df.columns:
            if df[col].dtype==object or pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_bool_dtype(df[col]):
                vc=df[col].value_counts(dropna=False)
                cats=["<NULL>" if pd.isna(v) else str(v) for v in vc.index]
                profile.append({"table":table,"column":col,"dtype":str(df[col].dtype),"unique_including_null":int(df[col].nunique(dropna=False)),"null_count":int(df[col].isna().sum()),"category_values_if_le_60":" | ".join(cats) if len(vc)<=60 else "high-cardinality; inspect source schema"})
                if len(vc)<=60:
                    for v,n in vc.items():
                        values.append({"table":table,"column":col,"value":"<NULL>" if pd.isna(v) else str(v),"count":int(n)})
    return pd.DataFrame(profile),pd.DataFrame(values)


def _write_readme() -> None:
    text='''# Cricket Pressure Performance Analytics — SupeRR Selector Season 2

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
'''
    (ROOT/"README.md").write_text(text,encoding="utf-8")


def _write_requirements() -> None:
    text='''pandas>=2.2
numpy>=1.26
matplotlib>=3.8
seaborn>=0.13
scikit-learn>=1.4
scipy>=1.11
python-pptx>=0.6.23
nbformat>=5.9
nbclient>=0.10
'''
    (ROOT/"requirements.txt").write_text(text,encoding="utf-8")


def _write_notebook() -> None:
    import nbformat as nbf
    nb=nbf.v4.new_notebook()
    nb.cells=[
        nbf.v4.new_markdown_cell("# Cricket Pressure Performance Analytics — SupeRR Selector Season 2\n\nThis notebook is a reproducible front end to the modular pipeline. It preserves the source CSVs and writes all analytical outputs under `outputs/`."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport sys\nPROJECT_ROOT = Path.cwd()\nif not (PROJECT_ROOT / 'data').exists():\n    PROJECT_ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'data').exists())\nsys.path.insert(0, str(PROJECT_ROOT))\nfrom src.pipeline import run_pipeline\nresults = run_pipeline()\nprint(f\"Eligible IPL matches: {results['prep']['eligible_primary_matches']}\")\nprint(f\"Pressure deliveries: {results['prep']['primary_pressure_deliveries']:,}\")\nprint(f\"Original CSVs unchanged: {results['source_hashes_unchanged']}\")"),
        nbf.v4.new_code_cell("from IPython.display import display\ndisplay(results['top_bat'][['rank','player_name','pressure_score','pressure_balls','pressure_strike_rate']])\ndisplay(results['top_bowl'][['rank','player_name','pressure_score','pressure_legal_balls','pressure_economy']])"),
        nbf.v4.new_markdown_cell("## Reproducibility notes\n\nThe output reports document pressure, scoring and ranking definitions, sensitivity checks, exclusions, and limits on 2027 auction recommendations. No supervised model is used because no suitable target variable is present."),
    ]
    nb.metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":platform.python_version()}}
    path=ROOT/"notebooks"/"cricket_pressure_analysis.ipynb";path.parent.mkdir(parents=True,exist_ok=True)
    nbf.write(nb,path)


def run_pipeline() -> dict:
    start=datetime.now(timezone.utc).isoformat()
    raw,manifest=load_inputs()
    audit,_=audit_data(raw)
    category_profile,category_values=_category_tables(raw)
    tables=clean_analytical_copies(raw)
    roster=resolve_playing_eleven(tables)
    integrated=integrate_deliveries(tables)
    d,prep=prepare_analysis(tables,integrated)
    summary=_make_summaries(tables,d)
    batter,bat_pressure,bat_innings=batting_summaries(d)
    bowler,bowl_pressure,bowl_innings=bowling_summaries(d)
    sensitivity,sensitivity_checks,sensitivity_state=rank_sensitivity(d)
    top_bat=rank_batters(d).head(10).copy()
    top_bowl=rank_bowlers(d).head(10).copy()
    # Attach roles and overall context for readable leaderboards.
    top_bat=top_bat.merge(batter[["player_id","batting_role","strike_rate","batting_average","innings"]],on="player_id",how="left",validate="1:1")
    top_bowl=top_bowl.merge(bowler[["player_id","bowling_type","pace_or_spin","economy","wickets","legal_balls"]],on="player_id",how="left",validate="1:1")
    # Full pressure tables get overall and consistency fields when available.
    bat_pressure=bat_pressure.merge(batter[["player_id","batting_role","strike_rate","batting_average","innings"]],on="player_id",how="left",validate="1:1")
    bowl_pressure=bowl_pressure.merge(bowler[["player_id","bowling_type","pace_or_spin","economy","legal_balls"]],on="player_id",how="left",validate="1:1")
    ipl_summaries=summarize_ipl(tables,d)
    death_bat,death_bowl,death_pressure_bat,death_pressure_bowl=_death_metrics(ipl_summaries["death_deliveries"])
    batter_consistency,bowler_consistency=_consistency_tables(d)
    death_bat_leaders=death_bat[(death_bat.balls>=30)&(death_bat.innings>=5)].nlargest(10,"strike_rate")
    death_bowl_leaders=death_bowl[(death_bowl.legal_balls>=30)&(death_bowl.innings>=5)].nsmallest(10,"economy")
    death_pressure_bat_leaders=death_pressure_bat[(death_pressure_bat.balls>=20)&(death_pressure_bat.innings>=3)].nlargest(10,"strike_rate")
    death_pressure_bowl_leaders=death_pressure_bowl[(death_pressure_bowl.legal_balls>=30)&(death_pressure_bowl.innings>=3)].nsmallest(10,"economy")
    clusters,ml_report=cluster_profiles(batter,bowler)
    events=pressure_events(d)
    # Merge pressure consistency onto overall batters/bowlers for comparison tables.
    batting_compare=batter.merge(bat_pressure[["player_id","pressure_runs","pressure_balls","pressure_innings","pressure_strike_rate","pressure_average","pressure_boundary_run_share_pct","pressure_dot_pct","pressure_innings_sr_sd"]],on="player_id",how="left",validate="1:1")
    bowling_compare=bowler.merge(bowl_pressure[["player_id","pressure_legal_balls","pressure_runs_conceded","pressure_innings","pressure_economy","pressure_wickets","pressure_wickets_per_100_balls","pressure_dot_pct","pressure_innings_economy_sd"]],on="player_id",how="left",validate="1:1")
    # Name/role summaries for conditional historical RR screening only.
    rr_bat=top_bat.head(5)[["player_name","batting_role","pressure_score","pressure_balls","pressure_strike_rate"]].copy()
    rr_bowl=top_bowl.head(5)[["player_name","bowling_type","pace_or_spin","pressure_score","pressure_legal_balls","pressure_economy"]].copy()
    recommended_batters=", ".join(rr_bat.player_name.astype(str).tolist()) or "none qualified"
    recommended_bowlers=", ".join(rr_bowl.player_name.astype(str).tolist()) or "none qualified"
    auction_text=(
        "**Conditional historical screen, not an availability claim:** use role-fit evidence to check pressure batters "
        f"({recommended_batters}) and pressure bowlers ({recommended_bowlers}) against the official 2027 auction pool, "
        "verified availability, RR retention list and purse once those records exist. The data does not establish current squad gaps, "
        "auction eligibility or affordability, so these names are research leads only. Profile-first priorities are a reliable top-order "
        "chase batter, a middle/death finisher, and a bowler who combines pressure dot-ball control with wickets; current RR roster needs must be verified."
    )

    proc=OUT/"processed"; ranks=OUT/"rankings"; reports=OUT/"reports"
    proc.mkdir(parents=True,exist_ok=True); ranks.mkdir(parents=True,exist_ok=True); reports.mkdir(parents=True,exist_ok=True)
    _safe_csv(integrated,proc/"integrated_delivery_dataset.csv")
    _safe_csv(d,proc/"delivery_state_analytics.csv")
    _safe_csv(roster,proc/"playing_eleven_analytical.csv")
    dup=roster[roster.candidate_key_group_size.gt(1)]
    _safe_csv(dup,proc/"playing_eleven_duplicate_exceptions.csv")
    mapping_exc=pd.DataFrame(audit["mapping_exceptions"])
    _safe_csv(mapping_exc,proc/"player_mapping_exceptions.csv")
    _safe_csv(summary["match_flags"],proc/"ipl_match_coverage_and_eligibility.csv")
    _safe_csv(summary["innings"],proc/"ipl_innings_summary.csv")
    _safe_csv(summary["season"],proc/"ipl_season_summary.csv")
    _safe_csv(summary["teams"],proc/"ipl_team_summary.csv")
    _safe_csv(summary["phase"],proc/"ipl_phase_summary.csv")
    _safe_csv(summary["rr_summary"],proc/"rajasthan_royals_historical_pressure_summary.csv")
    _safe_csv(category_profile,proc/"categorical_field_profile.csv")
    _safe_csv(category_values,proc/"categorical_value_counts.csv")
    all_matches=tables["matches"].merge(tables["competitions"],on="comp_id",validate="m:1")
    match_delivery_counts=integrated.groupby("match_id").size().rename("delivery_rows")
    all_matches=all_matches.join(match_delivery_counts,on="match_id")
    all_matches["delivery_rows"]=all_matches.delivery_rows.fillna(0).astype(int)
    coverage=all_matches.groupby(["comp_name","match_format","season"]).agg(
        scheduled_matches=("match_id","nunique"),matches_with_deliveries=("delivery_rows",lambda x:int((x>0).sum())),
        delivery_rows=("delivery_rows","sum"),
    ).reset_index()
    coverage["matches_without_deliveries"]=coverage.scheduled_matches-coverage.matches_with_deliveries
    non_ipl_coverage=coverage[~coverage.comp_name.str.match(r"^IPL \d{4}$",na=False)].copy()
    _safe_csv(coverage,proc/"competition_coverage_by_season.csv")
    _safe_csv(non_ipl_coverage,proc/"non_ipl_competition_coverage.csv")
    _safe_csv(batter,proc/"ipl_batter_performance.csv")
    _safe_csv(bat_pressure,proc/"ipl_batter_pressure_performance.csv")
    _safe_csv(batting_compare,proc/"ipl_batter_overall_vs_pressure.csv")
    _safe_csv(bowler,proc/"ipl_bowler_performance.csv")
    _safe_csv(bowl_pressure,proc/"ipl_bowler_pressure_performance.csv")
    _safe_csv(bowling_compare,proc/"ipl_bowler_overall_vs_pressure.csv")
    _safe_csv(death_bat,proc/"ipl_death_over_batting.csv")
    _safe_csv(death_bowl,proc/"ipl_death_over_bowling.csv")
    _safe_csv(death_pressure_bat,proc/"ipl_death_over_pressure_batting.csv")
    _safe_csv(death_pressure_bowl,proc/"ipl_death_over_pressure_bowling.csv")
    _safe_csv(batter_consistency,proc/"ipl_batter_consistency.csv")
    _safe_csv(bowler_consistency,proc/"ipl_bowler_consistency.csv")
    _safe_csv(events,proc/"ipl_pressure_delivery_events.csv")
    _safe_csv(clusters,proc/"exploratory_player_clusters.csv")
    _safe_csv(top_bat,ranks/"top_10_pressure_batters.csv")
    _safe_csv(top_bowl,ranks/"top_10_pressure_bowlers.csv")
    _safe_csv(rank_batters(d),ranks/"pressure_batter_rankings_all_eligible.csv")
    _safe_csv(rank_bowlers(d),ranks/"pressure_bowler_rankings_all_eligible.csv")
    _safe_csv(sensitivity,ranks/"pressure_ranking_sensitivity_top10.csv")
    _safe_csv(sensitivity_checks,ranks/"pressure_ranking_sensitivity_checks.csv")
    _safe_csv(rr_bat,OUT/"rankings"/"conditional_rr_batter_screen.csv")
    _safe_csv(rr_bowl,OUT/"rankings"/"conditional_rr_bowler_screen.csv")
    _safe_csv(death_bat_leaders,ranks/"top_death_over_batters.csv")
    _safe_csv(death_bowl_leaders,ranks/"top_death_over_bowlers.csv")
    _safe_csv(death_pressure_bat_leaders,ranks/"top_pressure_death_over_batters.csv")
    _safe_csv(death_pressure_bowl_leaders,ranks/"top_pressure_death_over_bowlers.csv")

    chartpaths=create_charts(OUT/"charts",d,batter,bat_pressure,bowler,bowl_pressure,top_bat,top_bowl,
                             death_bat,death_bowl,summary["innings"],summary["season"],summary["phase"],
                             death_pressure_bat,death_pressure_bowl,sensitivity_checks)
    chartpaths += create_team_chart(OUT/"charts",summary["teams"])
    write_data_quality_report(reports/"data_quality_report.md",raw,tables,audit,roster,prep,len(integrated))
    write_analysis_report(reports/"analysis_summary.md",prep,top_bat,top_bowl,
                          sensitivity_checks[sensitivity_checks.role.eq("batter")],
                          sensitivity_checks[sensitivity_checks.role.eq("bowler")],ml_report,
                          summary["season"],summary["rr_summary"],auction_text,
                          death_bat_leaders,death_bowl_leaders,death_pressure_bat_leaders,death_pressure_bowl_leaders,
                          batter_consistency.head(10),bowler_consistency.head(10))
    # Manifest written only after outputs; all source hashes are recomputed and compared.
    current={f:sha256(ROOT/"data"/f) for f in manifest["inputs"]}
    unchanged=all(current[f]==manifest["inputs"][f]["sha256"] for f in current)
    manifest["source_hashes_after_run"]=current
    manifest["source_hashes_unchanged"]=unchanged
    manifest["execution"]={"started_utc":start,"finished_utc":datetime.now(timezone.utc).isoformat(),"python":sys.version,"platform":platform.platform(),"integrated_delivery_rows":len(integrated),"primary_eligible_matches":prep["eligible_primary_matches"]}
    (OUT/"processed"/"input_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    _write_requirements(); _write_readme(); _write_notebook()
    # Presentation receives only computed outputs and real chart files.
    deck=OUT/"presentation"/"cricket_pressure_analytics_presentation.pptx"
    create_deck(deck, chartpaths, prep, top_bat, top_bowl, sensitivity_checks, ml_report,
                summary["season"],summary["rr_summary"],death_bat_leaders,death_bowl_leaders,
                death_pressure_bat_leaders,death_pressure_bowl_leaders,batter_consistency.head(10),bowler_consistency.head(10),auction_text)
    result={"prep":prep,"top_bat":top_bat,"top_bowl":top_bowl,"sensitivity":sensitivity_checks,
            "ml":ml_report,"charts":[str(x.relative_to(ROOT)) for x in chartpaths],"source_hashes_unchanged":unchanged,
            "integrated_rows":len(integrated),"presentation":str(deck.relative_to(ROOT))}
    (OUT/"processed"/"run_summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
    return result

