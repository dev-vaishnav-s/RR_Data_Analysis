"""Read-only ingestion, non-destructive cleaning, auditing, and integration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
FILES = {
    "ball_by_ball": "ball_by_ball_updated.csv",
    "matches": "matches.csv",
    "playing_eleven": "playing_eleven.csv",
    "player_mapping": "competition_team_player_mapping.csv",
    "teams": "teams.csv",
    "competitions": "competitions.csv",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_inputs() -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    tables: dict[str, pd.DataFrame] = {}
    manifest: dict[str, Any] = {"inputs": {}, "read_only": True}
    for key, filename in FILES.items():
        path = DATA / filename
        if not path.exists():
            raise FileNotFoundError(f"Required source dataset not found: {path}")
        df = pd.read_csv(path, low_memory=False)
        tables[key] = df
        manifest["inputs"][filename] = {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    return tables, manifest


def clean_analytical_copies(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Normalize types/text on copies; preserve source rows and columns."""
    cleaned = {name: df.copy() for name, df in tables.items()}
    for name, df in cleaned.items():
        for col in df.select_dtypes(include=["object", "string"]).columns:
            # Trim accidental whitespace but do not rewrite category spellings.
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    for col in ("match_date",):
        cleaned["matches"][col + "_parsed"] = pd.to_datetime(
            cleaned["matches"][col], errors="coerce", format="mixed"
        )
    cleaned["ball_by_ball"]["delivery_timestamp_parsed"] = pd.to_datetime(
        cleaned["ball_by_ball"]["delivery_ist_time"], errors="coerce", utc=True
    )
    # Exact duplicate rows are retained and flagged; none are expected in this extract.
    for name, df in cleaned.items():
        df["_source_row_number"] = range(1, len(df) + 1)
        df["_exact_duplicate_row"] = df.drop(
            columns=["_source_row_number"], errors="ignore"
        ).duplicated(keep=False)
    return cleaned


def _as_key_set(df: pd.DataFrame, cols: list[str]) -> set[tuple]:
    return set(map(tuple, df[cols].drop_duplicates().itertuples(index=False, name=None)))


