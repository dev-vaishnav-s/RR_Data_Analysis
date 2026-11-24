"""Final artifact and analytic invariant checks."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pptx import Presentation

from .data_pipeline import ROOT, OUT, sha256


def validate_outputs(notebook_execution: str = "not yet executed") -> dict:
    checks=[]; errors=[]
    def check(name, ok, detail=""):
        checks.append({"check":name,"passed":bool(ok),"detail":str(detail)})
        if not ok: errors.append(name)
    required=[
        "README.md","requirements.txt","main.py","notebooks/cricket_pressure_analysis.ipynb",
        "outputs/processed/integrated_delivery_dataset.csv","outputs/processed/delivery_state_analytics.csv",
        "outputs/processed/ipl_batter_performance.csv","outputs/processed/ipl_bowler_performance.csv",
        "outputs/processed/ipl_innings_summary.csv","outputs/processed/ipl_pressure_delivery_events.csv",
        "outputs/rankings/top_10_pressure_batters.csv","outputs/rankings/top_10_pressure_bowlers.csv",
        "outputs/reports/data_quality_report.md","outputs/reports/analysis_summary.md",
        "outputs/presentation/cricket_pressure_analytics_presentation.pptx",
    ]
    missing=[f for f in required if not (ROOT/f).exists()]
    check("required_deliverables_exist",not missing,f"missing={missing}")
    if (OUT/"processed"/"input_manifest.json").exists():
        manifest=json.loads((OUT/"processed"/"input_manifest.json").read_text(encoding="utf-8"))
        source_ok=all(sha256(ROOT/"data"/f)==info["sha256"] for f,info in manifest["inputs"].items())
        check("original_source_hashes_unchanged",source_ok,"All six source CSV SHA-256 hashes match pre-run manifest")
        integrated=pd.read_csv(OUT/"processed"/"integrated_delivery_dataset.csv",low_memory=False)
        check("integrated_delivery_row_count",len(integrated)==manifest["inputs"]["ball_by_ball_updated.csv"]["rows"],f"integrated={len(integrated):,}; source={manifest['inputs']['ball_by_ball_updated.csv']['rows']:,}")
        check("integrated_row_unique_delivery_key",not integrated.duplicated(["match_id","innings","innings_ball_num"]).any(),"m:1 joins preserve one row per source delivery")
        pressure=pd.read_csv(OUT/"processed"/"delivery_state_analytics.csv",low_memory=False)
        primary=pressure[pressure.pressure_primary]
        check("pressure_rows_have_valid_pre_state",bool((primary.state_valid_primary & primary.primary_match_eligible & primary.innings.eq(2) & primary.pressure_margin.gt(0)).all()),f"pressure rows={len(primary):,}")
        check("primary_excludes_revised_and_superovers",bool((~primary.match_has_revised_state & ~primary.match_has_super_over & primary.innings.eq(2)).all()),"No DLS/revised match or Super Over in primary pressure rows")
        check("pressure_only_ipl",bool(pressure.loc[pressure.pressure_primary,"is_ipl"].all()),"Primary pressure events are IPL-only")
    else:
        check("manifest_exists",False,"input manifest missing")
    for role,filename,balls_col,innings_col,minball,mininn in [
        ("batter","top_10_pressure_batters.csv","pressure_balls","pressure_innings",30,5),
        ("bowler","top_10_pressure_bowlers.csv","pressure_legal_balls","pressure_innings",60,5),
    ]:
        path=OUT/"rankings"/filename
        if path.exists():
            df=pd.read_csv(path)
            valid=(df[balls_col].ge(minball)&df[innings_col].ge(mininn)).all() if len(df) else True
            check(f"{role}_ranking_sample_gates",valid,f"rows={len(df)}; minimum={minball} pressure balls and {mininn} innings")
            check(f"{role}_ranking_max_ten",len(df)<=10,f"rows={len(df)}")
        else:check(f"{role}_ranking_exists",False,"missing")
    # Independent outcome-margin check on source deliveries, excluding DLS.
    bb=pd.read_csv(ROOT/"data"/"ball_by_ball_updated.csv",low_memory=False)
    mm=pd.read_csv(ROOT/"data"/"matches.csv",low_memory=False)
    totals=bb.assign(_total=bb.runs+bb.extras1_runs+bb.extras_2_runs).groupby(["match_id","innings"])._total.sum().unstack()
    margins=mm.merge(totals,left_on="match_id",right_index=True,how="inner")
    runwin=margins[margins.result.str.contains(r"Won by\s+\d+\s+Runs?",case=False,na=False)&~margins.result.str.contains(r"D/L|DLS",case=False,na=False)].copy()
    declared=runwin.result.str.extract(r"Won by\s+(\d+)\s+Runs?",flags=re.I)[0].astype(int)
    reconciled=declared.eq(runwin[1]-runwin[2])
    ok=bool(reconciled.all())
    check("non_dls_run_margin_reconciliation",ok,f"{int(reconciled.sum())}/{len(runwin)} run wins exactly reconcile")
    deckpath=OUT/"presentation"/"cricket_pressure_analytics_presentation.pptx"
    if deckpath.exists():
        prs=Presentation(deckpath)
        check("powerpoint_opens_and_slide_count",len(prs.slides)==26,f"slides={len(prs.slides)}")
        images=sum(1 for slide in prs.slides for sh in slide.shapes if sh.shape_type==13)
        check("powerpoint_contains_chart_images",images>=8,f"embedded images={images}")
    else:check("powerpoint_exists",False,"missing")
    charts=list((OUT/"charts").glob("*.png"))
    check("chart_assets_exist",len(charts)>=8,f"count={len(charts)}")
    check("notebook_execution",notebook_execution.lower().startswith("passed"),notebook_execution)
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"status":"passed" if not errors else "failed","checks":checks,"failed_checks":errors}
    report=["# Final Validation Report","",f"**Status:** {summary['status'].upper()}  ",f"**Executed:** {summary['created_utc']}  ",f"**Notebook:** {notebook_execution}","","## Checks","","| Check | Status | Detail |","|---|---|---|"]
    report += [f"| {c['check']} | {'PASS' if c['passed'] else 'FAIL'} | {c['detail']} |" for c in checks]
    report += ["","## Final interpretation","","All checks are executable validations of source preservation, join cardinality, state eligibility, ranking gates, result-margin reconciliation, notebook execution and presentation integrity. Passing these checks does not resolve provider-specific `other` / `extras_2_runs` definitions or missing 2027 auction inputs."]
    (OUT/"reports"/"final_validation_report.md").write_text("\n".join(report),encoding="utf-8")
    return summary

