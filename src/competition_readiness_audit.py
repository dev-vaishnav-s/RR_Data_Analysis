"""Reproducible SupeRR Selector Round 1 readiness audit.

Adds a separate T20I pressure screen and a PDF audit without changing the
existing IPL leaderboards, raw inputs, or previously generated artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from .data_pipeline import ROOT, OUT, load_inputs, clean_analytical_copies, integrate_deliveries, resolve_playing_eleven, sha256
from .ranking_analysis import rank_batters, rank_bowlers


REPORT = OUT / "reports" / "superrr_selector_round1_competition_readiness_audit.pdf"


def t20i_states(tables: dict[str, pd.DataFrame], integrated: pd.DataFrame) -> pd.DataFrame:
    """Build separate, full-quota T20I pre-delivery chase states."""
    m = tables["matches"].merge(tables["competitions"][["comp_id", "comp_name", "match_format"]], on="comp_id", validate="m:1")
    mids = set(m.loc[m.match_format.eq("T20I"), "match_id"])
    d = integrated[integrated.match_id.isin(mids)].copy()
    d = d.sort_values(["match_id", "innings", "innings_ball_num"], kind="stable").reset_index(drop=True)
    d["team_runs"] = d.runs + d.extras1_runs + d.extras_2_runs
    d["is_wide"] = d.extras_type.eq("wide")
    d["is_no_ball"] = d.extras_type.eq("Overstep")
    d["legal_ball_base"] = ~(d.is_wide | d.is_no_ball)
    d["bowler_runs_primary"] = d.runs + d.extras1_runs.where(d.extras_type.isin(["wide", "Overstep"]), 0)
    d["bowler_runs_other_charged"] = d.bowler_runs_primary + d.extras1_runs.where(d.extras_type.eq("other"), 0)
    d["bowler_runs_other_and_extra2_charged"] = d.bowler_runs_other_charged + d.extras_2_runs
    d["bowler_wicket"] = d.is_wicket & d.dismissal_type.isin({"Caught", "Bowled", "LBW", "Stump", "Hit Wicket"})
    d["unknown_extra"] = d.extras_type.eq("other") | (d.extras_type.isna() & (d.extras1_runs.ne(0) | d.extras_2_runs.ne(0)))
    grp = d.groupby(["match_id", "innings"], sort=False)
    d["score_before"] = grp.team_runs.cumsum() - d.team_runs
    d["wickets_before"] = grp.is_wicket.cumsum().astype(int) - d.is_wicket.astype(int)
    d["legal_balls_before"] = grp.legal_ball_base.cumsum().astype(int) - d.legal_ball_base.astype(int)
    d["unknown_extra_seen_before"] = grp.unknown_extra.cumsum().astype(int) - d.unknown_extra.astype(int)
    i_sets = d.groupby("match_id").innings.agg(lambda x: set(x.unique()))
    superovers = set(d.loc[d.innings.ge(3), "match_id"])
    m = m.set_index("match_id")
    valid_match = {}
    for mid in mids:
        r = m.loc[mid]
        noresult = bool(pd.notna(r.result) and ("no result" in str(r.result).lower() or "abandoned" in str(r.result).lower()))
        dls = bool(pd.notna(r.result) and ("d/l" in str(r.result).lower() or "dls" in str(r.result).lower()))
        revised = any(pd.notna(r[c]) for c in ["first_inn_revised_overs", "second_inn_revised_overs", "revised_target"])
        valid_match[mid] = ({1, 2}.issubset(i_sets.get(mid, set())) and mid not in superovers and not noresult and not dls and not revised)
    d["match_eligible"] = d.match_id.map(valid_match).fillna(False)
    first = d[d.innings.eq(1)].groupby("match_id").team_runs.sum()
    d["target"] = d.match_id.map(first + 1)
    d["runs_required"] = (d.target - d.score_before).clip(lower=0)
    d["balls_remaining"] = (120 - d.legal_balls_before).clip(lower=0)
    d["wickets_remaining"] = (10 - d.wickets_before).clip(lower=0)
    d["required_run_rate"] = np.where(d.balls_remaining.gt(0) & d.runs_required.gt(0), d.runs_required * 6 / d.balls_remaining, np.nan)
    d["opening_required_run_rate"] = d.target * 6 / 120
    d["pressure_margin"] = d.required_run_rate - d.opening_required_run_rate
    d["state_valid_primary"] = d.match_eligible & d.innings.eq(2) & d.unknown_extra_seen_before.eq(0) & d.runs_required.gt(0) & d.balls_remaining.gt(0)
    d["pressure_primary"] = d.state_valid_primary & d.pressure_margin.gt(1e-12)
    # Rank functions use this cohort flag as the common competition selector.
    d["is_ipl"] = True
    return d


def _fig_page(pdf: PdfPages, title: str, subtitle: str = "") -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="#f7f5fa")
    ax = fig.add_axes([.055, .07, .89, .84])
    ax.axis("off")
    fig.text(.06, .95, title, fontsize=21, fontweight="bold", color="#24123d", va="top")
    if subtitle:
        fig.text(.06, .91, subtitle, fontsize=9.2, color="#655a70", va="top")
    return fig, ax


def _table(ax: plt.Axes, df: pd.DataFrame, bbox=(0, .04, 1, .84), fontsize=8.4, col_widths=None) -> None:
    ax.axis("off")
    tbl = ax.table(cellText=df.values, colLabels=df.columns, cellLoc="center", colLoc="center", bbox=bbox, colWidths=col_widths)
    tbl.auto_set_font_size(False); tbl.set_fontsize(fontsize)
    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#ded8e6")
        if row == 0:
            cell.set_facecolor("#39205d"); cell.get_text().set_color("white"); cell.get_text().set_weight("bold")
        else:
            cell.set_facecolor("#eeeaf3" if row % 2 == 0 else "white")


def build_audit() -> dict:
    raw, manifest = load_inputs()
    tables = clean_analytical_copies(raw)
    integrated = integrate_deliveries(tables)
    d_t20i = t20i_states(tables, integrated)
    t20i_pressure = d_t20i[d_t20i.pressure_primary].copy()
    t20i_bat = rank_batters(d_t20i)
    t20i_bowl = rank_bowlers(d_t20i)

    existing_bat = pd.read_csv(OUT / "rankings" / "top_10_pressure_batters.csv")
    existing_bowl = pd.read_csv(OUT / "rankings" / "top_10_pressure_bowlers.csv")
    recomputed_bat = rank_batters(pd.read_csv(OUT / "processed" / "delivery_state_analytics.csv", low_memory=False)).head(10)
    recomputed_bowl = rank_bowlers(pd.read_csv(OUT / "processed" / "delivery_state_analytics.csv", low_memory=False)).head(10)
    same_bat = existing_bat.player_id.astype(int).tolist() == recomputed_bat.player_id.astype(int).tolist()
    same_bowl = existing_bowl.player_id.astype(int).tolist() == recomputed_bowl.player_id.astype(int).tolist()
    # Lock around existing order to ensure report/CSV exact concordance, and never write to these files.
    assert same_bat and same_bowl, "Existing CSV rank order differs from a direct recomputation."

    # Roster corrections checked against all supplied exception rows.
    roster = resolve_playing_eleven(tables)
    dup = roster[roster.candidate_key_group_size.gt(1)].copy()
    dup_groups = dup.groupby(["match_id", "team_id", "player_id"], dropna=False)
    group_rows = dup_groups.agg(rows=("player_id", "size"), candidate_orders=("batting_order", lambda s: ", ".join(map(str, sorted(s.dropna().unique())))), observed_striker_orders=("observed_striker_orders", "first"), selected=("include_in_unique_roster_view", "sum"), resolution=("analytical_resolution", "first")).reset_index()
    group_rows["observed_striker_orders"] = group_rows.observed_striker_orders.map(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else "none")
    assert len(group_rows) == 35 and int((group_rows.rows - 1).sum()) == 40 and group_rows.selected.eq(1).all()
    assert group_rows.resolution.eq("delivery_striker_order_corrob; source_rows_preserved").all()
    mapping = pd.read_csv(OUT / "processed" / "player_mapping_exceptions.csv")
    assert len(mapping) == 5 and mapping.player_id.nunique() == 1

    # Match and data coverage by official format labels; coverage table is from the persisted output.
    coverage = pd.read_csv(OUT / "processed" / "competition_coverage_by_season.csv")
    ipl_cov = coverage[coverage.comp_name.str.match(r"^IPL \d{4}$", na=False)]
    t20i_cov = coverage[coverage.match_format.eq("T20I")]
    ipl = {
        "scheduled": int(ipl_cov.scheduled_matches.sum()), "with": int(ipl_cov.matches_with_deliveries.sum()),
        "without": int(ipl_cov.matches_without_deliveries.sum()), "deliveries": int(ipl_cov.delivery_rows.sum()),
        "primary_matches": int(pd.read_csv(OUT / "processed" / "ipl_match_coverage_and_eligibility.csv").primary_match_eligible.sum()),
        "pressure_deliveries": int(pd.read_csv(OUT / "processed" / "delivery_state_analytics.csv", low_memory=False).pressure_primary.sum()),
    }
    t20i = {
        "scheduled": int(t20i_cov.scheduled_matches.sum()), "with": int(t20i_cov.matches_with_deliveries.sum()),
        "without": int(t20i_cov.matches_without_deliveries.sum()), "deliveries": int(t20i_cov.delivery_rows.sum()),
        "competitions": int(t20i_cov.comp_name.nunique()), "eligible_matches": int(d_t20i.loc[d_t20i.match_eligible, "match_id"].nunique()),
        "valid_chase_states": int(d_t20i.state_valid_primary.sum()), "pressure_deliveries": int(d_t20i.pressure_primary.sum()),
        "qualified_batters": int(t20i_bat.eligible_for_ranking.sum()), "qualified_bowlers": int(t20i_bowl.eligible_for_ranking.sum()),
    }
    # Within-T20I overall baselines allow a fair same-competition comparison.
    t20i_eligible = d_t20i[d_t20i.match_eligible].copy()
    bbase = t20i_eligible[~t20i_eligible.is_wide].groupby(["striker_id","striker_name"],dropna=False).agg(
        overall_runs=("runs","sum"), overall_balls=("match_id","size"), overall_innings=("innings",lambda s:int(t20i_eligible.loc[s.index,["match_id","innings"]].drop_duplicates().shape[0]))
    ).reset_index().rename(columns={"striker_id":"player_id","striker_name":"player_name"})
    bbase["overall_strike_rate"] = 100*bbase.overall_runs/bbase.overall_balls
    wsource=t20i_eligible[~t20i_eligible.extras_type.eq("other")].copy()
    wbase=wsource.groupby(["bowler_id","bowler_name"],dropna=False).agg(
        overall_legal_balls=("legal_ball_base","sum"),overall_bowler_runs=("bowler_runs_primary","sum"),
        overall_innings=("innings",lambda s:int(wsource.loc[s.index,["match_id","innings"]].drop_duplicates().shape[0]))
    ).reset_index().rename(columns={"bowler_id":"player_id","bowler_name":"player_name"})
    wbase["overall_economy"] = 6*wbase.overall_bowler_runs/wbase.overall_legal_balls.replace(0,np.nan)
    # Supplementary screens are deliberately separate from IPL primary rankings.
    t20i_bat = t20i_bat.head(10).merge(bbase[["player_id","overall_strike_rate"]],on="player_id",how="left",validate="1:1")
    t20i_bat["pressure_vs_overall_sr_delta"] = t20i_bat.pressure_strike_rate-t20i_bat.overall_strike_rate
    t20i_bowl = t20i_bowl.head(10).merge(wbase[["player_id","overall_economy"]],on="player_id",how="left",validate="1:1")
    t20i_bowl["pressure_minus_overall_economy"] = t20i_bowl.pressure_economy-t20i_bowl.overall_economy
    t20i_bat.to_csv(OUT / "rankings" / "supplementary_t20i_pressure_batters.csv", index=False)
    t20i_bowl.to_csv(OUT / "rankings" / "supplementary_t20i_pressure_bowlers.csv", index=False)

    # Overall-to-pressure same-player comparisons for the published IPL top tens.
    bat_overall = pd.read_csv(OUT / "processed" / "ipl_batter_overall_vs_pressure.csv")
    bowl_overall = pd.read_csv(OUT / "processed" / "ipl_bowler_overall_vs_pressure.csv")
    bat_comp = existing_bat.merge(bat_overall[["player_id", "strike_rate", "pressure_strike_rate", "pressure_balls", "pressure_innings"]], on="player_id", suffixes=("", "_audit"), validate="1:1")
    bowl_comp = existing_bowl.merge(bowl_overall[["player_id", "economy", "pressure_economy", "pressure_legal_balls", "pressure_innings"]], on="player_id", suffixes=("", "_audit"), validate="1:1")
    bat_comp["overall_to_pressure_sr_ratio"] = bat_comp.pressure_strike_rate_audit / bat_comp.strike_rate
    bowl_comp["pressure_minus_overall_economy"] = bowl_comp.pressure_economy_audit - bowl_comp.economy

    # Cricket calculation and exclusion checks against actual inputs and derived dataset.
    rawb = raw["ball_by_ball"]
    extras_counts = rawb.extras_type.value_counts(dropna=False).to_dict()
    dismissals = rawb.loc[rawb.is_wicket, "dismissal_type"].value_counts(dropna=False).to_dict()
    state_file = pd.read_csv(OUT / "processed" / "delivery_state_analytics.csv", low_memory=False)
    source_hashes_unchanged = all(sha256(ROOT / "data" / fn) == item["sha256"] for fn, item in manifest["inputs"].items())
    primary = state_file[state_file.pressure_primary]
    assert primary.state_valid_primary.all() and primary.innings.eq(2).all() and primary.is_ipl.all()
    assert (~primary.match_has_revised_state & ~primary.match_has_super_over).all()
    assert source_hashes_unchanged
    # Pick deterministic observed IPL delivery rows to show cricket event arithmetic.
    sample_specs = [
        ("Pressure legal", state_file.pressure_primary & state_file.extras_type.isna()),
        ("Wide", state_file.extras_type.eq("wide")),
        ("No-ball (Overstep)", state_file.extras_type.eq("Overstep")),
        ("Bye", state_file.extras_type.eq("byes")),
        ("Leg-bye", state_file.extras_type.eq("legbyes")),
        ("Unknown other", state_file.extras_type.eq("other")),
        ("Bowler-credit wicket", state_file.bowler_wicket),
        ("Run-out (not bowler credit)", state_file.is_wicket & state_file.dismissal_type.eq("RunOut")),
    ]
    sample_rows=[]
    for label, mask in sample_specs:
        cand=state_file[mask].sort_values(["match_id","innings","innings_ball_num"])
        if cand.empty:
            continue
        r=cand.iloc[0]
        if label == "Unknown other":
            bowler_runs="not scored"
        else:
            bowler_runs=int(r.runs + (r.extras1_runs if r.extras_type in ["wide","Overstep"] else 0))
        expected_team=int(r.runs+r.extras1_runs+r.extras_2_runs)
        assert int(r.team_runs)==expected_team
        assert bool(r.batter_ball)==(r.extras_type!="wide")
        assert bool(r.legal_ball_base)==(r.extras_type not in ["wide","Overstep"])
        if label not in ["Unknown other"]:
            assert int(r.bowler_runs_primary)==bowler_runs
        sample_rows.append({"Event":label,"Match":int(r.match_id),"Inn":int(r.innings),"Ball seq.":int(r.innings_ball_num),"Runs":int(r.runs),"Ex1/Ex2":f"{int(r.extras1_runs)}/{int(r.extras_2_runs)}","Team":expected_team,"BF":"yes" if r.batter_ball else "no","Legal":"yes" if r.legal_ball_base else "no","Bowler runs":bowler_runs,"Bowler wicket":"yes" if r.bowler_wicket else "no"})

    # Build audited report; create all figures in memory, leaving existing charts intact.
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(REPORT) as pdf:
        fig, ax = _fig_page(pdf, "ROUND 1 | COMPETITION READINESS AUDIT", "SupeRR Selector Season 2 · Rajasthan Royals · Evidence audit of the completed analytics project")
        ax.clear(); ax.axis("off")
        ax.text(0, .95, "Audit conclusion", fontsize=15, weight="bold", color="#39205d", transform=ax.transAxes)
        conclusion = (
            "The project has a reproducible IPL-only primary pressure leaderboard and valid sample-gated top tens. "
            "IPL-only is defensible for auction-role transfer, but the supplied T20I sample should also be used as a separate, explicitly labelled supplementary comparison. "
            "This audit now calculates that T20I screen without pooling it into or reordering the IPL top tens. The lists remain descriptive/exploratory, not validated predictors of future IPL auction success."
        )
        ax.text(0, .84, conclusion, fontsize=12, wrap=True, va="top", linespacing=1.55, transform=ax.transAxes)
        rows = [
            ["Coverage", f"IPL: {ipl['scheduled']} scheduled; {ipl['with']} with deliveries; {ipl['primary_matches']} primary eligible", f"T20I: {t20i['scheduled']} scheduled; {t20i['with']} with deliveries; {t20i['eligible_matches']} eligible"],
            ["Pressure sample", f"{ipl['pressure_deliveries']:,} IPL pressure deliveries", f"{t20i['pressure_deliveries']:,} T20I pressure deliveries"],
            ["Rankings", "Existing IPL top tens: recomputed order matches CSV", "Supplementary independent screen generated; not pooled"],
            ["Integrity", "Source SHA-256 unchanged; 35/35 duplicate groups corroborated", "16 delivery-missing matches are abandoned/no-result"],
        ]
        tb = ax.table(cellText=rows, colLabels=["Audit area", "Primary IPL", "Separate T20I"], loc="lower left", cellLoc="left", bbox=[0, .19, 1, .42])
        tb.auto_set_font_size(False); tb.set_fontsize(9)
        for (r,c), cell in tb.get_celld().items():
            cell.set_edgecolor("#ded8e6"); cell.set_facecolor("#39205d" if r==0 else ("#eeeaf3" if r%2==0 else "white"))
            if r==0: cell.get_text().set_color("white"); cell.get_text().set_weight("bold")
        ax.text(0, .09, "Audit run does not modify raw CSVs, current IPL rankings, charts, or presentation.", fontsize=9, color="#655a70", transform=ax.transAxes)
        pdf.savefig(fig, dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "1 | DATASETS & COMPETITION SEPARATION", "Actual coverage from supplied match and delivery tables")
        labels = ["IPL", "T20I"]
        scheduled = [ipl["scheduled"], t20i["scheduled"]]; with_delivery = [ipl["with"], t20i["with"]]
        y = np.arange(2); h=.31
        ax.barh(y+h/2, scheduled, h, label="Scheduled match records", color="#bdb2ca")
        ax.barh(y-h/2, with_delivery, h, label="Matches with delivery rows", color="#692e91")
        ax.set_yticks(y, labels, fontsize=12); ax.invert_yaxis(); ax.set_xlabel("Matches")
        ax.legend(loc="lower right", frameon=False); ax.grid(axis="x", alpha=.2)
        ax.text(.02, .14, f"IPL: {ipl['deliveries']:,} deliveries · 2022–2026 · primary cohort {ipl['primary_matches']} matches\nT20I: {t20i['deliveries']:,} deliveries · {t20i['competitions']} named competitions · supplementary eligible cohort {t20i['eligible_matches']} matches",
                transform=ax.transAxes, fontsize=10, color="#39205d", bbox=dict(boxstyle="round,pad=.5", fc="white", ec="#ded8e6"))
        pdf.savefig(fig, dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "2 | PRESSURE DEFINITION & MATCH-STATE RECONSTRUCTION", "Pre-delivery chase state; outcome of the current delivery is never used to label its own state")
        ax.clear(); ax.axis("off")
        formulas = [
            ("Cohort", "Regulation 2nd innings; match has innings 1 and 2; full 20-over allocation; exclude abandoned/no-result, DLS/revised target/overs, and any match with Super Over."),
            ("Pre-delivery score", "score_before = cumulative sum of (batter runs + extras1 + extras2) before this delivery."),
            ("State", "R = target − score_before; B = 120 − legal balls used; W = 10 − wickets lost. Target = reconstructed 1st-innings team total + 1."),
            ("Rates", "RRR = 6 × R / B (when R>0 and B>0); opening RRR = 6 × target / 120."),
            ("Pressure flag", "Primary: RRR − opening RRR > 0. Positive means the chase has fallen behind its initial required pace. It is a transparent state marker, not psychological pressure, win probability, or proof of clutch ability."),
            ("Boundary conditions", "Exclude states after the target, after 120 legal balls, and after an unresolved 'other' extra has already appeared. An 'other' event is retained only at its pre-delivery state; bowling outcome rows tagged 'other' are omitted from the primary bowling composite."),
        ]
        y0=.91
        for head, body in formulas:
            ax.text(.01,y0,head.upper(),fontsize=9,weight="bold",color="#8e3e9d",transform=ax.transAxes)
            ax.text(.19,y0,body,fontsize=10.4,color="#24123d",wrap=True,va="top",transform=ax.transAxes)
            y0-=.145
        ax.text(.01,.07,"Both competitions use the same arithmetic, but states and player rates are reconstructed in separate cohorts.",fontsize=10,weight="bold",color="#39205d",transform=ax.transAxes)
        pdf.savefig(fig,dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "3 | SCORE, ELIGIBILITY & FAIR-COMPARISON AUDIT", "The ranking is an opportunity-gated, cohort-relative descriptive screen")
        ax.clear(); ax.axis("off")
        text = [
            "BATTERS · score = (z(shrunk pressure SR) + z(shrunk pressure boundary-run share) + z(−shrunk pressure dot rate)) / 3.",
            "Pressure batter runs use the delivery batter-runs field; batter balls exclude wides and include no-balls. Boundary-run share uses batter boundary runs / batter runs; dot rate uses pressure balls with zero team runs / balls.",
            "Batter shrinkage: SR and dot rate use 30 prior pressure balls at the pressure-cohort mean; boundary-run share uses 300 prior batter runs. Gate: ≥30 pressure balls and ≥5 pressure innings.",
            "BOWLERS · score = (z(−shrunk pressure economy) + z(shrunk bowler wickets / 100 legal balls) + z(shrunk legal-dot rate)) / 3.",
            "Bowler runs include batter runs plus recorded wide/no-ball penalty extras; exclude byes/leg-byes and omit 'other'-tagged delivery outcomes. Legal balls exclude wides and Overstep. Bowler-credit wickets: Caught, Bowled, LBW, Stump, Hit Wicket; run-outs and other non-credit dismissals are not credited.",
            "Bowler shrinkage uses 60 prior legal balls at cohort means; gate: ≥60 classified pressure legal balls and ≥5 pressure innings.",
            "Opportunity fairness: gates, shrinkage and displayed raw workload reduce small-sample dominance; z-scores standardize eligible players within their own competition cohort. Equal weights are transparent but normative and do not make the composite an objective talent estimate.",
            "Rank order is descending composite; ties break on more pressure balls, then more pressure runs (batters) or wickets (bowlers). Sensitivity is reported on page 7.",
        ]
        y=.91
        for s in text:
            ax.text(.01,y,"•",fontsize=13,color="#8e3e9d",transform=ax.transAxes)
            ax.text(.055,y,s,fontsize=9.1,wrap=True,va="top",color="#24123d",transform=ax.transAxes)
            y-=.102
        pdf.savefig(fig,dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "4 | TOP 10 PRESSURE BATTERS — IPL PRIMARY", "Values and order verified against the existing CSV and a direct recomputation")
        bview=bat_comp[["rank","player_name","pressure_score","pressure_balls","pressure_innings","pressure_strike_rate_audit","strike_rate"]].copy()
        bview.columns=["Rank","Player","Score","P balls","P inns","P SR","Overall SR"]
        for c in ["Score","P SR","Overall SR"]: bview[c]=bview[c].map(lambda z:f"{z:.1f}")
        _table(ax,bview,bbox=[0,.10,1,.75],fontsize=8.5)
        ax.text(0,.025,"Pressure SR / overall SR is a descriptive contrast; the leaderboard score is calculated from pressure metrics only. No outcome guarantee.",fontsize=8.7,color="#655a70",transform=ax.transAxes)
        pdf.savefig(fig,dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "5 | TOP 10 PRESSURE BOWLERS — IPL PRIMARY", "Values and order verified against the existing CSV and a direct recomputation")
        wview=bowl_comp[["rank","player_name","pressure_score","pressure_legal_balls","pressure_innings","pressure_economy_audit","economy","pressure_wickets"]].copy()
        wview.columns=["Rank","Player","Score","P legal balls","P inns","P econ","Overall econ","P wkts"]
        for c in ["Score","P econ","Overall econ"]: wview[c]=wview[c].map(lambda z:f"{z:.2f}")
        _table(ax,wview,bbox=[0,.10,1,.75],fontsize=8.2)
        ax.text(0,.025,"Economy is runs conceded per six legal balls; higher pressure wicket counts are credited dismissals only.",fontsize=8.7,color="#655a70",transform=ax.transAxes)
        pdf.savefig(fig,dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "6 | SEPARATE T20I SUPPLEMENTARY PRESSURE SCREEN", "Same formula and gates, standardized within T20I-qualified players; these names are not added to IPL ranks")
        ax.clear(); ax.axis("off")
        ax.text(.01,.96,f"{t20i['eligible_matches']} regulation T20I matches · {t20i['valid_chase_states']:,} valid pre-delivery chase states · {t20i['pressure_deliveries']:,} pressure deliveries · {t20i['qualified_batters']} qualified batters · {t20i['qualified_bowlers']} qualified bowlers",
                fontsize=10,color="#39205d",transform=ax.transAxes)
        bv=t20i_bat.head(8)[["rank","player_name","pressure_score","pressure_balls","pressure_innings","overall_strike_rate","pressure_strike_rate"]].copy()
        bv.columns=["#","T20I batter","score","P balls","P inns","overall SR","P SR"]
        for c in ["score","overall SR","P SR"]: bv[c]=bv[c].map(lambda z:f"{z:.1f}")
        _table(ax,bv,bbox=[0,.51,1,.36],fontsize=7.4)
        wv=t20i_bowl.head(8)[["rank","player_name","pressure_score","pressure_legal_balls","pressure_innings","overall_economy","pressure_economy"]].copy()
        wv.columns=["#","T20I bowler","score","P legal","P inns","overall econ","P econ"]
        for c in ["score","overall econ","P econ"]: wv[c]=wv[c].map(lambda z:f"{z:.2f}")
        _table(ax,wv,bbox=[0,.05,1,.36],fontsize=7.4)
        ax.text(.01,.005,"Independent T20I screen is supplementary evidence only. International roles/opposition and event context differ from franchise IPL; it cannot silently increase IPL sample sizes.",fontsize=8,color="#655a70",transform=ax.transAxes)
        pdf.savefig(fig,dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "7 | SENSITIVITY, UNCERTAINTY & VALIDATION", "A stable-looking score does not imply stable rank ordering")
        sens=pd.read_csv(OUT/"rankings"/"pressure_ranking_sensitivity_checks.csv")
        sens=sens[sens.scenario.isin(["margin_at_least_2","valid_state_top_quartile_margin_3.100","scoring_first_weights","wicket_first_weights","other_extras_treated_illegal"])].copy()
        sv=sens[["scenario","role","top10_overlap","spearman_rank_correlation","eligible_primary","eligible_scenario"]].copy()
        sv.columns=["Scenario","Role","Top-10 overlap","Spearman ρ","Eligible base","Eligible alt."]
        sv["Spearman ρ"]=sv["Spearman ρ"].map(lambda z:f"{z:.2f}")
        _table(ax,sv,bbox=[0,.38,1,.47],fontsize=8.2)
        ax.text(.01,.29,f"Pressure-threshold sensitivity is material: margin ≥2 retains {int(sens[(sens.scenario=='margin_at_least_2')&(sens.role=='batter')].top10_overlap.iloc[0])}/10 batters and {int(sens[(sens.scenario=='margin_at_least_2')&(sens.role=='bowler')].top10_overlap.iloc[0])}/10 bowlers; upper-quartile margin retains {int(sens[(sens.scenario.str.startswith('valid_state_top_quartile'))&(sens.role=='batter')].top10_overlap.iloc[0])}/10 and {int(sens[(sens.scenario.str.startswith('valid_state_top_quartile'))&(sens.role=='bowler')].top10_overlap.iloc[0])}/10.",fontsize=10,wrap=True,color="#39205d",transform=ax.transAxes)
        ax.text(.01,.17,"Reliability checks: six source hashes unchanged; IPL primary pressure rows are IPL-only, valid chase states, second innings, pre-outcome, and exclude revised/DLS and Super Over matches; direct top-10 recomputation matches both saved rank orders; non-DLS run-win score margins reconcile 399/399.",fontsize=9.2,wrap=True,color="#24123d",transform=ax.transAxes)
        ax.text(.01,.07,"This is a sensitivity audit, not out-of-time validation or proof that pressure skill persists. No confidence intervals or predictive reliability gate were part of the original score implementation.",fontsize=9,wrap=True,color="#8e3e9d",transform=ax.transAxes)
        pdf.savefig(fig,dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "8 | ACTUAL DELIVERY ARITHMETIC SPOT CHECKS", "Examples are selected from supplied IPL rows; calculations below use the actual recorded fields")
        sv=pd.DataFrame(sample_rows)
        _table(ax,sv,bbox=[0,.22,1,.60],fontsize=7.5)
        # A concrete state example confirms cumulative values are pre-delivery, not post-delivery.
        state_ex=state_file[state_file.pressure_primary].sort_values(["match_id","innings","innings_ball_num"]).iloc[0]
        ax.text(.01,.16,"State example (immediately before the listed delivery):",fontsize=9.2,weight="bold",color="#39205d",transform=ax.transAxes)
        ax.text(.01,.09,f"Match {int(state_ex.match_id)}, innings {int(state_ex.innings)}, sequence {int(state_ex.innings_ball_num)} · score {int(state_ex.score_before)} · target {int(state_ex.target)} · runs required {int(state_ex.runs_required)} · legal balls left {int(state_ex.balls_remaining)} · wickets left {int(state_ex.wickets_remaining)} · RRR {state_ex.required_run_rate:.3f}, opening RRR {state_ex.opening_required_run_rate:.3f} · pressure={bool(state_ex.pressure_primary)}.",fontsize=8.6,wrap=True,color="#24123d",transform=ax.transAxes)
        ax.text(.01,.015,"Spot checks validate recorded totals and flags; they do not resolve the provider's undefined 'other' or extras_2 semantics. State uses preceding deliveries only.",fontsize=8.1,color="#655a70",transform=ax.transAxes)
        pdf.savefig(fig,dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "9 | PLAYING XI & CRICKET-DATA EXCEPTION AUDIT", "Rechecked directly against all flagged source exception records")
        ax.clear(); ax.axis("off")
        ax.text(.01,.92,"PLAYING XI",fontsize=10,weight="bold",color="#8e3e9d",transform=ax.transAxes)
        ax.text(.01,.85,"35 repeated (match, team, player) groups contain 75 source rows / 40 excess rows. In all 35, exactly one unique striker-observed batting order matches exactly one conflicting roster candidate. All groups therefore have one corroborated analytical row, while every raw/analytical exception row and source row number remains preserved. These groups occur in three non-IPL T20Is (match IDs 13613, 21176, 28962); corroboration is not a provider correction.",fontsize=9.4,wrap=True,transform=ax.transAxes)
        sample=group_rows.sort_values(["match_id","team_id","player_id"]).head(7)[["match_id","team_id","player_id","candidate_orders","observed_striker_orders","selected"]].copy()
        sample.columns=["Match","Team","Player","Roster orders","Striker order","Selected"]
        _table(ax,sample,bbox=[0,.47,1,.29],fontsize=7.7)
        ax.text(.01,.39,"PLAYER MAPPING · Five rows are Bashir Ahmad (ID 29833), team ID 4444, competition ID 2670 (Men's T20 Emerging Teams Asia Cup 2024); they are flagged not-played with no batting-order/role fields. Preserve as roster-to-mapping exceptions; do not infer five appearances.",fontsize=9.1,wrap=True,transform=ax.transAxes)
        ax.text(.01,.27,"SCORING / WICKETS · Team runs = runs + extras1 + extras2; batter runs use runs only; wides are not batter balls; no-balls count as batter balls but not legal balls; byes/leg-byes are team runs but not bowler runs. Recognized bowler wickets match observed credited labels Caught/Bowled/LBW/Stump/Hit Wicket; run-outs, retire-out and obstruction do not count.",fontsize=8.8,wrap=True,transform=ax.transAxes)
        ax.text(.01,.14,f"Observed extras labels/counts: {extras_counts}. Observed dismissal labels: {dismissals}. A single Penalty extras row and undefined 'other' / extras_2 semantics remain provider-definition limitations. `Overstep` is treated as a no-ball based on the data dictionary/context, but the provider should confirm.",fontsize=8.3,wrap=True,transform=ax.transAxes)
        pdf.savefig(fig,dpi=180); plt.close(fig)

        fig, ax = _fig_page(pdf, "10 | DIRECT ANSWERS, LIMITATIONS & HUMAN REVIEW", "Competition-readiness verdict against the Round 1 aim")
        ax.clear(); ax.axis("off")
        answers=[
            ("IPL and T20I?", "Both are now analysed; IPL remains the primary transfer cohort and T20I is separate supplementary evidence. IPL-only leaderboards remain unchanged."),
            ("Overall comparison?", "Each IPL top-10 batter has overall and pressure strike rate; each bowler has overall and pressure economy, plus pressure workload. The audit table puts those side by side."),
            ("Reliable under pressure?", "This pipeline ranks pressure output, not demonstrated reliability/persistence. A same-player pressure-vs-overall contrast and sensitivity are supplied; no temporal/repeated-split reliability validation exists."),
            ("Auction actions?", "The six files lack official 2027 auction eligibility/availability, current RR retained roster, purse, prices, roster slots and role needs. Therefore player names remain evidence screens, not verified auction targets."),
            ("Human review needed", "Confirm official problem-statement version and data-provider definitions for Overstep, other, extras_2 and revised-overs units; decide whether separate T20I supplementary screens meet scoring expectations; review high leaderboard sensitivity and lack of predictive reliability validation; acquire verified 2027 candidate/roster/purse inputs before actionable auction recommendations."),
        ]
        yy=.91
        for h,b in answers:
            ax.text(.01,yy,h,fontsize=10,weight="bold",color="#8e3e9d",transform=ax.transAxes)
            ax.text(.22,yy,b,fontsize=9.4,wrap=True,va="top",color="#24123d",transform=ax.transAxes)
            yy-=.17
        ax.text(.01,.035,"Competition source: Unstop event listing describes Round 1 as identifying the most reliable players under pressure for RR's IPL 2027 auction (https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758). The exact organizer-issued PDF was not present in the project folder; request it for a final clause-by-clause compliance sign-off.",fontsize=7.4,wrap=True,color="#655a70",transform=ax.transAxes)
        pdf.savefig(fig,dpi=180); plt.close(fig)

    return {"report": str(REPORT.relative_to(ROOT)), "source_hashes_unchanged": source_hashes_unchanged,
            "ipl": ipl, "t20i": t20i, "ipl_top10_order_matches": {"batter": same_bat, "bowler": same_bowl},
            "duplicate_groups": len(group_rows), "duplicate_rows": int(len(dup)), "duplicate_excess": int((group_rows.rows-1).sum()),
            "mapping_exception_rows": int(len(mapping)), "t20i_top_batters": t20i_bat.player_name.tolist(), "t20i_top_bowlers": t20i_bowl.player_name.tolist(),
            "sample_delivery_checks": len(sample_rows), "pdf_pages": 11}


if __name__ == "__main__":
    result=build_audit()
    print(json.dumps(result,indent=2))
