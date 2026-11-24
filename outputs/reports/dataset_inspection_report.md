# Initial Dataset Inspection Report

**Project:** Rajasthan Royals IPL 2027 auction analysis - Cricket Pressure Performance Analytics  
**Inspection date:** 2026-11-16  
**Scope:** Read-only inspection of all CSV files in `data/`. No source data was edited. No rankings or analytical code were created.

## Executive findings

- The six requested files are present. Together they contain 237,170 rows across competition, team, player-roster, match and delivery levels.
- `matches.match_id` is unique; all match IDs referenced by `playing_eleven` and `ball_by_ball_updated` exist in `matches`. Match competition IDs resolve to `competitions`; match team IDs resolve to `teams` for the same competition; delivery teams are the two sides in their match.
- The natural candidate key `(match_id, team_id, player_id)` in `playing_eleven` has **35 duplicated groups / 40 excess rows**. In total, 75 rows are in these groups. They are not exact duplicates; same-key rows disagree on `batting_order` (and may repeat captain/wicketkeeper flags). Preserve and investigate them; do not deduplicate automatically.
- There are **16 matches without ball-by-ball rows**, including four IPL matches (three in IPL 2024 and one in IPL 2025). `playing_eleven` covers 880 of 883 matches. These gaps constrain delivery-derived measures.
- The data covers IPL 2022-2026 (371 matches in the match table) and other T20/T20I competitions. It does **not** contain IPL 2027 auction data or a supplied methodology specification. It can support retrospective, delivery-level T20 pressure features where coverage and semantics allow; it cannot alone establish a future auction shortlist or encode a pressure formula that is absent from the supplied materials.

> The six table dimensions sum to **237,170 rows**.

## 1. Files, dimensions and schemas

All six CSVs were read with pandas. Dimensions are rows - columns. Dtypes are pandas-inferred from the files (integer, floating-point, boolean, string); integer-coded IDs should be treated as identifiers, not quantities.

| File | Dimensions | Candidate grain |
|---|---:|---|
| `ball_by_ball_updated.csv` | 200,999 - 33 | One delivery record; proposed key `(match_id, innings, innings_ball_num)` |
| `competition_team_player_mapping.csv` | 6,413 - 6 | Player-team-competition membership |
| `competitions.csv` | 141 - 4 | One competition |
| `matches.csv` | 883 - 22 | One match |
| `playing_eleven.csv` | 28,381 - 9 | Player/team/match participation row; candidate key noted above |
| `teams.csv` | 353 - 3 | Team in a competition |

### Column names and inferred data types

- **ball_by_ball_updated.csv:** `match_id` int64; `innings` int64; `overid` int64; `over_ball_num` int64; `innings_ball_num` int64; `batting_team_id` int64; `bowling_team_id` int64; `striker_id` int64; `striker_name` string; `non_striker_id` int64; `non_striker_name` string; `bowler_id` int64; `bowler_name` string; `batting_type` string; `bowling_type` string; `batting_order` int64; `runs` int64; `is_four` bool; `is_six` bool; `is_wicket` bool; `dismissal_type_id` float64; `dismissal_type` string; `dismissed_player_id` float64; `extras_type` string; `extras1_runs` int64; `extras_2_runs` int64; `pace_or_spin` string; `bowl_speed` float64; `stroke` string; `delivery_style` string; `over_or_around` string; `on_or_off` string; `delivery_ist_time` string.
- **competition_team_player_mapping.csv:** `comp_id` int64; `comp_name` string; `team_id` int64; `team_name` string; `player_id` int64; `player_name` string.
- **competitions.csv:** `comp_id` int64; `comp_name` string; `match_format` string; `season` string.
- **matches.csv:** `match_id` int64; `comp_id` int64; `match_number` int64; `match_date` string; `stage` string; `venue_id` int64; `venue_country` string; `home_team_id` int64; `home_team` string; `away_team_id` int64; `away_team` string; `home_team_captain_id` float64; `away_team_captain_id` float64; `toss_win_team_id` float64; `toss_opted` string; `man_of_the_match` int64; `first_inn_revised_overs` float64; `second_inn_revised_overs` float64; `revised_target` float64; `knock_out` int64; `win_team_id` float64; `result` string.
- **playing_eleven.csv:** `match_id` int64; `team_id` int64; `player_id` int64; `batting_order` float64; `is_played` bool; `is_captain` object/string-like; `is_wk` object/string-like; `is_impact` int64; `is_impact_off` int64.
- **teams.csv:** `comp_id` int64; `team_id` int64; `team_name` string.

### Sample records observed

- `matches` starts with match `13511`, competition `1331`, dated `2022-01-22`, West Indies vs England; result text is `West Indies Won by 9 Wickets`.
- `ball_by_ball_updated` starts with match `13511`, innings 1, over 1, ball 1; Jason Roy faces Sheldon Cottrell and `runs=0`.
- `playing_eleven` starts with match `13511`, team 22, player 1187, batting order 1, `is_played=True`.
- `competitions` includes `IPL 2022` through `IPL 2026`; the displayed first record is a 2026 T20I competition.

## 2. Missing values and exact duplicates

No table has a full-row exact duplicate (`DataFrame.duplicated()` count is zero in each file).