def audit_data(t: dict[str, pd.DataFrame]) -> tuple[dict[str, Any], pd.DataFrame]:
    b, m, pe = t["ball_by_ball"], t["matches"], t["playing_eleven"]
    pm, teams, comps = t["player_mapping"], t["teams"], t["competitions"]
    dup_groups = (
        pe.groupby(["match_id", "team_id", "player_id"], dropna=False)
        .size().rename("group_rows").reset_index().query("group_rows > 1")
    )
    dup_rows = pe.merge(dup_groups, on=["match_id", "team_id", "player_id"], how="inner")
    # Establish whether the delivery-level batting_order is attached to the striker.
    striker_orders = (
        b.groupby(["match_id", "batting_team_id", "striker_id"])
        .batting_order.agg(lambda x: sorted(pd.unique(x.dropna()).tolist()))
        .rename("striker_observed_orders").reset_index()
        .rename(columns={"batting_team_id": "team_id", "striker_id": "player_id"})
    )
    dup_details = dup_rows.merge(
        striker_orders, on=["match_id", "team_id", "player_id"], how="left"
    )
    dup_details["candidate_orders"] = dup_details.groupby(
        ["match_id", "team_id", "player_id"]
    ).batting_order.transform(lambda x: [sorted(x.dropna().unique().tolist())] * len(x))
    dup_details["resolution_status"] = "unresolved_no_striker_delivery"
    for idx, row in dup_details.iterrows():
        observed = row["striker_observed_orders"]
        candidates = row["candidate_orders"]
        if isinstance(observed, list) and len(observed) == 1 and observed[0] in candidates:
            dup_details.at[idx, "resolution_status"] = "order_corrob_by_striker_delivery"
        elif isinstance(observed, list) and len(observed) > 1:
            dup_details.at[idx, "resolution_status"] = "unresolved_multiple_striker_orders"
    group_status = dup_details.groupby(
        ["match_id", "team_id", "player_id"]
    ).resolution_status.first().reset_index()
    missing_map = (
        pe.merge(m[["match_id", "comp_id"]], on="match_id", validate="m:1")
        .merge(pm[["comp_id", "team_id", "player_id"]].drop_duplicates(),
               on=["comp_id", "team_id", "player_id"], how="left", indicator=True,
               validate="m:1")
    )
    missing_roster_map = missing_map[missing_map._merge.eq("left_only")].copy()
    match_ids = set(m.match_id)
    team_keys = _as_key_set(teams, ["comp_id", "team_id"])
    match_team_keys = _as_key_set(m[["comp_id", "home_team_id"]].rename(columns={"home_team_id": "team_id"}), ["comp_id", "team_id"])
    match_team_keys |= _as_key_set(m[["comp_id", "away_team_id"]].rename(columns={"away_team_id": "team_id"}), ["comp_id", "team_id"])
    expected_sides = set(zip(m.comp_id, m.home_team_id)) | set(zip(m.comp_id, m.away_team_id))
    actual_sides = set(zip(teams.comp_id, teams.team_id))
    all_deliveries_have_match = set(b.match_id).issubset(match_ids)
    delivery_sides = b.merge(m[["match_id", "home_team_id", "away_team_id"]], on="match_id", validate="m:1")
    bad_delivery_sides = delivery_sides[
        ~delivery_sides.batting_team_id.isin(delivery_sides[["home_team_id", "away_team_id"]].values.flatten())
    ]
    # Row-wise robust side validation (the vectorized membership above is a conservative check).
    side_map = m.set_index("match_id")[["home_team_id", "away_team_id"]].apply(lambda r: {r.iloc[0], r.iloc[1]}, axis=1).to_dict()
    bad_delivery_side_rows = int(sum(
        r.batting_team_id not in side_map[r.match_id]
        or r.bowling_team_id not in side_map[r.match_id]
        or r.batting_team_id == r.bowling_team_id
        for r in b[["match_id", "batting_team_id", "bowling_team_id"]].itertuples(index=False)
    ))
    all_ipl_ids = set(m.merge(comps[comps.comp_name.str.match(r"^IPL \d{4}$", na=False)][["comp_id"]], on="comp_id").match_id)
    missing_delivery_matches = m[~m.match_id.isin(set(b.match_id))].merge(
        comps, on="comp_id", how="left", validate="m:1"
    )
    ipl_missing = missing_delivery_matches[missing_delivery_matches.comp_name.str.match(r"^IPL \d{4}$", na=False)]
    audit = {
        "dimensions": {k: [int(len(v)), int(len(v.columns))] for k, v in t.items()},
        "nulls": {k: {c: int(n) for c, n in v.isna().sum().items() if n} for k, v in t.items()},
        "exact_duplicate_rows": {k: int(v.duplicated().sum()) for k, v in t.items()},
        "keys": {
            "competition_id_unique": bool(comps.comp_id.is_unique),
            "match_id_unique": bool(m.match_id.is_unique),
            "team_comp_team_unique": bool(not teams.duplicated(["comp_id", "team_id"]).any()),
            "player_mapping_comp_team_player_unique": bool(not pm.duplicated(["comp_id", "team_id", "player_id"]).any()),
            "delivery_match_innings_ball_unique": bool(not b.duplicated(["match_id", "innings", "innings_ball_num"]).any()),
            "pe_duplicate_key_groups": int(len(dup_groups)),
            "pe_duplicate_excess_rows": int((dup_groups.group_rows - 1).sum()),
        },
        "foreign_keys": {
            "match_comp_missing": int((~m.comp_id.isin(comps.comp_id)).sum()),
            "match_side_comp_team_missing": int(len(expected_sides - actual_sides)),
            "delivery_match_missing": int((~b.match_id.isin(m.match_id)).sum()),
            "pe_match_missing": int((~pe.match_id.isin(m.match_id)).sum()),
            "delivery_invalid_or_same_side_rows": bad_delivery_side_rows,
            "pe_player_mapping_missing_rows": int(len(missing_roster_map)),
        },
        "coverage": {
            "all_matches": int(m.match_id.nunique()),
            "delivery_matches": int(b.match_id.nunique()),
            "matches_without_deliveries": int(m.match_id.nunique() - b.match_id.nunique()),
            "ipl_match_records": int(len(all_ipl_ids)),
            "ipl_matches_with_deliveries": int(len(all_ipl_ids & set(b.match_id))),
            "ipl_matches_without_deliveries": int(len(all_ipl_ids - set(b.match_id))),
            "no_delivery_results": missing_delivery_matches.result.value_counts(dropna=False).to_dict(),
        },
        "roster_duplicate_resolution": {
            "groups_by_status": group_status.resolution_status.value_counts().to_dict(),
            "group_details": dup_details[["match_id", "team_id", "player_id", "batting_order", "group_rows", "candidate_orders", "striker_observed_orders", "resolution_status"]].to_dict("records"),
        },
        "mapping_exceptions": missing_roster_map[["match_id", "comp_id", "team_id", "player_id"]].to_dict("records"),
        "missing_delivery_matches": missing_delivery_matches[["match_id", "comp_name", "match_date", "home_team", "away_team", "result"]].to_dict("records"),
    }
    return audit, missing_roster_map


