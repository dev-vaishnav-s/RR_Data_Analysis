# Data Quality and Exception Handling Report

**Inspection source:** `outputs/reports/dataset_inspection_report.md` (initial and second-stage investigation)  
**Execution:** Reproducible Python pipeline; source CSVs were read-only.  
**Purpose:** Record implementation-time checks, treatment, and coverage limits. This report supplements rather than replaces the inspection report.

## Source inventory and before/after row counts

| Source table | Source rows | Source columns | Exact duplicate rows | Null cells |
|---|---:|---:|---:|---:|
| `ball_by_ball` | 200,999 | 33 | 0 | 766,466 |
| `matches` | 883 | 22 | 0 | 2,736 |
| `playing_eleven` | 28,381 | 9 | 0 | 26,012 |
| `player_mapping` | 6,413 | 6 | 0 | 0 |
| `teams` | 353 | 3 | 0 | 0 |
| `competitions` | 141 | 4 | 0 | 0 |

**Total raw rows:** 237,170. Cleaning is performed on in-memory copies. No source rows are removed. Text values are whitespace-trimmed only in analytical copies; categories/spelling variants are retained. Date/timestamp parsing adds derived columns rather than overwriting source strings. No exact duplicate rows were found, so no rows were dropped. Integrated deliveries: 200,999, equal to source delivery rows: 200,999; validated match and competition joins did not multiply rows.

## Keys, relationships, and cleaning treatment

- Unique keys validated: `competitions.comp_id`, `matches.match_id`, `teams(comp_id, team_id)`, `competition_team_player_mapping(comp_id, team_id, player_id)`, and `ball_by_ball_updated(match_id, innings, innings_ball_num)`.
- Candidate delivery key `(match_id, innings, overid, over_ball_num)` is also unique in the source. The sequence field `innings_ball_num` counts recorded deliveries, not confirmed legal balls.
- Missing foreign references: `{"match_comp_missing": 0, "match_side_comp_team_missing": 0, "delivery_match_missing": 0, "pe_match_missing": 0, "delivery_invalid_or_same_side_rows": 0, "pe_player_mapping_missing_rows": 5}`. Delivery integration is many-to-one to matches and competitions and many-to-one to competition-team labels. Player rosters were **not** joined onto delivery rows, avoiding row multiplication from the 35 repeated candidate keys.
- No invalid match or team-side references were found in source checks. Five roster-to-player-mapping misses are listed below and preserved.

## Playing-eleven duplicate groups

There are 35 repeated `(match_id, team_id, player_id)` groups and 40 excess source rows. A striker-only delivery check is critical: in this feed, `ball_by_ball_updated.batting_order` tracks the striker's order; values seen while a player was the non-striker belong to the other batter and must not be used to resolve that player's roster row.

For **all 35 groups**, one unique observed striker order matched exactly one of that player's conflicting roster `batting_order` candidates. The pipeline therefore flags one corroborated roster row per group as the analytical selection and marks the other 40 rows `include_in_unique_roster_view=False`. All 75 duplicate-group source records remain in `playing_eleven_analytical.csv`, with source row numbers, candidate orders, observed striker orders, resolution status and selection flag. This is a transparent analytical view, not a destructive source correction; batting performance is calculated from deliveries, not from this roster selection.

The groups are exclusively in matches 13613, 21176 and 28962 (non-IPL T20Is). One-row-per-player roster views may use the striker-corroborated record for those groups. Original ambiguity remains documented because the delivery feed is corroboration, not an independent provider correction.