| File | Columns with nulls (count) |
|---|---|
| `ball_by_ball_updated.csv` | `dismissal_type_id` 190,118; `dismissal_type` 190,118; `dismissed_player_id` 190,107; `extras_type` 189,167; `stroke` 6,158; `delivery_style` 391; `over_or_around` 407 |
| `competition_team_player_mapping.csv` | None |
| `competitions.csv` | None |
| `matches.csv` | `home_team_captain_id` 44; `away_team_captain_id` 45; `toss_win_team_id` 15; `toss_opted` 15; `first_inn_revised_overs` 858; `second_inn_revised_overs` 858; `revised_target` 860; `win_team_id` 41 |
| `playing_eleven.csv` | `batting_order` 8,678; `is_captain` 8,667; `is_wk` 8,667 |
| `teams.csv` | None |

Nulls in dismissal and extras fields are often structurally expected for ordinary deliveries, but must not be globally imputed without understanding conventions. Roster nulls are substantial and may be concentrated in older seasons or non-playing squad members; profile by competition/season before use. Match revised-innings nulls appear mostly to indicate no revision, not a missing target; distinguish those cases from abandoned/unknown match state.

## 3. Candidate keys and relationships

### Candidate primary keys / uniqueness

- `competitions`: `comp_id` unique (141 rows).
- `matches`: `match_id` unique (883 rows).
- `teams`: `(comp_id, team_id)` unique (353 rows).
- `competition_team_player_mapping`: `(comp_id, team_id, player_id)` unique; 6,413 rows.
- `playing_eleven`: `(match_id, team_id, player_id)` is **not unique** (35 duplicate groups and 40 excess rows). Whole-row duplicates are zero.
- `ball_by_ball_updated`: both `(match_id, innings, innings_ball_num)` and `(match_id, innings, overid, over_ball_num)` are unique in this extract. This is a viable candidate delivery key, subject to confirming ball-number conventions and source lineage.

### Foreign-key/reference checks

- All 883 match `comp_id` values exist in `competitions`.
- All match home/away `(comp_id, team_id)` pairs exist in `teams`; all `teams` competition IDs exist.
- All 6,413 mapping rows refer to an existing competition-team pair.
- All `playing_eleven.match_id` and ball-by-ball `match_id` values exist in `matches`.
- Every playing-eleven team ID is a home/away side in its match; every ball-by-ball batting/bowling team is a distinct side in that match.
- Five `playing_eleven` records do not match a `(comp_id, team_id, player_id)` row in the mapping table. All are for competition 2670, team 4444, player 29833, in matches 37086, 37090, 37093, 37098 and 37099. This may be an incomplete mapping or roster source difference; inspect before treating mapping as a hard player FK.
- Player IDs in deliveries and roster rows have no separate player master table, so player identity/name consistency and stable cross-competition identity cannot be fully verified from these six files.

### Relationship map

```text
competitions (comp_id)
  -> matches (comp_id; match_id)
       -> playing_eleven (match_id; team_id; player_id)
       -> ball_by_ball_updated (match_id; innings; innings_ball_num)
  -> teams (comp_id; team_id)
  -> competition_team_player_mapping (comp_id; team_id; player_id)

teams and competition_team_player_mapping also link on (comp_id, team_id).
playing_eleven is conceptually linked to the mapping through match - comp_id and (team_id, player_id), with the five exceptions above.
```

## 4. Investigation of playing-eleven candidate-key duplicates

The candidate key `(match_id, team_id, player_id)` yields **35 groups** with count > 1. Since 35 groups of size 2 would create 35 excess rows and three groups of size 3 contribute two more each, observed multiplicity accounts for **40 excess rows** (75 total records across groups). This reconciles the prior 40-duplicates figure if it referred to excess rows. It is not 40 duplicated key combinations.

Affected match IDs are `13613`, `21176` and `28962`. Each duplicate group contains two or three rows and differing `batting_order` values. The rows are not exact copies; flags are generally the same within group. The discrepancies can reflect multiple phases/representations (for example, a player with alternate batting position) or a data issue, but the file alone does not establish which. They could multiply joins and corrupt player-match aggregation. Retain all raw rows; in implementation, quarantine/report these groups and resolve the correct player-match semantics before enforcing uniqueness or counting appearances. No deletion or correction was made.

## 5. Cricket-specific data quality and semantics

### Batting and delivery runs

- `runs` takes integer values 0-6; fours and sixes are separately flagged. All observed `is_four=True` rows have `runs=4`, and all `is_six=True` rows have `runs=6`.
- On sampled wides/leg-byes, `runs=0` while `extras1_runs` carries the extra value (for example a wide with `extras1_runs=1`). This suggests `runs` may represent batter runs rather than team total, but the field definition is not supplied. Do not calculate innings totals or pressure from `runs` alone until confirm whether runs means batter runs, delivery total, or another source-specific quantity and reconcile it against extras.
- Nonzero `extras1_runs + extras_2_runs` occurs on 11,833 deliveries. Two such rows have a null `extras_type` (match IDs 17555 and 36097). Extra labels include `wide`, `legbyes`, `byes`, `Overstep`, `other`, and `Penalty`; `Overstep` likely represents no-ball but needs source confirmation. Values of `extras_2_runs` include 0, 1 and 4, so the two extras fields need documented semantics.
- `runs` and extras should be reconciled against total runs, batter runs, legal-ball count, and scorecard/innings totals before using rates or run requirements. Wide/no-ball deliveries should generally not consume a legal ball, but source encoding must be validated.