def resolve_playing_eleven(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Keep every source row and explicitly flag the analyst-selected record."""
    pe = t["playing_eleven"].copy()
    b = t["ball_by_ball"]
    keys = ["match_id", "team_id", "player_id"]
    pe["candidate_key_group_size"] = pe.groupby(keys).player_id.transform("size")
    pe["analytical_resolution"] = "unique_candidate_key"
    pe["include_in_unique_roster_view"] = True
    striker_orders = b.groupby(["match_id", "batting_team_id", "striker_id"]).batting_order.agg(
        lambda x: sorted(pd.unique(x.dropna()).tolist())
    ).rename("observed_striker_orders").reset_index().rename(
        columns={"batting_team_id": "team_id", "striker_id": "player_id"}
    )
    pe = pe.merge(striker_orders, on=keys, how="left", validate="m:1")
    for _, idxs in pe[pe.candidate_key_group_size.gt(1)].groupby(keys, sort=False).groups.items():
        idxs = list(idxs)
        observed = pe.loc[idxs[0], "observed_striker_orders"]
        candidates = pe.loc[idxs, "batting_order"].dropna()
        if isinstance(observed, list) and len(observed) == 1 and candidates.eq(observed[0]).sum() == 1:
            chosen = candidates[candidates.eq(observed[0])].index[0]
            pe.loc[idxs, "include_in_unique_roster_view"] = False
            pe.loc[chosen, "include_in_unique_roster_view"] = True
            pe.loc[idxs, "analytical_resolution"] = "delivery_striker_order_corrob; source_rows_preserved"
        else:
            # Do not arbitrarily choose: all rows remain represented but are explicitly unresolved.
            pe.loc[idxs, "analytical_resolution"] = "unresolved_duplicate; source_rows_preserved"
            pe.loc[idxs, "include_in_unique_roster_view"] = False
    return pe


def integrate_deliveries(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join match and competition context with cardinality checks; never join roster rows."""
    b, m, c, teams = (t["ball_by_ball"], t["matches"], t["competitions"], t["teams"])
    match_cols = ["match_id", "comp_id", "match_number", "match_date", "stage", "venue_id", "venue_country",
                  "home_team_id", "home_team", "away_team_id", "away_team", "toss_win_team_id", "toss_opted",
                  "first_inn_revised_overs", "second_inn_revised_overs", "revised_target", "knock_out", "win_team_id", "result"]
    comp_cols = ["comp_id", "comp_name", "match_format", "season"]
    rows_before = len(b)
    x = b.merge(m[match_cols], on="match_id", how="left", validate="m:1", indicator="_match_join")
    if len(x) != rows_before or not x._match_join.eq("both").all():
        raise ValueError("Delivery-to-match integration failed cardinality/completeness validation")
    x = x.drop(columns="_match_join").merge(c[comp_cols], on="comp_id", how="left", validate="m:1", indicator="_competition_join")
    if len(x) != rows_before or not x._competition_join.eq("both").all():
        raise ValueError("Match-to-competition integration failed cardinality/completeness validation")
    team_lookup = teams.drop_duplicates(["comp_id", "team_id"])
    for role, id_col, name in [
        ("batting", "batting_team_id", "batting_team_name"),
        ("bowling", "bowling_team_id", "bowling_team_name"),
    ]:
        lookup = team_lookup.rename(columns={"team_id": id_col, "team_name": name})[["comp_id", id_col, name]]
        x = x.merge(lookup, on=["comp_id", id_col], how="left", validate="m:1")
    x["is_ipl"] = x.comp_name.str.match(r"^IPL \d{4}$", na=False)
    x["delivery_total_runs"] = x.runs + x.extras1_runs + x.extras_2_runs
    x["is_wide"] = x.extras_type.eq("wide")
    x["is_no_ball_candidate"] = x.extras_type.eq("Overstep")
    x["legal_ball_known"] = ~(x.is_wide | x.is_no_ball_candidate)
    x["legal_ball_alt_other_illegal"] = x.legal_ball_known & ~x.extras_type.eq("other")
    x["bowler_runs_confirmed"] = x.runs + x.extras1_runs.where(x.extras_type.isin(["wide", "Overstep"]), 0)
    x["bowler_runs_sensitivity_other_charged"] = x.bowler_runs_confirmed + x.extras1_runs.where(x.extras_type.eq("other"), 0)
    x["bowler_runs_sensitivity_extra2_charged"] = x.bowler_runs_sensitivity_other_charged + x.extras_2_runs
    credited = {"Caught", "Bowled", "LBW", "Stump", "Hit Wicket"}
    x["bowler_creditable_wicket"] = x.is_wicket & x.dismissal_type.isin(credited)
    x["dismissal_unknown_label"] = x.is_wicket & ~x.dismissal_type.isin(credited | {"RunOut", "Retire Out", "Obstracting the field", "Obstructing the field"})
    x["scheduled_over_phase"] = pd.cut(
        x.overid, bins=[0, 6, 15, 20, float("inf")], labels=["Powerplay", "Middle", "Death", "Other"], right=True
    ).astype("string")
    return x