| Match | Team ID | Player ID | Roster candidate orders | Unique striker order | Treatment |
|---:|---:|---:|---|---|---|
| 13613 | 20 | 3539 | 1, 3 | 1 | order_corrob_by_striker_delivery |
| 13613 | 20 | 838 | 1, 4 | 4 | order_corrob_by_striker_delivery |
| 13613 | 20 | 250 | 2, 4 | 2 | order_corrob_by_striker_delivery |
| 13613 | 20 | 2639 | 2, 6 | 6 | order_corrob_by_striker_delivery |
| 13613 | 20 | 4736 | 3, 5 | 3 | order_corrob_by_striker_delivery |
| 13613 | 20 | 223 | 5, 6 | 5 | order_corrob_by_striker_delivery |
| 13613 | 27 | 2436 | 1, 6 | 6 | order_corrob_by_striker_delivery |
| 13613 | 27 | 6931 | 1, 3 | 1 | order_corrob_by_striker_delivery |
| 13613 | 27 | 2351 | 2, 4 | 2 | order_corrob_by_striker_delivery |
| 13613 | 27 | 1100 | 2, 5 | 5 | order_corrob_by_striker_delivery |
| 13613 | 27 | 4902 | 3, 5 | 3 | order_corrob_by_striker_delivery |
| 13613 | 27 | 4895 | 4, 6 | 4 | order_corrob_by_striker_delivery |
| 21176 | 17 | 4106 | 1, 4 | 4 | order_corrob_by_striker_delivery |
| 21176 | 17 | 25534 | 1, 4 | 1 | order_corrob_by_striker_delivery |
| 21176 | 17 | 3323 | 2, 6 | 6 | order_corrob_by_striker_delivery |
| 21176 | 17 | 3700 | 2, 5 | 2 | order_corrob_by_striker_delivery |
| 21176 | 17 | 2246 | 3, 6 | 3 | order_corrob_by_striker_delivery |
| 21176 | 17 | 3374 | 3, 5 | 5 | order_corrob_by_striker_delivery |
| 21176 | 27 | 6931 | 1, 3 | 1 | order_corrob_by_striker_delivery |
| 21176 | 27 | 3672 | 1, 2 | 2 | order_corrob_by_striker_delivery |
| 21176 | 27 | 4895 | 2, 5 | 5 | order_corrob_by_striker_delivery |
| 21176 | 27 | 1481 | 3, 4 | 3 | order_corrob_by_striker_delivery |
| 21176 | 27 | 2407 | 4, 5 | 4 | order_corrob_by_striker_delivery |
| 28962 | 18 | 126 | 1, 2 | 2 | order_corrob_by_striker_delivery |
| 28962 | 18 | 6819 | 1, 2, 4 | 1 | order_corrob_by_striker_delivery |
| 28962 | 18 | 4708 | 2, 3, 6 | 6 | order_corrob_by_striker_delivery |
| 28962 | 18 | 2258 | 3, 5 | 5 | order_corrob_by_striker_delivery |
| 28962 | 18 | 47 | 3, 5 | 3 | order_corrob_by_striker_delivery |
| 28962 | 18 | 4755 | 4, 6 | 4 | order_corrob_by_striker_delivery |
| 28962 | 78 | 6674 | 1, 2 | 1 | order_corrob_by_striker_delivery |
| 28962 | 78 | 1107 | 1, 3, 5 | 5 | order_corrob_by_striker_delivery |
| 28962 | 78 | 2214 | 1, 3, 4 | 3 | order_corrob_by_striker_delivery |
| 28962 | 78 | 6448 | 2, 5 | 2 | order_corrob_by_striker_delivery |
| 28962 | 78 | 5808 | 3, 4, 6 | 6 | order_corrob_by_striker_delivery |
| 28962 | 78 | 6676 | 4, 6 | 4 | order_corrob_by_striker_delivery |

## Player mapping exceptions

All five rows are player 29833 (Bashir Ahmad), team 4444 (Afghanistan A), competition 2670 (Mens T20 Emerging Teams Asia Cup 2024), with `is_played=False` and null batting order/captain/wicketkeeper fields. His identity occurs under Afghanistan in other competitions. Preserve these as missing competition-team mapping rows; do not infer five appearances or reject the person ID.

| Match | Competition | Team | Player |
|---:|---:|---:|---:|
| 37086 | 2670 | 4444 | 29833 |
| 37090 | 2670 | 4444 | 29833 |
| 37093 | 2670 | 4444 | 29833 |
| 37098 | 2670 | 4444 | 29833 |
| 37099 | 2670 | 4444 | 29833 |

## Match coverage and exclusions