### Bowling and over/ball sequencing

- `overid` has values 1-20; `over_ball_num` has 1-13; `innings_ball_num` has 1-136. The proposed delivery keys are unique, but `over_ball_num` may count illegal deliveries and the maximum alone does not signal a defect. Validate reconstructed legal overs and innings against cricket rules and scorecards.
- `bowler_id/name`, `bowling_type`, pace/spin, and `bowl_speed` exist. `bowl_speed` is a float with 1,033 distinct values, including 0.0 in the sample; missing/zero speeds and units/radar provenance need interpretation before use. `delivery_style` and field/line-related attributes have some nulls.
- No bowler spell/over summary is supplied; derive only after delivery legality and team-run semantics are resolved.

### Dismissals

- `is_wicket=True` appears with known dismissal type for all observed wicket rows; no false rows have a non-null dismissal type. Dismissal labels include `Caught`, `Bowled`, `LBW`, `RunOut`, `Stump`, `Hit Wicket`, `Retire Out`, and spelling variants `Obstracting the field` / `Obstructing the field`.
- `dismissed_player_id` has a different null pattern: 1 wicket row (a `Retire Out` in match 40709) lacks the ID, while 12 non-wicket rows carry a dismissed-player ID with no dismissal type. Treat those as field-level exceptions; do not infer a dismissal from the ID alone.
- Not all dismissals count as a bowler-credited wicket (run out, retired out, obstruction and other special cases). Do not equate `is_wicket` with bowler wickets or assume all wickets reduce the same way without a dismissal mapping.

### Match state and outcome

- `matches` provides date, stage, venue, sides, toss, revised overs/target, winner and result text. Revised target is present on 23 rows, revised-over fields on 25 rows; `win_team_id` is null on 41 rows. These likely include no-results/ties/abandonments and must be classified explicitly.
- Delivery data supports reconstructing score, wickets, legal balls and chase state only after run/extras semantics are resolved. The match file does not include innings scorecards, target/required runs for ordinary chases, wickets at start, or ball-level win probability. For chasing innings, derive target from first-innings score only if score reconstruction is validated; use `revised_target` and revised overs for affected matches.
- Delivery timestamps are strings such as `2022-01-23 00:00:00 UTC`; the field name says IST but shown value includes UTC. Match dates span `2022-01-22` to `2026-11-01`; delivery timestamps span `2022-01-23 00:00:00 UTC` to `2026-11-01 16:50:46 UTC`. Confirm timezone meaning and match-level consistency.
- Innings values 1-4 occur (innings 3: 25 rows; innings 4: 13 rows). These may represent super overs or unusual innings; identify and handle separately rather than assuming exactly two innings per match.

## 6. Coverage and support for pressure-performance methodology

### Coverage relevant to Rajasthan Royals IPL analysis

- `competitions` contains five IPL seasons: 2022 (74 matches), 2023 (74), 2024 (74), 2025 (75), and 2026 (74), **371 IPL matches total**. The IPL competitions are marked `T20`.
- 367 IPL matches have ball-by-ball records; four do not (three IPL 2024, one IPL 2025). Other competitions contribute the rest of the 883 match records.
- `ball_by_ball_updated` covers 867 distinct matches total. `playing_eleven` covers 880 distinct matches.
- No 2027 competition, auction pool, auction price, player availability/retention, salary/remaining-purse, role demand, or roster-constraint dataset is present. The supplied files alone cannot answer actual 2027 auction decisions.

### What is supportable, conditionally

The delivery table has the core ingredients for retrospective ball-by-ball T20 measures: match/innings/order, batting and bowling identities, teams, runs/extras, wicket markers and match outcomes. With specification and source-field validation, it can support pressure contexts such as innings phase, required runs/balls, wickets in hand, run-rate/required-rate state, and outcome-conditioned player/bowler performance. The roster, competition and match tables can supply season/team/player context.

The current files do **not** define the project's pressure-performance methodology. The project specification was not present among workspace files (only the six CSVs were found). Exact pressure thresholds, scoring weights, minimum sample sizes, role adjustments, player eligibility and auction decision criteria therefore cannot be confirmed. Nor can reliable pressure rates be asserted until run/extras and legal-ball conventions, revised-target handling, missing matches and duplicate roster semantics are addressed. The data can support a carefully bounded retrospective analysis; it does not by itself support fully specified 2027 auction recommendations.

## 7. Recommended implementation plan

