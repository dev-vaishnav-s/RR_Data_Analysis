# Cricket Pressure Performance Analytics — Results Summary

## Scope and cautions

Historical IPL 2022-2026 data only. Primary pressure cohort has 354 regulation matches and 24,844 pre-delivery states labelled pressure. Other T20/T20I competitions are reported separately, not pooled into these rankings. The pressure condition is current required run rate above the opening required run rate. It measures a chase falling behind its initial pace, not psychological state or win probability.

The player composite is cohort-relative. Batters require at least 30 pressure balls across five pressure innings; bowlers require at least 60 classified pressure legal balls across five pressure innings. Batter strike rate and dot rate shrink to the eligible cohort mean using 30 prior balls; boundary-run share uses 300 prior batter runs. Bowler economy, wicket rate and dot rate use 60 prior legal balls. The components receive equal one-third weights after standardization. Bowler runs are provisional where `other` extras remain unresolved; see sensitivity and limitations below. Historical performance does not guarantee future results.

## Top pressure-performing batters

| rank | player_name | pressure_score | pressure_runs | pressure_balls | pressure_innings | pressure_dismissals | pressure_strike_rate | pressure_average | pressure_dot_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Vaibhav Sooryavanshi | 1.87 | 102 | 39 | 10 | 3 | 261.54 | 34.00 | 33.33 |
| 2 | Vipraj Nigam | 1.61 | 101 | 47 | 5 | 3 | 214.89 | 33.67 | 21.28 |
| 3 | Ryan Rickelton | 1.35 | 180 | 92 | 12 | 6 | 195.65 | 30.00 | 33.70 |
| 4 | Naman Dhir | 1.31 | 174 | 90 | 12 | 6 | 193.33 | 29.00 | 27.78 |
| 5 | Cooper Connolly | 1.20 | 115 | 57 | 6 | 1 | 201.75 | 115.00 | 33.33 |
| 6 | Dinesh Karthik | 1.19 | 245 | 135 | 12 | 7 | 181.48 | 35.00 | 22.96 |
| 7 | Yashasvi Jaiswal | 1.17 | 534 | 313 | 30 | 13 | 170.61 | 41.08 | 32.59 |
| 8 | Tim David | 1.15 | 252 | 136 | 17 | 10 | 185.29 | 25.20 | 27.21 |
| 9 | Mahipal Lomror | 1.14 | 109 | 58 | 6 | 5 | 187.93 | 21.80 | 25.86 |
| 10 | Ashutosh Sharma | 1.05 | 270 | 151 | 13 | 5 | 178.81 | 54.00 | 29.14 |

## Top pressure-performing bowlers

| rank | player_name | pressure_score | pressure_legal_balls | pressure_innings | pressure_economy | pressure_wickets | pressure_wickets_per_100_balls | pressure_dot_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Eshan Malinga | 1.71 | 108 | 9 | 7.67 | 13 | 12.04 | 41.67 |
| 2 | Mohsin Khan | 1.56 | 197 | 15 | 8.10 | 17 | 8.63 | 46.70 |
| 3 | Prasidh Krishna | 1.48 | 376 | 22 | 7.88 | 24 | 6.38 | 48.67 |
| 4 | Mohit Sharma | 1.45 | 199 | 13 | 8.05 | 23 | 11.56 | 34.67 |
| 5 | Anshul Kamboj | 1.38 | 126 | 9 | 7.19 | 9 | 7.14 | 46.83 |
| 6 | Matheesha Pathirana | 1.12 | 255 | 16 | 8.07 | 19 | 7.45 | 41.57 |
| 7 | Josh Hazlewood | 1.11 | 327 | 20 | 8.59 | 24 | 7.34 | 43.73 |
| 8 | Wayne Parnell | 1.09 | 82 | 5 | 7.61 | 6 | 7.32 | 46.34 |
| 9 | Khaleel Ahmed | 0.96 | 290 | 21 | 8.52 | 17 | 5.86 | 46.21 |
| 10 | Jofra Archer | 0.96 | 144 | 12 | 8.88 | 10 | 6.94 | 47.22 |

## Sensitivity

Pressure threshold and legality variation are compared with the primary top ten. Low overlap indicates that a leaderboard should be interpreted as a screen, not a stable ordering. The complete scenario leaderboard and rank correlations are saved under `outputs/rankings/`.

**Batter scenarios:**

