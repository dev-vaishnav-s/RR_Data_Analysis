"""Transparent opportunity-adjusted pressure leaderboards and sensitivity checks."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


BATTER_MIN_BALLS = 30
BATTER_MIN_INNINGS = 5
BOWLER_MIN_BALLS = 60
BOWLER_MIN_INNINGS = 5


def _z(series: pd.Series) -> pd.Series:
    sd = series.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / sd


def rank_batters(d: pd.DataFrame, pressure_col: str = "pressure_primary",
                 threshold_name: str = "primary", weights: tuple[float, float, float] = (1/3, 1/3, 1/3)) -> pd.DataFrame:
    x = d[d.is_ipl & d[pressure_col] & ~d.is_wide].copy()
    if x.empty:
        return pd.DataFrame()
    x["boundary_runs"] = x.runs.where(x.is_four | x.is_six, 0)
    x["dot"] = x.team_runs.eq(0)
    g = x.groupby(["striker_id", "striker_name"], dropna=False).agg(
        pressure_runs=("runs", "sum"), pressure_balls=("match_id", "size"),
        boundary_runs=("boundary_runs", "sum"), dot_balls=("dot", "sum"),
        pressure_deliveries=("match_id", "size"),
    ).reset_index().rename(columns={"striker_id": "player_id", "striker_name": "player_name"})
    outs = d[d.is_ipl & d[pressure_col] & d.is_wicket & d.dismissed_player_id.notna()].groupby("dismissed_player_id").size()
    g["pressure_dismissals"] = g.player_id.map(outs).fillna(0).astype(int)
    inns = x[["striker_id", "match_id", "innings"]].drop_duplicates().groupby("striker_id").size()
    g["pressure_innings"] = g.player_id.map(inns).fillna(0).astype(int)
    g["pressure_strike_rate"] = np.where(g.pressure_balls.gt(0), 100*g.pressure_runs/g.pressure_balls, np.nan)
    g["pressure_average"] = np.where(g.pressure_dismissals.gt(0), g.pressure_runs/g.pressure_dismissals, np.nan)
    g["pressure_boundary_run_share_pct"] = np.where(g.pressure_runs.gt(0), 100*g.boundary_runs/g.pressure_runs, np.nan)
    g["pressure_dot_pct"] = np.where(g.pressure_balls.gt(0), 100*g.dot_balls/g.pressure_balls, np.nan)
    cohort_sr = 100*x.runs.sum()/len(x)
    cohort_boundary = 100*x.boundary_runs.sum()/max(1, x.runs.sum())
    cohort_dot = 100*x.team_runs.eq(0).sum()/len(x)
    k = 30.0
    g["sr_adjusted"] = (g.pressure_runs*100 + k*cohort_sr)/(g.pressure_balls+k)
    g["boundary_share_adjusted"] = (g.boundary_runs*100 + 300*cohort_boundary)/(g.pressure_runs+300)
    g["dot_pct_adjusted"] = (g.dot_balls*100 + k*cohort_dot)/(g.pressure_balls+k)
    eligible = g.pressure_balls.ge(BATTER_MIN_BALLS) & g.pressure_innings.ge(BATTER_MIN_INNINGS)
    g["eligible_for_ranking"] = eligible
    e = g[eligible].copy()
    if e.empty:
        return g
    e["z_pressure_sr"] = _z(e.sr_adjusted)
    e["z_boundary_share"] = _z(e.boundary_share_adjusted)
    e["z_dot_avoidance"] = _z(-e.dot_pct_adjusted)
    w = np.asarray(weights, dtype=float); w = w/w.sum()
    e["pressure_score"] = w[0]*e.z_pressure_sr + w[1]*e.z_boundary_share + w[2]*e.z_dot_avoidance
    e = e.sort_values(["pressure_score", "pressure_balls", "pressure_runs"], ascending=False).reset_index(drop=True)
    e.insert(0, "rank", np.arange(1, len(e)+1))
    e["ranking_threshold"] = threshold_name
    return e


def rank_bowlers(d: pd.DataFrame, pressure_col: str = "pressure_primary",
                 threshold_name: str = "primary", weights: tuple[float, float, float] = (1/3, 1/3, 1/3),
                 other_charged: bool = False, extra2_charged: bool = False) -> pd.DataFrame:
    x = d[d.is_ipl & d[pressure_col] & ~d.extras_type.eq("other")].copy()
    if x.empty:
        return pd.DataFrame()
    runs_col = "bowler_runs_primary"
    if other_charged:
        runs_col = "bowler_runs_other_charged"
    if extra2_charged:
        runs_col = "bowler_runs_other_and_extra2_charged"
    x["runs_for_metric"] = x[runs_col]
    x["legal_dot"] = x.legal_ball_base & x.team_runs.eq(0)
    g = x.groupby(["bowler_id", "bowler_name"], dropna=False).agg(
        pressure_legal_balls=("legal_ball_base", "sum"), pressure_runs_conceded=("runs_for_metric", "sum"),
        pressure_wickets=("bowler_wicket", "sum"), pressure_dots=("legal_dot", "sum"),
        pressure_deliveries=("match_id", "size"),
    ).reset_index().rename(columns={"bowler_id": "player_id", "bowler_name": "player_name"})
    innings = x[["bowler_id", "match_id", "innings"]].drop_duplicates().groupby("bowler_id").size()
    g["pressure_innings"] = g.player_id.map(innings).fillna(0).astype(int)
    g["pressure_economy"] = np.where(g.pressure_legal_balls.gt(0), 6*g.pressure_runs_conceded/g.pressure_legal_balls, np.nan)
    g["pressure_wickets_per_100_balls"] = np.where(g.pressure_legal_balls.gt(0), 100*g.pressure_wickets/g.pressure_legal_balls, np.nan)
    g["pressure_strike_rate"] = np.where(g.pressure_wickets.gt(0), g.pressure_legal_balls/g.pressure_wickets, np.nan)
    g["pressure_dot_pct"] = np.where(g.pressure_legal_balls.gt(0), 100*g.pressure_dots/g.pressure_legal_balls, np.nan)
    bound = (x.is_four | x.is_six).groupby(x.bowler_id).sum()
    g["pressure_boundary_balls"] = g.player_id.map(bound).fillna(0).astype(int)
    g["pressure_boundary_pct"] = np.where(g.pressure_legal_balls.gt(0),100*g.pressure_boundary_balls/g.pressure_legal_balls,np.nan)
    cohort_econ = 6*x[runs_col].sum()/max(1,int(x.legal_ball_base.sum()))
    cohort_wkt = 100*x.bowler_wicket.sum()/max(1,int(x.legal_ball_base.sum()))
    cohort_dot = 100*(x.legal_ball_base & x.team_runs.eq(0)).sum()/max(1,int(x.legal_ball_base.sum()))
    k = 60.0
    g["economy_adjusted"] = (g.pressure_runs_conceded*6 + cohort_econ*k)/(g.pressure_legal_balls+k)
    g["wicket_rate_adjusted"] = (g.pressure_wickets*100 + cohort_wkt*k)/(g.pressure_legal_balls+k)
    g["dot_pct_adjusted"] = (g.pressure_dots*100 + cohort_dot*k)/(g.pressure_legal_balls+k)
    eligible = g.pressure_legal_balls.ge(BOWLER_MIN_BALLS) & g.pressure_innings.ge(BOWLER_MIN_INNINGS)
    g["eligible_for_ranking"] = eligible
    e = g[eligible].copy()
    if e.empty:
        return g
    e["z_economy"] = _z(-e.economy_adjusted)
    e["z_wicket_rate"] = _z(e.wicket_rate_adjusted)
    e["z_dot_rate"] = _z(e.dot_pct_adjusted)
    w = np.asarray(weights, dtype=float); w = w/w.sum()
    e["pressure_score"] = w[0]*e.z_economy + w[1]*e.z_wicket_rate + w[2]*e.z_dot_rate
    e = e.sort_values(["pressure_score", "pressure_legal_balls", "pressure_wickets"], ascending=False).reset_index(drop=True)
    e.insert(0, "rank", np.arange(1, len(e)+1))
    e["ranking_threshold"] = threshold_name
    e["bowler_runs_sensitivity"] = "confirmed extras only; other-type rows excluded"
    return e


def rank_sensitivity(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Base pressure = RRR has risen above the chase opening requirement. Alternatives:
    # +2 runs/over margin; upper quartile of observed valid state margins; alternate 'other' legality.
    valid_margins = d.loc[d.state_valid_primary & d.pressure_margin.gt(0), "pressure_margin"].dropna()
    q75 = float(valid_margins.quantile(.75)) if len(valid_margins) else float("nan")
    d = d.copy()
    d["pressure_q75"] = d.state_valid_primary & d.pressure_margin.ge(q75)
    scenarios = [
        ("primary_margin_gt_0", "pressure_primary"),
        ("margin_at_least_2", "pressure_alt_margin_2"),
        (f"valid_state_top_quartile_margin_{q75:.3f}", "pressure_q75"),
        ("other_extras_treated_illegal", "pressure_other_illegal"),
    ]
    bat_rows, bowl_rows = [], []
    primary_bat = primary_bowl = None
    for name, col in scenarios:
        b = rank_batters(d, col, name)
        w = rank_bowlers(d, col, name)
        if name == "primary_margin_gt_0":
            primary_bat, primary_bowl = b, w
        for frame, out, role in [(b, bat_rows, "batter"), (w, bowl_rows, "bowler")]:
            if not frame.empty:
                tmp = frame.head(10)[["player_id", "player_name", "rank", "pressure_score"]].copy()
                tmp["scenario"] = name; tmp["role"] = role
                out.extend(tmp.to_dict("records"))
    sens = pd.DataFrame(bat_rows + bowl_rows)
    def compare(primary: pd.DataFrame, scenario: pd.DataFrame, label: str, role: str) -> dict:
        if primary is None or scenario.empty:
            return {"scenario": label, "role": role, "top10_overlap": 0, "spearman_rank_correlation": np.nan}
        p = primary[["player_id", "rank"]].rename(columns={"rank": "rank_primary"})
        q = scenario[["player_id", "rank"]].rename(columns={"rank": "rank_scenario"})
        joined = p.merge(q, on="player_id", how="inner")
        rho = spearmanr(joined.rank_primary, joined.rank_scenario).statistic if len(joined) >= 3 else np.nan
        return {"scenario": label, "role": role, "top10_overlap": int(len(set(primary.head(10).player_id)&set(scenario.head(10).player_id))),
                "spearman_rank_correlation": float(rho) if pd.notna(rho) else np.nan,
                "eligible_primary": int(primary.eligible_for_ranking.sum()), "eligible_scenario": int(scenario.eligible_for_ranking.sum())}
    checks = []
    if primary_bat is not None and primary_bowl is not None:
        for name, col in scenarios[1:]:
            checks.append(compare(primary_bat, rank_batters(d,col,name), name, "batter"))
            checks.append(compare(primary_bowl, rank_bowlers(d,col,name), name, "bowler"))
        # Score-weight sensitivity on the primary cohort.
        checks.append(compare(primary_bat, rank_batters(d,"pressure_primary","scoring_first",(.50,.30,.20)), "scoring_first_weights", "batter"))
        checks.append(compare(primary_bowl, rank_bowlers(d,"pressure_primary","wicket_first",(.30,.50,.20)), "wicket_first_weights", "bowler"))
    return sens, pd.DataFrame(checks), d