1. **Obtain and freeze the methodology specification.** Translate its pressure definition, event windows, outcome measure, exclusions, minimum sample thresholds, role/auction constraints and output requirements into explicit acceptance rules before analysis.
2. **Preserve raw inputs and build a reproducible ingestion layer.** Read CSVs unchanged, retain source columns/rows, record file hashes and parsing rules, parse dates/timestamps explicitly, and use integer IDs as keys rather than labels.
3. **Create a data-quality/exception layer.** Emit non-destructive reports for the 35 duplicate roster keys/40 excess rows, five roster-to-mapping exceptions, 16 match delivery gaps, 2 extras-without-type records, dismissal label spelling variants, missing dismissed IDs, revised/no-result matches, and innings > 2. Do not silently drop or impute exceptions.
4. **Resolve cricket field semantics with the source or scorecard reconciliation.** Establish batter runs vs team runs, extras1/extras_2 definitions, no-ball label/penalty behavior, legal-ball counting, over indexing, dismissal credit/ball legality, revised targets, super overs and timestamp timezone. Reconcile a sample and then totals for complete matches against authoritative scorecards if available.
5. **Build validated match/innings state.** Derive team totals, wickets, legal balls, target, runs/balls remaining, wickets in hand and phases only from validated definitions; treat DLS/revised and super-over cases separately. Flag incomplete-delivery matches.
6. **Implement pressure features exactly as specified.** Keep feature definitions versioned and auditable. Calculate player and bowler performance at the required event grain, apply role/sample-size treatment as specified, and prevent leakage from post-event match outcome into predictors if the design requires prediction.
7. **Validate aggregation and coverage.** Check reconstructed innings and outcomes against available match results and independent scorecards; quantify coverage by season/team/player and sensitivity to missing/ambiguous rows. Maintain an explicit eligible-match/player cohort.
8. **Only then produce RR-focused summaries and auction decision outputs.** Join validated RR seasons and eligible player records to the specified 2027 candidate pool and auction/retention/purse constraints. Keep evidence, uncertainty and exclusions visible; do not infer the candidate pool from historical tables alone.

## 8. Approval checkpoint

This is the initial inspection only. The source CSVs remain unchanged, no rankings have been built, and no analytical pipeline has been started. The full implementation should begin after review of this report and confirmation of the methodology specification and resolution policy for the identified data exceptions.



# Second investigation phase

**Scope:** Row-level investigation of roster exceptions; cricket-score reconstruction checks; match-state feasibility; and a proposed pressure definition. All checks were read-only. No rankings were generated.

## 9. Candidate-key duplicate groups: findings for all 35

The 35 groups occur only in three T20I matches, not in the IPL competitions. Every same-key group has multiple `batting_order` values; all rows have `is_played=True`, with repeated captain/wicketkeeper/impact flags rather than distinct participant identities. This is not a legitimate one-row-per-player-match representation. The source does not say whether the alternate orders are corrupt positions, duplicate scorecard stages, or some other artifact. We therefore classify the groups as **ambiguous source duplicates / likely data-quality errors**, not as verified separate player appearances. No principled rule in these files selects one order.

The delivery table does not resolve them: its `batting_order` for the same player also takes multiple values in these matches. It cannot be used to choose a unique roster order. These matches are non-IPL and can be excluded from the initial IPL cohort, but the underlying data exception should remain visible.

| Match | Team ID | Player ID / mapped name | Conflicting `batting_order` values |
|---:|---:|---|---|
| 13613 | 20 | 223 / Steven Smith | 5, 6 |
| 13613 | 20 | 250 / Aaron Finch | 2, 4 |
| 13613 | 20 | 838 / Glenn Maxwell | 1, 4 |
| 13613 | 20 | 2639 / Marcus Stoinis | 2, 6 |
| 13613 | 20 | 3539 / Ben McDermott | 1, 3 |
| 13613 | 20 | 4736 / Josh Inglis | 3, 5 |
| 13613 | 27 | 1100 / Dinesh Chandimal | 2, 5 |
| 13613 | 27 | 2351 / Danushka Gunathilaka | 2, 4 |
| 13613 | 27 | 2436 / Dasun Shanaka | 1, 6 |
| 13613 | 27 | 4895 / Charith Asalanka | 4, 6 |
| 13613 | 27 | 4902 / Avishka Fernando | 3, 5 |
| 13613 | 27 | 6931 / Pathum Nissanka | 1, 3 |
| 21176 | 17 | 2246 / Tom Latham | 3, 6 |
| 21176 | 17 | 3323 / Jimmy Neesham | 2, 6 |
| 21176 | 17 | 3374 / Mark Chapman | 3, 5 |
| 21176 | 17 | 3700 / Tim Seifert | 2, 5 |
| 21176 | 17 | 4106 / Daryl Mitchell | 1, 4 |
| 21176 | 17 | 25534 / Chad Bowes | 1, 4 |
| 21176 | 27 | 1481 / Kusal Perera | 3, 4 |
| 21176 | 27 | 2407 / Dhananjaya de Silva | 4, 5 |
| 21176 | 27 | 3672 / Kusal Mendis | 1, 2 |
| 21176 | 27 | 4895 / Charith Asalanka | 2, 5 |
| 21176 | 27 | 6931 / Pathum Nissanka | 1, 3 |
| 28962 | 18 | 47 / Virat Kohli | 3, 5 |
| 28962 | 18 | 126 / Rohit Sharma | 1, 2 |
| 28962 | 18 | 2258 / Sanju Samson | 3, 5 |
| 28962 | 18 | 4708 / Rinku Singh | 2, 3, 6 |
| 28962 | 18 | 4755 / Shivam Dube | 4, 6 |
| 28962 | 18 | 6819 / Yashasvi Jaiswal | 1, 2, 4 |
| 28962 | 78 | 1107 / Mohammad Nabi | 1, 3, 5 |
| 28962 | 78 | 2214 / Gulbadin Naib | 1, 3, 4 |
| 28962 | 78 | 5808 / Karim Janat | 3, 4, 6 |
| 28962 | 78 | 6448 / Ibrahim Zadran | 2, 5 |
| 28962 | 78 | 6674 / Rahmanullah Gurbaz | 1, 2 |
| 28962 | 78 | 6676 / Azmatullah Omarzai | 4, 6 |