| scenario | role | top10_overlap | spearman_rank_correlation | eligible_primary | eligible_scenario |
| --- | --- | --- | --- | --- | --- |
| margin_at_least_2 | batter | 2 | 0.85 | 126 | 65 |
| valid_state_top_quartile_margin_3.100 | batter | 2 | 0.83 | 126 | 49 |
| other_extras_treated_illegal | batter | 9 | 0.99 | 126 | 129 |
| scoring_first_weights | batter | 8 | 0.99 | 126 | 126 |

**Bowler scenarios:**

| scenario | role | top10_overlap | spearman_rank_correlation | eligible_primary | eligible_scenario |
| --- | --- | --- | --- | --- | --- |
| margin_at_least_2 | bowler | 4 | 0.74 | 99 | 43 |
| valid_state_top_quartile_margin_3.100 | bowler | 3 | 0.68 | 99 | 38 |
| other_extras_treated_illegal | bowler | 8 | 0.98 | 99 | 108 |
| wicket_first_weights | bowler | 8 | 0.97 | 99 | 99 |

## Death-over performance (separate from pressure)

Death overs are scheduled one-based overs 16-20. Overall death leader screens require at least 30 balls across five death-over innings; the pressure-only screens require at least 20 batter balls or 30 bowler legal balls across three pressure-death innings.

**Overall death-over batters (by strike rate):**

| player_name | runs | balls | innings | strike_rate | boundary_run_share_pct | dot_pct |
| --- | --- | --- | --- | --- | --- | --- |
| Quinton de Kock | 154 | 64 | 7 | 240.62 | 79.22 | 18.75 |
| Liam Livingstone | 341 | 153 | 18 | 222.88 | 80.35 | 24.84 |
| Rajat Patidar | 267 | 124 | 19 | 215.32 | 81.65 | 27.42 |
| Dewald Brevis | 88 | 41 | 6 | 214.63 | 81.82 | 29.27 |
| Glenn Maxwell | 176 | 82 | 11 | 214.63 | 80.68 | 25.61 |
| Shreyas Iyer | 444 | 207 | 25 | 214.49 | 77.48 | 22.22 |
| Yashasvi Jaiswal | 88 | 42 | 5 | 209.52 | 81.82 | 28.57 |
| Rishabh Pant | 347 | 167 | 18 | 207.78 | 76.66 | 28.14 |
| Donovan Ferreira | 192 | 94 | 13 | 204.26 | 80.21 | 34.04 |
| Marcus Stoinis | 528 | 261 | 31 | 202.30 | 77.27 | 25.67 |

**Overall death-over bowlers (by economy):**

| player_name | legal_balls | innings | runs_conceded | wickets | economy | dot_pct |
| --- | --- | --- | --- | --- | --- | --- |
| Sunil Narine | 204 | 33 | 208 | 18 | 6.12 | 40.20 |
| Jasprit Bumrah | 387 | 43 | 470 | 28 | 7.29 | 32.30 |
| Piyush Chawla | 30 | 5 | 37 | 2 | 7.40 | 43.33 |
| Wanindu Hasaranga | 108 | 18 | 135 | 12 | 7.50 | 38.89 |
| Nandre Burger | 63 | 11 | 83 | 6 | 7.90 | 44.44 |
| Axar Patel | 72 | 12 | 98 | 1 | 8.17 | 27.78 |
| Noor Ahmad | 151 | 22 | 208 | 13 | 8.26 | 40.40 |
| Kuldeep Yadav | 220 | 36 | 309 | 16 | 8.43 | 32.73 |
| Lungi Ngidi | 116 | 12 | 165 | 9 | 8.53 | 32.76 |
| Maheesh Theekshana | 144 | 23 | 205 | 11 | 8.54 | 31.94 |

**Death-over batting under identified pressure:**

| player_name | runs | balls | innings | strike_rate |
| --- | --- | --- | --- | --- |
| Jos Buttler | 71 | 30 | 3 | 236.67 |
| Rinku Singh | 322 | 139 | 10 | 231.65 |
| Rishabh Pant | 59 | 26 | 4 | 226.92 |
| Rashid Khan | 193 | 90 | 13 | 214.44 |
| David Miller | 223 | 106 | 17 | 210.38 |
| Sam Curran | 61 | 29 | 6 | 210.34 |
| Shubham Dubey | 103 | 49 | 7 | 210.20 |
| Ashutosh Sharma | 170 | 82 | 10 | 207.32 |
| Heinrich Klaasen | 87 | 42 | 5 | 207.14 |
| Tim David | 206 | 100 | 14 | 206.00 |

