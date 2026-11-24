"""Cricket-state reconstruction and IPL performance summaries."""
from __future__ import annotations

import numpy as np
import pandas as pd


IPL_PATTERN = r"^IPL \d{4}$"
NON_RESULT = r"abandoned|no result"
DISMISSAL_CREDITED = {"Caught", "Bowled", "LBW", "Stump", "Hit Wicket"}


def prepare_analysis(tables: dict[str, pd.DataFrame], integrated: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    matches = tables["matches"].merge(tables["competitions"], on="comp_id", validate="m:1")
    ipl_matches = matches[matches.comp_name.str.match(IPL_PATTERN, na=False)].copy()
    d = integrated[integrated.is_ipl].copy()
    d = d.sort_values(["match_id", "innings", "innings_ball_num"], kind="stable").reset_index(drop=True)
    d["is_no_ball_candidate"] = d.extras_type.eq("Overstep")
    d["is_wide"] = d.extras_type.eq("wide")
    d["is_unknown_extra_type"] = d.extras_type.eq("other") | (
        d.extras_type.isna() & (d.extras1_runs.ne(0) | d.extras_2_runs.ne(0))
    )
    d["team_runs"] = d.runs + d.extras1_runs + d.extras_2_runs
    d["legal_ball_base"] = ~(d.is_wide | d.is_no_ball_candidate)
    d["legal_ball_other_illegal"] = d.legal_ball_base & ~d.extras_type.eq("other")
    d["bowler_runs_primary"] = d.runs + d.extras1_runs.where(d.extras_type.isin(["wide", "Overstep"]), 0)
    d["bowler_runs_other_charged"] = d.bowler_runs_primary + d.extras1_runs.where(d.extras_type.eq("other"), 0)
    d["bowler_runs_other_and_extra2_charged"] = d.bowler_runs_other_charged + d.extras_2_runs
    d["bowler_wicket"] = d.is_wicket & d.dismissal_type.isin(DISMISSAL_CREDITED)
    d["batter_ball"] = ~d.is_wide  # Scorecard balls faced exclude wides; no-balls count as faced.
    d["batter_boundary_runs"] = d.runs.where(d.is_four | d.is_six, 0)
    d["team_dot"] = d.team_runs.eq(0)
    d["batter_dot"] = d.batter_ball & d.team_dot

    inn = d.groupby(["match_id", "innings"], sort=False)
    d["score_before"] = inn.team_runs.cumsum() - d.team_runs
    d["wickets_before"] = inn.is_wicket.cumsum().astype(int) - d.is_wicket.astype(int)
    d["legal_balls_before"] = inn.legal_ball_base.cumsum().astype(int) - d.legal_ball_base.astype(int)
    d["legal_balls_before_other_illegal"] = inn.legal_ball_other_illegal.cumsum().astype(int) - d.legal_ball_other_illegal.astype(int)
    # Unknown 'other' status makes later ball counts uncertain. Keep the state through
    # the first such delivery's pre-delivery state, then flag the remaining state.
    d["unknown_extra_seen_before"] = inn.is_unknown_extra_type.cumsum().astype(int) - d.is_unknown_extra_type.astype(int)
    d["match_has_revised_state"] = d["first_inn_revised_overs"].notna() | d["second_inn_revised_overs"].notna() | d["revised_target"].notna()
    d["match_has_super_over"] = d.match_id.isin(set(d.loc[d.innings.ge(3), "match_id"]))
    d["match_is_no_result"] = d.result.str.contains(NON_RESULT, case=False, na=False)
    d["match_is_tie_superover"] = d.result.str.contains(r"tied|super over", case=False, na=False)
    # A chase is primary-eligible only with a regulation two-innings structure,
    # no revised allocation/target, no DLS/no-result, and no Super Over.
    innings_counts = d.groupby("match_id").innings.agg(lambda x: set(x.unique()))
    result_map = matches.set_index("match_id").result
    revised_map = matches.set_index("match_id").apply(
        lambda r: pd.notna(r.first_inn_revised_overs) or pd.notna(r.second_inn_revised_overs) or pd.notna(r.revised_target), axis=1
    )
    dls_map = result_map.str.contains(r"D/L|DLS", case=False, na=False)
    noresult_map = result_map.str.contains(NON_RESULT, case=False, na=False)
    super_map = d.loc[d.innings.ge(3), "match_id"].drop_duplicates().set_index(d.loc[d.innings.ge(3), "match_id"].drop_duplicates()).index if False else set(d.loc[d.innings.ge(3), "match_id"])
    eligible = {}
    excluded_reasons: dict[int, str] = {}
    for mid in d.match_id.unique():
        reasons = []
        iset = innings_counts.get(mid, set())
        if not {1, 2}.issubset(iset): reasons.append("missing_innings_1_or_2")
        if revised_map.get(mid, False): reasons.append("revised_target_or_overs")
        if dls_map.get(mid, False): reasons.append("DLS_result")
        if noresult_map.get(mid, False): reasons.append("abandoned_or_no_result")
        if mid in super_map: reasons.append("super_over")
        eligible[mid] = not reasons
        if reasons: excluded_reasons[mid] = ";".join(reasons)
    d["primary_match_eligible"] = d.match_id.map(eligible).fillna(False)
    d["primary_exclusion_reason"] = d.match_id.map(excluded_reasons).fillna("")
    first_totals = d[d.innings.eq(1)].groupby("match_id").team_runs.sum()
    d["target"] = d.match_id.map(first_totals + 1).where(d.innings.eq(2))
    d["runs_required"] = (d.target - d.score_before).clip(lower=0)
    d["balls_remaining"] = (120 - d.legal_balls_before).clip(lower=0)
    d["balls_remaining_other_illegal"] = (120 - d.legal_balls_before_other_illegal).clip(lower=0)
    d["wickets_remaining"] = (10 - d.wickets_before).clip(lower=0)
    d["required_run_rate"] = np.where(
        d.balls_remaining.gt(0) & d.runs_required.gt(0), d.runs_required * 6 / d.balls_remaining, np.nan
    )
    d["required_run_rate_other_illegal"] = np.where(
        d.balls_remaining_other_illegal.gt(0) & d.runs_required.gt(0),
        d.runs_required * 6 / d.balls_remaining_other_illegal, np.nan
    )
    d["opening_required_run_rate"] = d.target * 6 / 120
    d["pressure_margin"] = d.required_run_rate - d.opening_required_run_rate
    d["pressure_margin_other_illegal"] = d.required_run_rate_other_illegal - d.opening_required_run_rate
    d["state_valid_primary"] = (
        d.primary_match_eligible & d.innings.eq(2) & d.unknown_extra_seen_before.eq(0)
        & d.runs_required.gt(0) & d.balls_remaining.gt(0)
    )
    d["pressure_primary"] = d.state_valid_primary & d.pressure_margin.gt(1e-12)
    d["pressure_alt_margin_2"] = d.state_valid_primary & d.pressure_margin.ge(2.0)
    d["state_valid_other_illegal"] = (
        d.primary_match_eligible & d.innings.eq(2) & d.runs_required.gt(0)
        & d.balls_remaining_other_illegal.gt(0)
    )
    d["pressure_other_illegal"] = d.state_valid_other_illegal & d.pressure_margin_other_illegal.gt(1e-12)
    return d, {
        "ipl_matches": int(len(ipl_matches)),
        "ipl_matches_with_deliveries": int(d.match_id.nunique()),
        "ipl_delivery_rows": int(len(d)),
        "eligible_primary_matches": int(sum(eligible.values())),
        "excluded_primary_matches": {reason: int(sum(reason in v for v in excluded_reasons.values())) for reason in sorted({x for v in excluded_reasons.values() for x in v.split(";")})},
        "eligible_match_ids": [int(k) for k, v in eligible.items() if v],
        "excluded_match_reasons": {int(k): v for k, v in excluded_reasons.items()},
        "primary_pressure_deliveries": int(d.pressure_primary.sum()),
        "state_valid_chase_deliveries": int(d.state_valid_primary.sum()),
        "other_extra_delivery_rows": int(d.is_unknown_extra_type.sum()),
    }


def _name_lookup(d: pd.DataFrame, id_col: str, name_col: str) -> dict[int, str]:
    s = d[[id_col, name_col]].dropna().copy()
    return s.groupby(id_col)[name_col].agg(lambda x: x.value_counts().index[0]).to_dict()


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num.div(den.replace(0, np.nan))


def batting_summaries(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ipl = d[d.is_ipl].copy()
    ipl["batter_name"] = ipl.striker_name
    # One row per batter per innings for workload/consistency. A wide is not a ball faced.
    striker = ipl[ipl.batter_ball].copy()
    group = ["striker_id"]
    overall = striker.groupby(group).agg(
        runs=("runs", "sum"), balls_faced=("batter_ball", "sum"),
        boundary_runs=("batter_boundary_runs", "sum"), boundary_balls=("is_four", "sum"),
        dot_balls=("team_dot", "sum"), total_deliveries=("match_id", "size"),
    )
    sixes = striker[striker.is_six].groupby("striker_id").size()
    fours = striker[striker.is_four].groupby("striker_id").size()
    overall["boundary_balls"] = fours.add(sixes, fill_value=0)
    dismissals = ipl[ipl.is_wicket & ipl.dismissed_player_id.notna()].groupby("dismissed_player_id").size()
    overall["dismissals"] = dismissals
    innings_counts = pd.concat([
        ipl[["match_id", "innings", "striker_id"]].rename(columns={"striker_id": "player_id"}),
        ipl[["match_id", "innings", "non_striker_id"]].rename(columns={"non_striker_id": "player_id"}),
    ]).drop_duplicates().groupby("player_id").size()
    overall["innings"] = innings_counts
    overall["strike_rate"] = _safe_ratio(overall.runs * 100, overall.balls_faced)
    overall["batting_average"] = _safe_ratio(overall.runs, overall.dismissals)
    overall["boundary_ball_pct"] = _safe_ratio(overall.boundary_balls * 100, overall.balls_faced)
    overall["boundary_run_share_pct"] = _safe_ratio(overall.boundary_runs * 100, overall.runs)
    overall["dot_ball_pct"] = _safe_ratio(overall.dot_balls * 100, overall.balls_faced)
    overall["dismissal_rate_per_100_balls"] = _safe_ratio(overall.dismissals * 100, overall.balls_faced)
    names = _name_lookup(ipl, "striker_id", "striker_name")
    overall.insert(0, "player_name", overall.index.map(names))
    overall.index.name = "player_id"
    overall = overall.reset_index()
    overall_innings = striker.groupby(["striker_id", "match_id", "innings"]).agg(
        runs=("runs", "sum"), balls=("batter_ball", "sum")
    ).reset_index()
    overall_innings["innings_strike_rate"] = _safe_ratio(overall_innings.runs * 100, overall_innings.balls)
    bat_consistency = overall_innings.groupby("striker_id").agg(
        overall_innings_count=("innings", "size"), overall_innings_sr_sd=("innings_strike_rate", "std"),
        overall_innings_runs_sd=("runs", "std"), overall_innings_runs_mean=("runs", "mean"),
    ).reset_index().rename(columns={"striker_id": "player_id"})
    bat_consistency["overall_innings_runs_cv_pct"] = _safe_ratio(
        bat_consistency.overall_innings_runs_sd * 100, bat_consistency.overall_innings_runs_mean
    )
    overall = overall.merge(bat_consistency, on="player_id", how="left", validate="1:1")

    pressure = striker[striker.pressure_primary].copy()
    p = pressure.groupby("striker_id").agg(
        pressure_runs=("runs", "sum"), pressure_balls=("batter_ball", "sum"),
        pressure_boundary_runs=("batter_boundary_runs", "sum"), pressure_dots=("team_dot", "sum"),
        pressure_innings=("innings", lambda s: int(pressure.loc[s.index, ["match_id", "innings"]].drop_duplicates().shape[0])),
    )
    pb = pressure[pressure.is_four | pressure.is_six].groupby("striker_id").size()
    p["pressure_boundary_balls"] = pb
    p["pressure_strike_rate"] = _safe_ratio(p.pressure_runs * 100, p.pressure_balls)
    p["pressure_boundary_ball_pct"] = _safe_ratio(p.pressure_boundary_balls * 100, p.pressure_balls)
    p["pressure_boundary_run_share_pct"] = _safe_ratio(p.pressure_boundary_runs * 100, p.pressure_runs)
    p["pressure_dot_pct"] = _safe_ratio(p.pressure_dots * 100, p.pressure_balls)
    pressure_wicket_ids = d[d.is_ipl & d.pressure_primary & d.is_wicket & d.dismissed_player_id.notna()].groupby("dismissed_player_id").size()
    p["pressure_dismissals"] = pd.Series(p.index, index=p.index).map(pressure_wicket_ids).fillna(0).astype(int)
    p["pressure_average"] = _safe_ratio(p.pressure_runs, p.pressure_dismissals)
    p["pressure_dismissal_rate_per_100_balls"] = _safe_ratio(p.pressure_dismissals * 100, p.pressure_balls)
    p.index.name = "player_id"
    p = p.reset_index().rename(columns={"striker_id": "player_id"})
    p.insert(1, "player_name", p.player_id.map(names))

    # Role cues from striker rows only: batting_order is the striker's order in this feed.
    order = ipl.groupby("striker_id").batting_order.median().rename("median_striker_order")
    roles = order.map(lambda v: "Top order (1-3)" if v <= 3 else ("Middle order (4-6)" if v <= 6 else "Lower order (7+)")).rename("batting_role")
    role_df = pd.concat([order, roles], axis=1).reset_index().rename(columns={"striker_id": "player_id"})
    overall = overall.merge(role_df, on="player_id", how="left", validate="1:1")
    # Pressure innings consistency from per-player pressure strike rates.
    pi = pressure.groupby(["striker_id", "match_id", "innings"]).agg(
        runs=("runs", "sum"), balls=("batter_ball", "sum")
    ).reset_index()
    pi["innings_strike_rate"] = _safe_ratio(pi.runs * 100, pi.balls)
    consistency = pi.groupby("striker_id").innings_strike_rate.agg(
        pressure_innings_sr_sd="std", pressure_innings_count="count"
    ).reset_index().rename(columns={"striker_id": "player_id"})
    p = p.merge(consistency, on="player_id", how="left", validate="1:1")
    return overall, p, pi


def bowling_summaries(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ipl = d[d.is_ipl].copy()
    all_balls = ipl.copy()
    all_balls["legal_dot"] = all_balls.legal_ball_base & all_balls.team_runs.eq(0)
    overall = all_balls.groupby("bowler_id").agg(
        legal_balls=("legal_ball_base", "sum"), runs_conceded=("bowler_runs_primary", "sum"),
        runs_conceded_other_charged=("bowler_runs_other_charged", "sum"),
        runs_conceded_other_and_extra2_charged=("bowler_runs_other_and_extra2_charged", "sum"),
        wickets=("bowler_wicket", "sum"), deliveries=("match_id", "size"),
        dot_balls=("legal_dot", "sum"),
    )
    # Boundaries are batter boundaries recorded on the delivery, not extras.
    bound = (all_balls.is_four | all_balls.is_six).groupby(all_balls.bowler_id).sum()
    overall["boundary_balls_conceded"] = bound
    overall["overs"] = overall.legal_balls / 6
    overall["economy"] = _safe_ratio(overall.runs_conceded * 6, overall.legal_balls)
    overall["bowling_strike_rate"] = _safe_ratio(overall.legal_balls, overall.wickets)
    overall["dot_ball_pct"] = _safe_ratio(overall.dot_balls * 100, overall.legal_balls)
    overall["boundary_ball_pct"] = _safe_ratio(overall.boundary_balls_conceded * 100, overall.deliveries)
    names = _name_lookup(ipl, "bowler_id", "bowler_name")
    overall.insert(0, "player_name", overall.index.map(names))
    overall.index.name = "player_id"
    overall = overall.reset_index()
    bowler_innings_all = all_balls.groupby(["bowler_id", "match_id", "innings"]).agg(
        legal_balls=("legal_ball_base", "sum"), runs=("bowler_runs_primary", "sum"),
        wickets=("bowler_wicket", "sum")
    ).reset_index()
    bowler_innings_all["innings_economy"] = _safe_ratio(bowler_innings_all.runs * 6, bowler_innings_all.legal_balls)
    bowl_consistency = bowler_innings_all[bowler_innings_all.legal_balls.gt(0)].groupby("bowler_id").agg(
        overall_bowling_innings=("innings", "size"), overall_innings_economy_sd=("innings_economy", "std"),
        overall_innings_runs_sd=("runs", "std"),
    ).reset_index().rename(columns={"bowler_id": "player_id"})
    overall = overall.merge(bowl_consistency, on="player_id", how="left", validate="1:1")
    style = ipl.groupby("bowler_id").agg(
        bowling_type=("bowling_type", lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"),
        pace_or_spin=("pace_or_spin", lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"),
    ).reset_index().rename(columns={"bowler_id": "player_id"})
    overall = overall.merge(style, on="player_id", how="left", validate="1:1")
    # Pressure events have valid pre-delivery chase states; exclude unresolved 'other'
    # extras from bowler run and delivery denominators in the confirmed-runs view.
    pressure = ipl[ipl.pressure_primary].copy()
    pressure_known = pressure[~pressure.extras_type.eq("other")]
    p = pressure_known.groupby("bowler_id").agg(
        pressure_legal_balls=("legal_ball_base", "sum"), pressure_runs_conceded=("bowler_runs_primary", "sum"),
        pressure_runs_other_charged=("bowler_runs_other_charged", "sum"),
        pressure_runs_other_and_extra2_charged=("bowler_runs_other_and_extra2_charged", "sum"),
        pressure_wickets=("bowler_wicket", "sum"), pressure_deliveries=("match_id", "size"),
        pressure_dots=("team_dot", "sum"), pressure_innings=("innings", lambda s: int(pressure_known.loc[s.index, ["match_id", "innings"]].drop_duplicates().shape[0])),
    )
    p["pressure_economy"] = _safe_ratio(p.pressure_runs_conceded * 6, p.pressure_legal_balls)
    p["pressure_strike_rate"] = _safe_ratio(p.pressure_legal_balls, p.pressure_wickets)
    p["pressure_wickets_per_100_balls"] = _safe_ratio(p.pressure_wickets * 100, p.pressure_legal_balls)
    p["pressure_dot_pct"] = _safe_ratio(p.pressure_dots * 100, p.pressure_legal_balls)
    p["pressure_boundary_balls"] = (pressure_known.is_four | pressure_known.is_six).groupby(pressure_known.bowler_id).sum()
    p["pressure_boundary_ball_pct"] = _safe_ratio(p.pressure_boundary_balls * 100, p.pressure_deliveries)
    p.index.name = "player_id"
    p = p.reset_index().rename(columns={"bowler_id": "player_id"})
    p.insert(1, "player_name", p.player_id.map(names))
    pi = pressure_known.groupby(["bowler_id", "match_id", "innings"]).agg(
        legal_balls=("legal_ball_base", "sum"), runs=("bowler_runs_primary", "sum"), wickets=("bowler_wicket", "sum")
    ).reset_index()
    pi["economy"] = _safe_ratio(pi.runs * 6, pi.legal_balls)
    consistency = pi.groupby("bowler_id").economy.agg(
        pressure_innings_economy_sd="std", pressure_innings_count="count"
    ).reset_index().rename(columns={"bowler_id": "player_id"})
    p = p.merge(consistency, on="player_id", how="left", validate="1:1")
    return overall, p, pi


def pressure_events(d: pd.DataFrame) -> pd.DataFrame:
    keep = d[d.pressure_primary].copy()
    columns = ["match_id", "comp_name", "season", "match_date", "innings", "innings_ball_num", "overid",
               "striker_id", "striker_name", "bowler_id", "bowler_name", "batting_team_name", "bowling_team_name",
               "score_before", "target", "runs_required", "balls_remaining", "wickets_remaining",
               "required_run_rate", "opening_required_run_rate", "pressure_margin", "runs", "extras_type",
               "extras1_runs", "extras_2_runs", "delivery_total_runs", "is_wicket", "dismissal_type", "bowler_creditable_wicket"]
    return keep[columns].sort_values(["match_id", "innings_ball_num"]).reset_index(drop=True)


def summarize_ipl(tables: dict[str, pd.DataFrame], d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    m = tables["matches"].merge(tables["competitions"], on="comp_id", validate="m:1")
    im = m[m.comp_name.str.match(IPL_PATTERN, na=False)].copy()
    # Standard regulation innings: exclude every match with revised resources/target,
    # DLS/no-result/abandoned, or a Super Over. Death overs use one-based overid 16-20.
    revise = im.first_inn_revised_overs.notna() | im.second_inn_revised_overs.notna() | im.revised_target.notna()
    dls = im.result.str.contains(r"D/L|DLS", case=False, na=False)
    noresult = im.result.str.contains(NON_RESULT, case=False, na=False)
    super_ids = set(d.loc[d.innings.ge(3), "match_id"])
    im["death_eligible"] = ~(revise | dls | noresult | im.match_id.isin(super_ids))
    eligible_ids = set(im.loc[im.death_eligible, "match_id"])
    death = d[d.match_id.isin(eligible_ids) & d.innings.le(2) & d.overid.between(16, 20)].copy()
    return {"ipl_matches": im, "death_deliveries": death}


def quality_metrics(d: pd.DataFrame, audit: dict) -> dict:
    ipl = d[d.is_ipl]
    byres = ipl.groupby("result", dropna=False).match_id.nunique().to_dict()
    primary_ids = set(d.loc[d.primary_match_eligible, "match_id"])
    primary = d[d.match_id.isin(primary_ids)]
    return {
        "ipl_match_results": byres,
        "primary_match_count": int(len(primary_ids)),
        "primary_delivery_rows": int(len(primary)),
        "primary_pressure_delivery_rows": int(primary.pressure_primary.sum()),
        "primary_state_valid_rows": int(primary.state_valid_primary.sum()),
        "other_extra_rows_ipl": int(ipl.extras_type.eq("other").sum()),
        "nonzero_extra2_ipl": int(ipl.extras_2_runs.ne(0).sum()),
        "no_ball_candidate_rows_ipl": int(ipl.extras_type.eq("Overstep").sum()),
        "wide_rows_ipl": int(ipl.extras_type.eq("wide").sum()),
        "innings_3_4_ipl": ipl[ipl.innings.ge(3)].groupby("innings").size().to_dict(),
    }