**Disposition:** In a later implementation, preserve a duplicate-exception table with source row references. Do not collapse these to one player-match row or average the batting orders. The IPL-only analysis can exclude them by competition filter without silently repairing the records.

## 10. Five roster-to-mapping exceptions

All five rows are the same ID/name pair in the same competition/team:

- Competition 2670: *Mens T20 Emerging Teams Asia Cup 2024*; team 4444: *Afghanistan A*.
- Player 29833 is **Bashir Ahmad** in the mapping table for other Afghanistan competitions, confirming a consistent player ID/name elsewhere. There is no mapping row for this player with team Afghanistan A in competition 2670.
- Match IDs are 37086, 37090, 37093, 37098 and 37099. In all five roster records, `is_played=False`; `batting_order`, `is_captain` and `is_wk` are null. The records therefore describe squad/non-playing entries, not five observed appearances. The mapping is likely incomplete for the competition squad or intentionally limited to another roster scope; it is not evidence that the player ID itself is invalid.

**Disposition:** Keep the player identity; flag the missing competition-team membership as a mapping coverage exception. It does not affect delivery-derived player statistics for these matches, and it is outside the IPL cohort. Do not use mapping presence as a hard filter for participation or eligibility.

## 11. Matches without ball-by-ball records

All 16 matches have result text `Match Abandoned`, and all have null `win_team_id`. Thus their missing delivery rows are consistent with no play being recorded, rather than evidence of missing played innings. They remain part of scheduled-match/competition coverage, but contribute no delivery-level performance observations.

### IPL (4 abandoned matches)

| Match | Date | Fixture |
|---:|---|---|
| 31281 | 2024-05-13 | Gujarat Titans vs Kolkata Knight Riders |
| 31284 | 2024-05-16 | Sunrisers Hyderabad vs Gujarat Titans |
| 31288 | 2024-05-19 | Rajasthan Royals vs Kolkata Knight Riders |
| 40761 | 2025-05-17 | Royal Challengers Bengaluru vs Kolkata Knight Riders |

**IPL coverage implication:** The 371 scheduled IPL matches contain ball-by-ball records for 367. Four abandoned matches should be reported in the schedule denominator, but excluded from delivery-level and player-performance denominators. One is an RR fixture (31288); it supplies no pressure or player-event sample.

### Non-IPL (12 abandoned matches)

| Match | Date | Competition | Fixture |
|---:|---|---|---|
| 32622 | 2024-05-20 | Netherlands Tri-Nation T20I Series 2024 | Ireland vs Scotland |
| 32610 | 2024-05-22 | Pakistan in England T20I Series 2024 | England vs Pakistan |
| 32612 | 2024-05-28 | Pakistan in England T20I Series 2024 | England vs Pakistan |
| 36564 | 2024-09-15 | Australia in England T20I Series 2024 | England vs Australia |
| 38797 | 2024-12-14 | Pakistan in South Africa T20I Series 2024 | South Africa vs Pakistan |
| 41502 | 2025-06-12 | West Indies in Ireland T20I Series 2025 | Ireland vs West Indies |
| 41503 | 2025-06-14 | West Indies in Ireland T20I Series 2025 | Ireland vs West Indies |
| 36210 | 2025-09-14 | South Africa in England T20I Series 2025 | England vs South Africa |
| 46008 | 2025-09-19 | England in Ireland T20I series 2025 | Ireland vs England |
| 42030 | 2025-12-17 | South Africa in India T20I Series 2025 | India vs South Africa |
| 48513 | 2026-01-10 | Pakistan in Sri Lanka T20I Series 2026 | Sri Lanka vs Pakistan |
| 50189 | 2026-04-29 | New Zealand in Bangladesh T20I Series 2026 | Bangladesh vs New Zealand |

The non-IPL match set has the same interpretation: scheduled events exist in `matches`, but there are no delivery performance observations to include. Keep these records out of the pressure-event denominator while retaining them in schedule coverage.

## 12. Cricket calculation validation from observed deliveries

### Run components and innings totals

The observed data supports this **candidate accounting identity**:

`team runs on a delivery = runs + extras1_runs + extras_2_runs`

Evidence:

- Ordinary and extra-only examples behave as expected: a wide with `runs=0`, `extras1_runs=1`, `extras_2_runs=0` contributes one team run; a bye with `runs=0`, `extras1_runs=2` contributes two; a leg-bye with `runs=0`, `extras1_runs=4` contributes four.
- An IPL sample (match 14098, 2022-03-29, Rajasthan Royals vs Mumbai Indians) reconstructs innings 1 as `196 + 14 + 0 = 210`, with 130 delivery rows. The chase reconstructs to 149. Match result says Rajasthan Royals won by 61 runs, matching `210 - 149`.
- Across **all 399 non-DLS matches recorded as won by runs** with both innings represented, reconstructed innings totals differ by exactly the stated victory margin in all 399. This is strong internal evidence that the sum of the three run columns reconstructs team runs for ordinary completed results. It is not a provider data dictionary, so keep the formula documented and continue scorecard reconciliation on the eventual IPL cohort.
- Match 13512 similarly reconstructs 171 vs 170 and the recorded England victory by one run.