**Death-over bowling under identified pressure:**

| player_name | legal_balls | innings | runs | wickets | economy |
| --- | --- | --- | --- | --- | --- |
| Kuldeep Yadav | 42 | 7 | 39 | 7 | 5.57 |
| Jamie Overton | 30 | 3 | 30 | 3 | 6.00 |
| Maheesh Theekshana | 49 | 9 | 49 | 4 | 6.00 |
| Noor Ahmad | 42 | 7 | 45 | 4 | 6.43 |
| Varun Chakravarthy | 61 | 11 | 68 | 9 | 6.69 |
| Mohammed Shami | 45 | 8 | 51 | 4 | 6.80 |
| Sunil Narine | 51 | 9 | 58 | 4 | 6.82 |
| Anshul Kamboj | 38 | 5 | 48 | 5 | 7.58 |
| Wanindu Hasaranga | 47 | 8 | 60 | 4 | 7.66 |
| Josh Hazlewood | 111 | 12 | 142 | 13 | 7.68 |

## Consistency screens

These descriptive screens sort players by lower standard deviation in innings strike rate (batters) or innings economy (bowlers), after at least ten IPL innings. Low variance is not automatically high quality; read it with the mean rate and opportunity.

**Batters:**

| player_name | innings | balls | mean_strike_rate | sd_strike_rate | runs_cv_pct |
| --- | --- | --- | --- | --- | --- |
| Daryl Mitchell | 15 | 267 | 123.16 | 35.31 | 70.64 |
| Sai Sudharsan | 57 | 1,686 | 138.74 | 38.00 | 64.52 |
| Kane Williamson | 14 | 258 | 78.39 | 38.62 | 100.31 |
| Matthew Wade | 11 | 144 | 109.25 | 41.28 | 73.16 |
| Shikhar Dhawan | 30 | 757 | 114.49 | 41.38 | 85.66 |
| Kartik Sharma | 11 | 216 | 131.47 | 45.66 | 78.41 |
| Angkrish Raghuvanshi | 30 | 608 | 136.21 | 46.60 | 74.18 |
| Manish Pandey | 21 | 371 | 100.82 | 48.85 | 76.07 |
| Aiden Markram | 60 | 1,114 | 119.87 | 49.18 | 76.61 |
| Mayank Agarwal | 30 | 491 | 111.05 | 49.29 | 90.41 |

**Bowlers:**

| player_name | innings | legal_balls | mean_economy | sd_economy |
| --- | --- | --- | --- | --- |
| Zeeshan Ansari | 10 | 204 | 9.79 | 0.94 |
| Nathan Ellis | 14 | 312 | 8.74 | 1.65 |
| Azmatullah Omarzai | 18 | 354 | 9.65 | 1.70 |
| Maheesh Theekshana | 38 | 876 | 8.29 | 1.87 |
| Ravichandran Ashwin | 53 | 1,212 | 8.07 | 1.91 |
| Dwayne Bravo | 10 | 209 | 8.61 | 1.92 |
| Prince Yadav | 20 | 449 | 9.12 | 1.97 |
| Kumar Kartikeya Singh | 16 | 282 | 8.83 | 2.00 |
| Jason Behrendorff | 12 | 252 | 9.33 | 2.21 |
| Brijesh Sharma | 13 | 277 | 9.67 | 2.35 |

## Season-level context

| season | innings | matches | mean_innings_runs | median_innings_runs | mean_runs_per_over | mean_wickets_lost |
| --- | --- | --- | --- | --- | --- | --- |
| 2022 | 148 | 74 | 164.80 | 162.50 | 8.52 | 6.16 |
| 2023 | 147 | 74 | 174.75 | 178.00 | 8.97 | 6.22 |
| 2024 | 142 | 71 | 182.89 | 179.50 | 9.59 | 6.22 |
| 2025 | 146 | 74 | 181.53 | 186.00 | 9.60 | 5.95 |
| 2026 | 147 | 74 | 186.73 | 194.00 | 9.87 | 5.97 |

## Rajasthan Royals context and conditional recommendation

| view | pressure_events | matches | runs_or_conceded | balls_or_legal_balls | rate_per_100_or_economy | wickets |
| --- | --- | --- | --- | --- | --- | --- |
| RR batting in eligible chases | 2,347 | 34 | 3,431 | 2,255 | 152.15 | 134 |
| RR bowling in eligible chases | 3,146 | 37 | 4,308 | 2,996 | 8.63 | 149 |

