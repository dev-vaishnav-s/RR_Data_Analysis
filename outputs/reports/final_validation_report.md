# Final Validation Report

**Status:** PASSED  
**Executed:** 2026-11-16T15:55:23.504406+00:00  
**Notebook:** passed via IPython InteractiveShell; notebook cells 2/2 executed

## Checks

| Check | Status | Detail |
|---|---|---|
| required_deliverables_exist | PASS | missing=[] |
| original_source_hashes_unchanged | PASS | All six source CSV SHA-256 hashes match pre-run manifest |
| integrated_delivery_row_count | PASS | integrated=200,999; source=200,999 |
| integrated_row_unique_delivery_key | PASS | m:1 joins preserve one row per source delivery |
| pressure_rows_have_valid_pre_state | PASS | pressure rows=24,844 |
| primary_excludes_revised_and_superovers | PASS | No DLS/revised match or Super Over in primary pressure rows |
| pressure_only_ipl | PASS | Primary pressure events are IPL-only |
| batter_ranking_sample_gates | PASS | rows=10; minimum=30 pressure balls and 5 innings |
| batter_ranking_max_ten | PASS | rows=10 |
| bowler_ranking_sample_gates | PASS | rows=10; minimum=60 pressure balls and 5 innings |
| bowler_ranking_max_ten | PASS | rows=10 |
| non_dls_run_margin_reconciliation | PASS | 399/399 run wins exactly reconcile |
| powerpoint_opens_and_slide_count | PASS | slides=26 |
| powerpoint_contains_chart_images | PASS | embedded images=9 |
| chart_assets_exist | PASS | count=14 |
| notebook_execution | PASS | passed via IPython InteractiveShell; notebook cells 2/2 executed |

## Final interpretation

All checks are executable validations of source preservation, join cardinality, state eligibility, ranking gates, result-margin reconciliation, notebook execution and presentation integrity. Passing these checks does not resolve provider-specific `other` / `extras_2_runs` definitions or missing 2027 auction inputs.