`runs` behaves as batter runs in observed examples: extras-only deliveries have zero `runs`, while a no-ball delivery can have batter `runs=4` plus a one-run `extras1_runs` penalty. That interpretation is strongly supported by the aggregate checks above, but should be retained as an explicit feed interpretation, not silently assumed from the generic column name.

### Wides, no-balls, byes/leg-byes and legal deliveries

| `extras_type` | Rows | Observed pattern | Accounting treatment supported by records / rules |
|---|---:|---|---|
| `wide` | 7,714 | `extras1_runs` totals 9,174; observed values 1-5; `runs` and `extras_2_runs` are zero in this category. | Team runs include wide extras; bowler is charged wides; wide is not a legal ball. |
| `Overstep` | 576 | `extras1_runs=1` on every row; `runs` can also be nonzero; `extras_2_runs` is nonzero on 48 rows. | Strongly consistent with no-ball: one penalty run plus any batter runs. Likely no-ball, but confirm provider meaning. No-ball is not a legal ball. The 48 additional `extras_2_runs` need a field definition before assigning bowler cost. |
| `byes` | 529 | `runs=0`; `extras1_runs` totals 1,000. | Team extras, not runs credited to batter or bowler; legal-ball status is ordinarily legal absent a no-ball/wide marker. |
| `legbyes` | 2,748 | `runs` is 0 on almost all rows; `extras1_runs` totals 3,603. | Team extras, not batter or bowler runs; ordinarily legal absent an illegal-delivery marker. |
| `other` | 264 | `extras1_runs` totals 264; `extras_2_runs` is nonzero on 35 rows; includes a run-out. | Meaning and bowler/legal-ball treatment unresolved. Keep as exception until defined. |
| `Penalty` | 1 | `extras1_runs=5`. | Team penalty run; do not charge bowler. Delivery legality cannot be decided from this label alone. |
| null | 189,167 | Two rows have nonzero extra fields despite null `extras_type` (match 17555 has `extras_2_runs=1`; match 36097 has `extras1_runs=1`). | These two records require exception handling; type and legal-ball/bowler treatment cannot be inferred. |