**Conditional historical screen, not an availability claim:** use role-fit evidence to check pressure batters (Vaibhav Sooryavanshi, Vipraj Nigam, Ryan Rickelton, Naman Dhir, Cooper Connolly) and pressure bowlers (Eshan Malinga, Mohsin Khan, Prasidh Krishna, Mohit Sharma, Anshul Kamboj) against the official 2027 auction pool, verified availability, RR retention list and purse once those records exist. The data does not establish current squad gaps, auction eligibility or affordability, so these names are research leads only. Profile-first priorities are a reliable top-order chase batter, a middle/death finisher, and a bowler who combines pressure dot-ball control with wickets; current RR roster needs must be verified.

## Machine learning

K-Means was tested only as an exploratory player-profile tool, separately for batters and bowlers, using scaled IPL performance rates and a minimum overall workload (150 batter balls / 120 bowler legal balls). The candidate cluster count was selected by silhouette score over k=2..5. No supervised model is used: the files contain no auction success or future performance target, and an auction recommendation target would be leakage-prone / unobserved.

```json
{
  "supervised_prediction": "not implemented: no auction success or future performance target is supplied",
  "batters": {
    "role": "batter",
    "status": "exploratory",
    "n_players": 120,
    "best_k": 5,
    "best_silhouette": 0.26817501109115577,
    "candidate_silhouettes": {
      "2": 0.2497581473602096,
      "3": 0.2562478704301914,
      "4": 0.26211373908098323,
      "5": 0.26817501109115577
    },
    "cluster_means": {
      "1": {
        "strike_rate": 150.68,
        "batting_average": 39.61,
        "boundary_run_share_pct": 62.15,
        "dot_ball_pct": 29.14
      },
      "2": {
        "strike_rate": 148.44,
        "batting_average": 26.77,
        "boundary_run_share_pct": 69.69,
        "dot_ball_pct": 36.95
      },
      "3": {
        "strike_rate": 107.22,
        "batting_average": 16.52,
        "boundary_run_share_pct": 52.85,
        "dot_ball_pct": 41.34
      },
      "4": {
        "strike_rate": 181.39,
        "batting_average": 33.45,
        "boundary_run_share_pct": 76.73,
        "dot_ball_pct": 33.22
      },
      "5": {
        "strike_rate": 140.62,
        "batting_average": 24.02,
        "boundary_run_share_pct": 59.72,
        "dot_ball_pct": 31.62
      }
    },
    "features": [
      "strike_rate",
      "batting_average",
      "boundary_run_share_pct",
      "dot_ball_pct"
    ]
  },
  "bowlers": {
    "role": "bowler",
    "status": "exploratory",
    "n_players": 146,
    "best_k": 5,
    "best_silhouette": 0.26756533290577045,
    "candidate_silhouettes": {
      "2": 0.25316566179338806,
      "3": 0.23814199002768202,
      "4": 0.24323831269883886,
      "5": 0.26756533290577045
    },
    "cluster_means": {
      "1": {
        "economy": 9.77,
        "wickets_per_100_balls": 3.53,
        "dot_ball_pct": 27.8
      },
      "2": {
        "economy": 10.21,
        "wickets_per_100_balls": 4.71,
        "dot_ball_pct": 34.14
      },
      "3": {
        "economy": 9.62,
        "wickets_per_100_balls": 6.9,
        "dot_ball_pct": 30.72
      },
      "4": {
        "economy": 9.2,
        "wickets_per_100_balls": 5.59,
        "dot_ball_pct": 40.08
      },
      "5": {
        "economy": 8.29,
        "wickets_per_100_balls": 4.77,
        "dot_ball_pct": 33.05
      }
    },
    "features": [
      "economy",
      "wickets_per_100_balls",
      "dot_ball_pct"
    ]
  }
}
```

## Limitations

- No verified 2027 auction pool, RR retention/squad state, purse, role-slot constraints, or player availability was supplied. No player is described as available for auction.
- No 2027 auction prices or budget recommendations are produced.
- `extras_type=other` and `extras_2_runs` semantics are not supplied. Some bowling rates are explicitly provisional and tested with alternate treatment.
- DLS/revised-target matches and Super Overs are excluded from primary pressure analysis; revised-over units appear to be balls but are not used.
- Minimum samples reduce small-opportunity noise but do not eliminate selection bias, role/venue/opposition differences, or historical-to-future uncertainty.
- The ranking composite is descriptive; weights, pressure cutoffs and cohort selection materially affect ranks.