- All 16 matches with no ball-by-ball rows are marked `Match Abandoned`, with null winner. They remain in schedule coverage and do not contribute player delivery observations.
- IPL schedule: 371 matches; delivery records in 367; no-delivery abandoned matches: 4.
- For primary pressure analysis, eligible regulation IPL matches: 354; primary chase-state rows with valid pre-delivery state: 39,324; identified pressure deliveries (RRR above opening requirement): 24,844.
- Competition-by-season coverage is saved separately. Non-IPL T20/T20I rows are not pooled into IPL performance or pressure rates.
- Primary exclusions are applied at match level: missing innings 1/2, no-result/abandoned, any revised overs or target, DLS result, or any Super Over. These conditions can overlap; the reason counts in the JSON below are not additive.
- There are four IPL matches without any delivery rows; exclusions with partial ball data are separately counted above.

### All matches without deliveries

| Match | Date | Competition | Fixture | Result |
|---:|---|---|---|---|
| 36564 | 2024-09-15 | Australia in England T20I Series 2024 | England vs Australia | Match Abandoned |
| 46008 | 2025-09-19 | England in Ireland T20I series 2025 | Ireland vs England | Match Abandoned |
| 31281 | 2024-05-13 | IPL 2024 | Gujarat Titans vs Kolkata Knight Riders | Match Abandoned |
| 31284 | 2024-05-16 | IPL 2024 | Sunrisers Hyderabad vs Gujarat Titans | Match Abandoned |
| 31288 | 2024-05-19 | IPL 2024 | Rajasthan Royals vs Kolkata Knight Riders | Match Abandoned |
| 40761 | 2025-05-17 | IPL 2025 | Royal Challengers Bengaluru vs Kolkata Knight Riders | Match Abandoned |
| 32622 | 2024-05-20 | Netherlands Tri-Nation T20I Series 2024 | Ireland vs Scotland | Match Abandoned |
| 50189 | 2026-04-29 | New Zealand in Bangladesh T20I Series 2026 | Bangladesh vs New Zealand | Match Abandoned |
| 32610 | 2024-05-22 | Pakistan in England T20I Series 2024 | England vs Pakistan | Match Abandoned |
| 32612 | 2024-05-28 | Pakistan in England T20I Series 2024 | England vs Pakistan | Match Abandoned |
| 38797 | 2024-12-14 | Pakistan in South Africa T20I Series 2024 | South Africa vs Pakistan | Match Abandoned |
| 48513 | 2026-01-10 | Pakistan in Sri Lanka T20I Series 2026 | Sri Lanka vs Pakistan | Match Abandoned |
| 36210 | 2025-09-14 | South Africa in England T20I Series 2025 | England vs South Africa | Match Abandoned |
| 42030 | 2025-12-17 | South Africa in India T20I Series 2025 | India vs South Africa | Match Abandoned |
| 41502 | 2025-06-12 | West Indies in Ireland T20I Series 2025 | Ireland vs West Indies | Match Abandoned |
| 41503 | 2025-06-14 | West Indies in Ireland T20I Series 2025 | Ireland vs West Indies | Match Abandoned |

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
| IPL primary pressure cohort | 371 scheduled IPL matches | Exclude no-result/abandoned, revisions/DLS, super overs, and matches lacking innings 1/2 | 354 eligible matches |

## Run metadata

```json
{
  "audit_keys": {
    "competition_id_unique": true,
    "match_id_unique": true,
    "team_comp_team_unique": true,
    "player_mapping_comp_team_player_unique": true,
    "delivery_match_innings_ball_unique": true,
    "pe_duplicate_key_groups": 35,
    "pe_duplicate_excess_rows": 40
  },
  "foreign_keys": {
    "match_comp_missing": 0,
    "match_side_comp_team_missing": 0,
    "delivery_match_missing": 0,
    "pe_match_missing": 0,
    "delivery_invalid_or_same_side_rows": 0,
    "pe_player_mapping_missing_rows": 5
  },
  "coverage": {
    "all_matches": 883,
    "delivery_matches": 867,
    "matches_without_deliveries": 16,
    "ipl_match_records": 371,
    "ipl_matches_with_deliveries": 367,
    "ipl_matches_without_deliveries": 4,
    "no_delivery_results": {
      "Match Abandoned": 16
    }
  },
  "primary_exclusions": {
    "DLS_result": 4,
    "abandoned_or_no_result": 5,
    "missing_innings_1_or_2": 4,
    "revised_target_or_overs": 5,
    "super_over": 2
  }
}
```