In match 14098 innings 1, there are 130 recorded deliveries, including six wides and four `Overstep` rows. Excluding those ten gives 120 candidate legal balls, exactly 20 overs. This validates the basic method on a complete sample. Across the full set, `innings_ball_num` counts recorded deliveries and must **not** be treated directly as legal balls. Proposed legal-ball counting is to exclude `wide` and confirmed no-ball/`Overstep` deliveries; do not apply this to `other`, null extras, or penalty cases until their semantics are known. ICC playing conditions state that wides and no-balls do not count in the over; they also specify bowler charging for wide and no-ball penalty runs, and distinguish byes/leg-byes. See [ICC T20I Clause 17: The Over](https://www.icc-cricket.com/news/mens-t20i-match-clause-17-the-over), [Clause 18: Scoring Runs](https://www.icc-cricket.com/news/mens-t20i-match-clause-18-scoring-runs), [Clause 21: No Ball](https://www.icc-cricket.com/news/mens-t20i-match-clause-21-no-ball), and [Clause 22: Wide Ball](https://www.icc-cricket.com/news/mens-t20i-match-clause-22-wide-ball). These are rule references; the source's encoding still needs confirmation.

### Bowler-conceded runs

A provisional rule-based calculation would charge the bowler for batter runs, wides, and no-ball penalty runs; it would exclude byes, leg-byes, and penalty runs. `Overstep` rows consistently carry the one-run extra expected for no-ball, and wide rows carry their extra amount. But `extras_2_runs` on 48 no-balls and 35 `other` records is not classified; two rows have missing `extras_type`. Therefore **bowler-conceded runs are not fully reliable across the raw feed yet**. For the initial IPL cohort, validate these cases and category totals against scorecards before creating economy or conceded-run features. Until then, report a provisional formula and an unresolved-extra count separately.

### Dismissals and bowler-creditable wickets

There are **10,881** rows with `is_wicket=True`; all have a non-null dismissal type. One `Retire Out` row (match 40709) lacks `dismissed_player_id`. Separately, 12 non-wicket records have a populated `dismissed_player_id` despite null dismissal ID/type; they should not count as wickets.

Observed dismissal counts include Caught 7,557; Bowled 1,775; LBW 709; RunOut 600 (including run-outs on wide/no-ball/other extras); Stump 214; Hit Wicket 17; Retire Out 6; and obstruction spelling variants 3. A candidate bowler-creditable set is **10,272**: Caught, Bowled, LBW, Stump, and Hit Wicket. RunOut, Retire Out, and obstruction should not be credited to the bowler. This follows the standard scoring distinction; see [ICC T20I Clause 38: Run Out](https://www.icc-cricket.com/news/mens-t20i-match-clause-38-run-out). Keep `is_wicket` as wickets lost for match state, but use a dismissal-type mapping for bowler wickets.

### Innings, super overs and revised-target limitations

- Six matches have innings 3 and 4, with 25 and 13 delivery records respectively. All six results explicitly identify a Super Over: matches 34429, 40725, 45512, 48027, 48029 and 50359. Exclude these innings from regulation chase-rate/pressure analysis; preserve them as separate tie-breaker phases.
- `revised_target` is non-null on 23 matches. Revised-overs fields are non-null on 25 matches each (34 matches have at least one of the three revision fields). Their values are 30-114 and **all are multiples of six** (for example, 114, 90 and 48), strongly suggesting legal-ball allocations despite the `_overs` column name (114 likely means 19 overs, not 114 overs). In sample matches these values align with legal-ball counts or stated match lengths. Do not divide by six or treat as overs in implementation until the provider confirms units; store original value and an explicitly converted, validated balls allocation.
- DLS/revised matches cannot be given a fully correct ball-by-ball target history from `matches` alone. A final revised target does not capture the timing of interruptions or possible changing targets/par scores. ICC playing conditions provide for targets recalculated after interruptions, and the DLS method considers overs and wickets/resources; see [ICC DLS overview](https://www.icc-cricket.com/about/cricket/rules-and-regulations/duckworth-lewis-stern). Exclude DLS/revised matches from the primary pressure cohort unless delivery-time target/par data are obtained or the full target history is independently reconstructed.
- For non-revised regulation matches, first-innings reconstructed total + 1 is a defensible second-innings target, subject to completion and score validation. A tie or a super over is a distinct outcome; do not manufacture a conventional chase target in those cases.

## 13. Match-state reconstruction feasibility

| State quantity | Support from these files | Conditions / limitations |
|---|---|---|
| Current team score before a delivery | Strong, using cumulative `runs + extras1_runs + extras_2_runs` | Validate the exception extras and sequence; exclude abandoned/no-delivery matches. State is pre-delivery by summing rows before the current row. |
| Batter runs | Strong candidate from `runs` | Observed consistency supports it, but retain feed definition as a documented assumption and reconcile player scorecards. |
| Wickets lost / wickets remaining | Supported from cumulative `is_wicket`; remaining = 10 minus wickets lost | Super overs separate; run-out and other dismissals count as wickets lost even when not bowler-credited. Check whether innings starts with 10 available batters for the competition. |
| Legal balls faced / balls remaining | Derivable, not directly supplied | Exclude confirmed wides/no-balls; uncertain `other`, missing extras type and penalty encodings need adjudication. For standard full IPL innings, scheduled allowance is 120 legal balls. For revised matches, verify converted allocation. |
| Target / runs required | Supported for clean regulation chases after first innings reconstruction | Use verified `revised_target` only if the match has a stable official target; absent interruption timing means revised/DLS cases should be excluded from the initial state model. `runs_required = max(target - score_before, 0)`; stop pressure observations after target is reached. |
| Required run rate | Derivable if target and legal balls remaining are valid | `runs_required * 6 / legal_balls_remaining`; undefined if no balls remain, zero after target is reached, and not a DLS resource/par-rate. |
| Current run rate | Derivable from reconstructed team score and legal balls bowled | Undefined at zero legal balls. Does not represent expected/par score. |
| Phase (powerplay/middle/death) | Derivable from legal-ball number for standard IPL | Phase boundaries should follow the official IPL format for the season; keep revised innings separate. |
| Innings 1 pressure / par score | Not directly supported | Requires an explicit expected-score baseline/model (venue, season, innings resources, wickets) or an external par-score source. Do not label first-innings events "pressure" from current score alone. |

## 14. Recommended pressure-identification method

Use a narrowly defined, auditable **chase-pressure state** first. This method is supported by the fields after validation and avoids pretending to estimate win probability.

1. **Cohort:** IPL competitions only (`comp_name` IPL seasons 2022-2026), regulation second innings with complete ball data, no abandoned/no-result match, no Super Over, no DLS/revised target/overs in the primary cohort, and no unresolved extras affecting the event's run/legal-ball state. Keep T20I and other T20 competitions in separate analyses and never pool their events into IPL summaries.
2. **Before-delivery state:** Sort by `(match_id, innings, innings_ball_num)`. For each delivery, calculate the state using only earlier deliveries in that innings: team score, wickets lost, legal balls used, and current batters/bowler. This prevents the delivery's outcome leaking into its own pressure classification.
3. **Target:** In a standard chase, use validated first-innings team total + 1. Confirm first/second innings sides and winner against `matches`; exclude tied/no-result cases and the six super-over matches from primary chase performance.
4. **Remaining state:** `runs_required = target - pre_delivery_score`; `balls_remaining = 120 - legal_balls_used` for a standard 20-over innings; `wickets_remaining = 10 - wickets_lost`. Clamp/report only where rules require and mark innings that are already complete. Required run rate is `6 * runs_required / balls_remaining` when balls remain and runs are still required.
5. **Pressure indicator:** Keep the primary pressure signal continuous: **required-rate pressure margin = current required run rate minus the chase's opening required run rate** (`6 * target / 120`). A positive value means the batting side is behind the rate needed from the start; a larger positive margin indicates greater scoring-rate stress. Publish it alongside runs/balls/wickets remaining, not as a standalone opaque score. `RRR > 6` can be reported as a transparent "more than one per legal ball required" marker, but should not be presented as the whole pressure definition.
6. **Outcomes:** For batting, retain batter runs, boundary, and dismissal outcomes per delivery; for bowling, retain conceded runs after exception resolution, dot balls, and bowler-creditable wicket outcomes. Aggregate only after minimum sample sizes and role definitions are approved. Do not define a player score or ranking without the project spec.
7. **Binary high-pressure labels:** Do not invent a weighted index or arbitrary "clutch" cutoff. If a binary label is required, pre-register the pressure-margin threshold and late-innings window in the methodology specification, then publish sensitivity at nearby thresholds. A data-derived percentile can be an exploratory sensitivity check, not the primary label.
8. **First innings:** Exclude from primary pressure identification until an expected-score/par baseline is specified and validated using historical IPL innings. Required rate alone does not define pressure when no target exists.
9. **DLS:** Exclude from primary state/pressure calculations until ball/time-specific target and par score history is available. Keep any eventual DLS analysis separate and label its target source.

This output is a state and event framework, not a player ranking. It distinguishes observed pressure conditions from performance outcomes and makes every calculated field reproducible.

## 15. IPL and other T20 analysis separation

- Define the IPL cohort only from competition records matching the actual IPL competitions (`IPL 2022` through `IPL 2026`; 371 match records, 367 with ball-by-ball). Confirm competition IDs from the table rather than filtering the entire dataset by `match_format='T20'`.
- Keep other `T20` tournaments and all `T20I` competitions separate. T20I and franchise IPL player roles, opposition depth, selection, rules/season conditions and match environments are not interchangeable by default.
- Use non-IPL data only as a separately labelled supplementary benchmark if the specification authorizes it, with competition-format/season effects and eligibility stated. Never let it silently increase an IPL player's pressure sample count.
- Exclude the 16 abandoned matches from delivery observations, but report them in scheduled-match coverage (4 IPL and 12 non-IPL). Exclude Super Overs and revised/DLS matches from primary regulation-pressure cohorts as described above.

## 16. Additional inputs required for genuine IPL 2027 auction recommendations

These six files do not contain an auction candidate list or team-budget/roster constraints. At minimum, obtain:

- Official 2027 auction player pool and player identifiers, plus auction/retention/release status and team-specific eligibility.
- Rajasthan Royals' retained/released players, current squad, contract/retention values, purse remaining, roster slots, overseas-player slots, and role gaps.
- Official 2027 auction rules: purse, squad-size limits, overseas limits, RTM/retention rules, replacement rules and any impact-player provisions. Use the official season documents once issued rather than projecting current rules into 2027.
- Player availability for the 2027 season: international commitments/NOCs, expected availability windows, injury/fitness status, workload limits and relevant role/position information.
- A current player identity/profile source for age, handedness, bowling type, wicketkeeping, domestic/capped status and role; the six files lack a standalone player master, and `batting_order` is inconsistent in the roster duplicates.
- If pressure performance is intended to be predictive rather than descriptive: independent validation seasons, a benchmark/expected-score or win-probability design, explicit outcome horizon, uncertainty/minimum-sample treatment and leakage controls.
- The project specification itself: exact pressure definition, score/weighting, sample thresholds, role adjustments, availability assumptions, and decision objective (best available player, role fit, expected value, or budget allocation).

## 17. Final implementation plan and approval gate

1. Obtain and version the methodology specification and official 2027 auction/retention constraints before any ranking logic.
2. Create a read-only, reproducible input manifest (source paths, file hashes, row counts, parsing/date rules) and preserve raw columns/records.
3. Implement data-quality outputs first: roster duplicates, the five membership exceptions, abandoned/no-ball match coverage, extra-field exceptions, dismissal ID/type inconsistencies, revision-field unit ambiguity, and super-over identification.
4. Confirm field semantics with the data provider or authoritative scorecard-level evidence: `runs`, `extras1_runs`, `extras_2_runs`, `Overstep`, `other`, `Penalty`, legal-ball count and revised-allocation units. Reconcile IPL season totals and sample innings before producing player aggregates.
5. Build an IPL-only clean regulation-match/innings layer. Exclude abandoned/no-result, Super Over and unresolved/revised cases from primary pressure calculations, while emitting explicit coverage counts and keeping separate analytical cohorts for any subsequently approved exceptions.
6. Derive pre-delivery match state and the chase-pressure margin described above; preserve pressure variables and event outcomes as separate columns. Validate score and result reconstruction on the eligible IPL cohort.
7. Add a separate non-IPL T20/T20I benchmark only if authorized; report its coverage and never pool it invisibly with IPL.
8. Join the approved 2027 player pool and RR constraints; only then create player comparisons, uncertainty/sample-size reporting, and auction recommendations.

**Approval checkpoint:** This second phase only updates the inspection and recommended method. No raw data changed and no player rankings or implementation code were created. Proceed to full implementation only after review and approval of the pressure definition, exception policy, and requested 2027 inputs.


## Implementation addendum: striker-order corroboration (2026-11-16)

The implementation phase tested the 35 repeated roster keys against **striker rows only** in `ball_by_ball_updated.csv`. In this feed, `batting_order` describes the striker on that delivery; values on rows where a player is the non-striker describe the other batter and must not be used as that player's batting order. The striker-only check finds one unique observed order matching exactly one roster candidate in **all 35 groups**. This corroborates an analytical row selection, but it is not a provider correction.

The earlier second-phase statement that delivery records did not resolve the orders was too broad; it compared player appearances as both striker and non-striker. The corrected group-size distribution is **30 pairs and 5 triples**, accounting for 40 excess rows (not three triple groups). The pipeline flags one corroborated candidate per group and retains all 75 original duplicate-group records with source-row and selection flags.
