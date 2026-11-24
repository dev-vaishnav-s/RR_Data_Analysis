"""Create a layout-only HTML source for the final competition audit PDF.

This formatter reads the already-published audit tables. It does not load raw
data, rerun analysis, or write rankings. Chrome's print engine creates the PDF.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
import pandas as pd

from .data_pipeline import ROOT, OUT


FINAL_PDF = OUT / "reports" / "superrr_selector_round1_competition_readiness_audit_FINAL_v2.pdf"
HTML_PATH = OUT / "reports" / ".superrr_selector_round1_competition_readiness_audit_FINAL_v2.html"


def esc(value) -> str:
    if pd.isna(value):
        return ""
    return escape(str(value), quote=True)


def table(headers, rows, classes=""):
    head = "".join(f'<th>{esc(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell if isinstance(cell, SafeHtml) else esc(cell)}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<table class="{classes}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


class SafeHtml(str):
    pass


def page(number, title, subtitle, body, cover=False):
    return f'''<section class="sheet {'cover' if cover else ''}" id="page-{number}">
      <header class="running-head"><span>SUPERR SELECTOR · SEASON 2</span><span>ROUND 1 · READINESS AUDIT</span></header>
      <div class="rule"></div>
      <h1>{title}</h1><p class="subtitle">{subtitle}</p>
      <main>{body}</main>
      <footer><span>Cricket Pressure Performance Analytics · Rajasthan Royals</span><span>PAGE {number} OF 11</span></footer>
    </section>'''


def make_html() -> Path:
    reports, ranks, proc = OUT / "reports", OUT / "rankings", OUT / "processed"
    bat = pd.read_csv(ranks / "top_10_pressure_batters.csv")
    bowl = pd.read_csv(ranks / "top_10_pressure_bowlers.csv")
    t20b = pd.read_csv(ranks / "supplementary_t20i_pressure_batters.csv")
    t20w = pd.read_csv(ranks / "supplementary_t20i_pressure_bowlers.csv")
    sens = pd.read_csv(ranks / "pressure_ranking_sensitivity_checks.csv")
    # Display the exact eight alternate-scenario records already included in the original report.
    wanted = {"margin_at_least_2", "valid_state_top_quartile_margin_3.100", "other_extras_treated_illegal", "scoring_first_weights", "wicket_first_weights"}
    sens = sens[sens.scenario.isin(wanted)].copy()
    roster_exc = pd.read_csv(proc / "playing_eleven_duplicate_exceptions.csv")

    # Existing text and values from the original PDF, with the same table contents and order.
    cover_rows = [
        ["Coverage", "IPL: 371 scheduled; 367 with deliveries; 354 primary eligible", "T20I: 482 scheduled; 470 with deliveries; 427 eligible"],
        ["Pressure sample", "24,844 IPL pressure deliveries", "30,104 T20I pressure deliveries"],
        ["Rankings", "Existing IPL top tens: recomputed order matches CSV", "Supplementary independent screen generated; not pooled"],
        ["Integrity", "Source SHA-256 unchanged; 35/35 duplicate groups corroborated", "16 delivery-missing matches are abandoned/no-result"],
    ]
    cover = table(["Audit area", "Primary IPL", "Separate T20I"], cover_rows)
    cover += '''<h2>Audit conclusion</h2><p>The project has a reproducible IPL-only primary pressure leaderboard and valid sample-gated top tens. IPL-only is defensible for auction-role transfer, but the supplied T20I sample should also be used as a separate, explicitly labelled supplementary comparison. This audit now calculates that T20I screen without pooling it into or reordering the IPL top tens. The lists remain descriptive/exploratory, not validated predictors of future IPL auction success.</p><p class="note">Audit run does not modify raw CSVs, current IPL rankings, charts, or presentation.</p>'''

    coverage = '''<div class="coverage-key"><span><i class="key scheduled"></i>Scheduled matches</span><span><i class="key delivered"></i>Matches with delivery rows</span></div><div class="coverage-grid"><b>IPL</b><div><span class="coverage-count">371 scheduled</span><span class="coverage-count">367 with deliveries</span><div class="coverage-track"><i class="scheduled" style="width:77%"></i><i class="delivered" style="width:76%"></i></div></div><b>T20I</b><div><span class="coverage-count">482 scheduled</span><span class="coverage-count">470 with deliveries</span><div class="coverage-track"><i class="scheduled" style="width:100%"></i><i class="delivered" style="width:98%"></i></div></div></div>'''
    coverage += '<p>IPL: 87,687 deliveries · 2022–2026 · primary cohort 354 matches<br>T20I: 106,327 deliveries · 131 named competitions · supplementary eligible cohort 427 matches</p>'

    methods = [
        ("COHORT", "Regulation 2nd innings; match has innings 1 and 2; full 20-over allocation; exclude abandoned/no-result, DLS/revised target/overs, and any match with Super Over."),
        ("PRE-DELIVERY SCORE", "score_before = cumulative sum of (batter runs + extras1 + extras2) before this delivery."),
        ("STATE", "R = target − score_before; B = 120 − legal balls used; W = 10 − wickets lost. Target = reconstructed 1st-innings team total + 1."),
        ("RATES", "RRR = 6 × R / B (when R>0 and B>0); opening RRR = 6 × target / 120."),
        ("PRESSURE FLAG", "Primary: RRR − opening RRR > 0. Positive means the chase has fallen behind its initial required pace. It is a transparent state marker, not psychological pressure, win probability, or proof of clutch ability."),
        ("BOUNDARY CONDITIONS", "Exclude states after the target, after 120 legal balls, and after an unresolved 'other' extra has already appeared. An 'other' event is retained only at its pre-delivery state; bowling outcome rows tagged 'other' are omitted from the primary bowling composite."),
    ]
    method_html = "".join(f'<div class="method"><b>{escape(h)}</b><p>{escape(b)}</p></div>' for h,b in methods)
    method_html += '<p class="note">Both competitions use the same arithmetic, but states and player rates are reconstructed in separate cohorts.</p>'

    score_bullets = [
        ("BATTERS | Composite = ( z(shrunk pressure strike rate) + z(shrunk pressure boundary-run share) + z(" + chr(8722) + "shrunk pressure dot rate) ) " + chr(247) + " 3", "strong"),
        ("Pressure batter runs use the delivery batter-runs field; batter balls exclude wides and include no-balls. Boundary-run share uses batter boundary runs / batter runs; dot rate uses pressure balls with zero team runs / balls.", ""),
        ("Batter shrinkage: SR and dot rate use 30 prior pressure balls at the pressure-cohort mean; boundary-run share uses 300 prior batter runs. Eligibility: at least 30 pressure balls across at least 5 pressure innings.", ""),
        ("BOWLERS | Composite = ( z(" + chr(8722) + "shrunk pressure economy) + z(shrunk bowler wickets per 100 legal balls) + z(shrunk legal-dot rate) ) " + chr(247) + " 3", "strong"),
        ("Bowler runs include batter runs plus recorded wide/no-ball penalty extras; exclude byes/leg-byes and omit 'other'-tagged delivery outcomes. Legal balls exclude wides and Overstep. Bowler-credit wickets: Caught, Bowled, LBW, Stump, Hit Wicket; run-outs and other non-credit dismissals are not credited.", ""),
        ("Bowler shrinkage uses 60 prior legal balls at cohort means; eligibility: at least 60 classified pressure legal balls across at least 5 pressure innings.", ""),
        ("Opportunity fairness: gates, shrinkage and displayed raw workload reduce small-sample dominance; z-scores standardize eligible players within their own competition cohort. Equal weights are transparent but normative and do not make the composite an objective talent estimate.", ""),
        ("Rank order is descending composite; ties break on more pressure balls, then more pressure runs (batters) or wickets (bowlers). Sensitivity is reported on page 7.", ""),
    ]
    scores = "".join("<li class=\"" + cls + "\"><div class=\"math\">" + escape(text) + "</div></li>" if cls == "strong" else "<li>" + escape(text) + "</li>" for text,cls in score_bullets)

    bat_rows=[]
    for r in bat.itertuples(index=False):
        bat_rows.append([int(r.rank), r.player_name, f"{r.pressure_score:.1f}", int(r.pressure_balls), int(r.pressure_innings), f"{r.pressure_strike_rate:.1f}", f"{r.strike_rate:.1f}"])
    bat_table=table(["Rank","Player","Score","P balls","P inns","P SR","Overall SR"],bat_rows,"compact player-table")
    bat_table += '<p class="note">Pressure SR / overall SR is a descriptive contrast; the leaderboard score is calculated from pressure metrics only. No outcome guarantee.</p>'

    bowl_rows=[]
    for r in bowl.itertuples(index=False):
        bowl_rows.append([int(r.rank),r.player_name,f"{r.pressure_score:.2f}",int(r.pressure_legal_balls),int(r.pressure_innings),f"{r.pressure_economy:.2f}",f"{r.economy:.2f}",int(r.pressure_wickets)])
    bowl_table=table(["Rank","Player","Score","P legal balls","P inns","P econ","Overall econ","P wkts"],bowl_rows,"compact player-table")
    bowl_table += '<p class="note">Economy is runs conceded per six legal balls; higher pressure wicket counts are credited dismissals only.</p>'

    t20b_rows=[]
    for r in t20b.head(8).itertuples(index=False):
        t20b_rows.append([int(r.rank),r.player_name,f"{r.pressure_score:.1f}",int(r.pressure_balls),int(r.pressure_innings),f"{r.overall_strike_rate:.1f}",f"{r.pressure_strike_rate:.1f}"])
    t20w_rows=[]
    for r in t20w.head(8).itertuples(index=False):
        t20w_rows.append([int(r.rank),r.player_name,f"{r.pressure_score:.2f}",int(r.pressure_legal_balls),int(r.pressure_innings),f"{r.overall_economy:.2f}",f"{r.pressure_economy:.2f}"])
    t20_html="<p class=\"note\">427 regulation T20I matches; 45,833 valid pre-delivery chase states; 30,104 pressure deliveries; 181 qualified batters; 126 qualified bowlers. The same gates apply as in IPL: batters require at least 30 pressure balls across 5 pressure innings; bowlers require at least 60 classified pressure legal balls across 5 pressure innings.</p>"
    t20_html+=table(["#","T20I batter","Score","P balls","P inns","Overall SR","P SR"],t20b_rows,"compact player-table")
    t20_html+=table(["#","T20I bowler","Score","P legal","P inns","Overall econ","P econ"],t20w_rows,"compact player-table")
    t20_html+='<p class="note">Independent T20I screen is supplementary evidence only. International roles/opposition and event context differ from franchise IPL; it cannot silently increase IPL sample sizes.</p>'

    sv=[]
    for r in sens.itertuples(index=False):
        sv.append([r.scenario,r.role,int(r.top10_overlap),f"{r.spearman_rank_correlation:.2f}",int(r.eligible_primary),int(r.eligible_scenario)])
    sensitivity=table(["Scenario","Role","Top-10 overlap","Spearman rho (Greek letter " + chr(961) + ")","Eligible base","Eligible alt."],sv,"compact sensitivity-table")
    sensitivity += '<p>Pressure-threshold sensitivity is material: margin ≥2 retains 2/10 batters and 4/10 bowlers; upper-quartile margin retains 2/10 and 3/10.</p><p>Reliability checks: six source hashes unchanged; IPL primary pressure rows are IPL-only, valid chase states, second innings, pre-outcome, and exclude revised/DLS and Super Over matches; direct top-10 recomputation matches both saved rank orders; non-DLS run-win score margins reconcile 399/399.</p><p class="note">This is a sensitivity audit, not out-of-time validation or proof that pressure skill persists. No confidence intervals or predictive reliability gate were part of the original score implementation.</p>'

    spot_rows=[
        ["Pressure legal",14094,2,2,0,"0/0",0,"yes","yes",0,"no"],
        ["Wide",14094,1,3,0,"1/0",1,"no","no",1,"no"],
        ["No-ball (Overstep)",14094,1,1,0,"1/0",1,"yes","no",1,"no"],
        ["Bye",14094,2,47,0,"4/0",4,"yes","yes",0,"no"],
        ["Leg-bye",14095,1,105,0,"1/0",1,"yes","yes",0,"no"],
        ["Unknown other",14094,1,119,6,"1/0",7,"yes","yes","not scored","no"],
        ["Bowler-credit wicket",14094,1,5,0,"0/0",0,"yes","yes",0,"yes"],
        ["Run-out (not bowler credit)",14094,1,56,0,"0/0",0,"yes","yes",0,"no"],
    ]
    spot=table(["Event","Match","Inn","Ball seq.","Runs","Ex1/Ex2","Team","BF","Legal","Bowler runs","Bowler wicket"],spot_rows,"compact spot-table")
    spot += '<p><b>State example (immediately before the listed delivery):</b><br>Match 14094, innings 2, sequence 2 · score 0 · target 132 · runs required 132 · legal balls left 119 · wickets left 10 · RRR 6.655, opening RRR 6.600 · pressure=True.</p><p class="note">Spot checks validate recorded totals and flags; they do not resolve the provider\'s undefined \'other\' or extras_2 semantics. State uses preceding deliveries only.</p>'

    # Retain the original seven displayed group examples exactly; the analytical exception CSV retains all 35 groups.
    group_rows=[]
    for match,team,player,orders,observed in [
        (13613,20,223,"5.0, 6.0","5"),(13613,20,250,"2.0, 4.0","2"),(13613,20,838,"1.0, 4.0","4"),
        (13613,20,2639,"2.0, 6.0","6"),(13613,20,3539,"1.0, 3.0","1"),(13613,20,4736,"3.0, 5.0","3"),(13613,27,1100,"2.0, 5.0","5")]:
        group_rows.append([match,team,player,orders,observed,1])
    roster=table(["Match","Team","Player","Roster orders","Striker order","Selected"],group_rows,"compact exception-table")
    roster += '<h2>PLAYING XI</h2><p>35 repeated (match, team, player) groups contain 75 source rows / 40 excess rows. In all 35, exactly one unique striker-observed batting order matches exactly one conflicting roster candidate. All groups therefore have one corroborated analytical row, while every raw/analytical exception row and source row number remains preserved. These groups occur in three non-IPL T20Is (match IDs 13613, 21176, 28962); corroboration is not a provider correction.</p>'
    roster += '<p><b>PLAYER MAPPING ·</b> Five rows are Bashir Ahmad (ID 29833), team ID 4444, competition ID 2670 (Men\'s T20 Emerging Teams Asia Cup 2024); they are flagged not-played with no batting-order/role fields. Preserve as roster-to-mapping exceptions; do not infer five appearances.</p>'
    roster += '<p><b>SCORING / WICKETS ·</b> Team runs = runs + extras1 + extras2; batter runs use runs only; wides are not batter balls; no-balls count as batter balls but not legal balls; byes/leg-byes are team runs but not bowler runs. Recognized bowler wickets match observed credited labels Caught/Bowled/LBW/Stump/Hit Wicket; run-outs, retire-out and obstruction do not count.</p>'
    roster += '<p class="small">Observed extras labels/counts: {nan: 189167, \'wide\': 7714, \'legbyes\': 2748, \'Overstep\': 576, \'byes\': 529, \'other\': 264, \'Penalty\': 1}. Observed dismissal labels: {\'Caught\': 7557, \'Bowled\': 1775, \'LBW\': 709, \'RunOut\': 600, \'Stump\': 214, \'Hit Wicket\': 17, \'Retire Out\': 6, \'Obstracting the field\': 2, \'Obstructing the field\': 1}. A single Penalty extras row and undefined \'other\' / extras_2 semantics remain provider-definition limitations. `Overstep` is treated as a no-ball based on the data dictionary/context, but the provider should confirm.</p>'

    final = [
        ("IPL and T20I?", "Both are now analysed; IPL remains the primary transfer cohort and T20I is separate supplementary evidence. IPL-only leaderboards remain unchanged."),
        ("Overall comparison?", "Each IPL top-10 batter has overall and pressure strike rate; each bowler has overall and pressure economy, plus pressure workload. The audit table puts those side by side."),
        ("Reliable under pressure?", "This pipeline ranks pressure output, not demonstrated reliability/persistence. A same-player pressure-vs-overall contrast and sensitivity are supplied; no temporal/repeated-split reliability validation exists."),
        ("Auction actions?", "The six files lack official 2027 auction eligibility/availability, current RR retained roster, purse, prices, roster slots and role needs. Therefore player names remain evidence screens, not verified auction targets."),
        ("Human review needed", "Confirm official problem-statement version and data-provider definitions for Overstep, other, extras_2 and revised-overs units; decide whether separate T20I supplementary screens meet scoring expectations; review high leaderboard sensitivity and lack of predictive reliability validation; acquire verified 2027 candidate/roster/purse inputs before actionable auction recommendations."),
    ]
    final_html="".join(f'<div class="answer"><b>{escape(h)}</b><p>{escape(b)}</p></div>' for h,b in final)
    final_html += '<p class="source">Competition source: Unstop event listing describes Round 1 as identifying the most reliable players under pressure for RR\'s IPL 2027 auction (<a href="https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758">https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758</a>). The exact organizer-issued PDF was not present in the project folder; request it for a final clause-by-clause compliance sign-off.</p>'

    sections = [
        page(1,"ROUND 1 | COMPETITION READINESS AUDIT","SupeRR Selector Season 2 · Rajasthan Royals · Evidence audit of the completed analytics project",cover,cover=True),
        page(2,"1 | DATASETS & COMPETITION SEPARATION","Actual coverage from supplied match and delivery tables",coverage),
        page(3,"2 | PRESSURE DEFINITION & MATCH-STATE RECONSTRUCTION","Pre-delivery chase state; outcome of the current delivery is never used to label its own state",method_html),
        page(4,"3 | SCORE, ELIGIBILITY & FAIR-COMPARISON AUDIT","The ranking is an opportunity-gated, cohort-relative descriptive screen",f"<ul class='score-list'>{scores}</ul>"),
        page(5,"4 | TOP 10 PRESSURE BATTERS — IPL PRIMARY","Values and order verified against the existing CSV and a direct recomputation",bat_table),
        page(6,"5 | TOP 10 PRESSURE BOWLERS — IPL PRIMARY","Values and order verified against the existing CSV and a direct recomputation",bowl_table),
        page(7,"6 | SEPARATE T20I SUPPLEMENTARY PRESSURE SCREEN","Same formula and gates, standardized within T20I-qualified players; these names are not added to IPL ranks",t20_html),
        page(8,"7 | SENSITIVITY, UNCERTAINTY & VALIDATION","A stable-looking score does not imply stable rank ordering",sensitivity),
        page(9,"8 | ACTUAL DELIVERY ARITHMETIC SPOT CHECKS","Examples are selected from supplied IPL rows; calculations below use the actual recorded fields",spot),
        page(10,"9 | PLAYING XI & CRICKET-DATA EXCEPTION AUDIT","Rechecked directly against all flagged source exception records",roster),
        page(11,"10 | DIRECT ANSWERS, LIMITATIONS & HUMAN REVIEW","Competition-readiness verdict against the Round 1 aim",final_html),
    ]
    css = '''
@page { size: A4 landscape; margin: 12mm 14mm 14mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin:0; color:#182538; background:#fff; font-family:Arial,Helvetica,sans-serif; font-size:9.3pt; line-height:1.28; }
.sheet { position:relative; page-break-after:always; break-after:page; min-height:180mm; padding-bottom:9mm; }
.sheet:last-child { page-break-after:auto; break-after:auto; }
.running-head { display:flex; justify-content:space-between; color:#52647a; font-size:8pt; font-weight:700; letter-spacing:.5pt; margin:0 0 3mm; }
.rule { border-top:2px solid #203c63; margin-bottom:5mm; }
h1 { color:#18365d; font-size:20pt; line-height:1.12; margin:0 0 1.5mm; font-weight:700; }
.subtitle { color:#53647a; font-size:9.2pt; margin:0 0 5mm; line-height:1.25; }
h2 { color:#244d78; font-size:11pt; margin:4mm 0 1.5mm; page-break-after:avoid; }
p { margin:0 0 2.5mm; widows:2; orphans:2; }
.note { color:#52647a; font-size:8.3pt; margin-top:2.5mm; }
.small { font-size:7.5pt; line-height:1.2; }
table { width:100%; border-collapse:collapse; table-layout:fixed; margin:2mm 0 3mm; font-size:8.1pt; }
th { color:white; background:#203c63; font-weight:700; text-align:left; padding:2.2mm 1.8mm; border:1px solid #d7e0e9; }
td { padding:1.65mm 1.8mm; border:1px solid #d7e0e9; overflow-wrap:anywhere; vertical-align:top; }
tbody tr:nth-child(even) { background:#f2f5f8; }
tr { break-inside:avoid; page-break-inside:avoid; }
td:nth-child(1):not(:last-child) { font-variant-numeric:tabular-nums; }
.player-table td:nth-child(1),.player-table td:nth-child(n+3),.player-table th:nth-child(1),.player-table th:nth-child(n+3),.sensitivity-table td:nth-child(n+3),.sensitivity-table th:nth-child(n+3),.spot-table td:nth-child(n+2),.spot-table th:nth-child(n+2) { text-align:right; font-variant-numeric:tabular-nums; }
.player-table td:nth-child(2) { text-align:left; font-weight:600; }
.player-table th:nth-child(1),.player-table td:nth-child(1) { width:7%; }
.player-table th:nth-child(2),.player-table td:nth-child(2) { width:25%; }
.sensitivity-table th:first-child,.sensitivity-table td:first-child { width:39%; }
.sensitivity-table th:nth-child(2),.sensitivity-table td:nth-child(2) { width:11%; }
.spot-table th:first-child,.spot-table td:first-child { width:22%; }
.compact { font-size:7.7pt; }
.compact th { padding:1.8mm 1.4mm; }
.compact td { padding:1.35mm 1.4mm; }
.sheet:nth-of-type(7) h2 { margin:1.5mm 0 1mm; }
.sheet:nth-of-type(7) table { margin:1mm 0 1.5mm; font-size:7.1pt; }
.sheet:nth-of-type(7) table th,.sheet:nth-of-type(7) table td { padding:.8mm 1mm; }
.sheet:nth-of-type(7) .note { font-size:7.8pt; margin-top:1.2mm; }
.method { display:grid; grid-template-columns:33mm 1fr; gap:4mm; padding:2.7mm 0; border-bottom:1px solid #dfe5ec; break-inside:avoid; }
.method b { color:#315c88; font-size:8.4pt; letter-spacing:.35pt; }
.method p { margin:0; }
.score-list { margin:0; padding:0 0 0 7mm; }
.score-list li { margin:0 0 2.5mm; padding-left:1mm; }
.score-list li::marker { color:#315c88; }
.score-list .strong { font-weight:700; color:#18365d; }
.coverage-key { display:flex; gap:12mm; color:#52647a; font-size:9pt; margin:8mm 0 3mm 18mm; }
.coverage-grid { display:grid; grid-template-columns:18mm 1fr; gap:5mm 4mm; align-items:center; width:94%; margin:0 0 7mm 18mm; }
.coverage-grid > b { color:#18365d; font-size:12pt; }
.coverage-count { display:inline-block; width:42%; color:#263e5c; font-size:9pt; font-weight:700; margin-bottom:2mm; }
.coverage-track { height:7mm; background:#e4eaf1; position:relative; }
.coverage-track i { position:absolute; left:0; height:2mm; display:block; }
.coverage-track .scheduled { top:1mm; background:#aebccd; }
.coverage-track .delivered { bottom:1mm; background:#315c88; }
.math { background:#f2f5f8; border-left:3px solid #315c88; padding:2.5mm 3mm; font-size:10pt; line-height:1.3; }
.sheet:nth-of-type(10) .small { font-size:8.2pt; line-height:1.3; }
.sheet:nth-of-type(10) p { margin-bottom:2mm; }
.bar-row { display:grid; grid-template-columns:15mm 1fr; gap:4mm; align-items:center; margin:5mm 0; }
.bar-track { height:10mm; background:#e4eaf1; display:flex; align-items:center; position:relative; }
.bar-track i { position:absolute; left:0; height:3.2mm; display:block; }
.bar-track .scheduled { top:1.5mm; background:#aebccd; }
.bar-track .delivered { bottom:1.5mm; background:#315c88; }
.legend { display:flex; gap:10mm; color:#52647a; font-size:8pt; margin:2mm 0 5mm 19mm; }
.legend span { white-space:nowrap; }
.key { display:inline-block; width:4mm; height:2mm; margin-right:1.5mm; vertical-align:middle; }
.key.scheduled { background:#aebccd; }.key.delivered { background:#315c88; }
.answer { display:grid; grid-template-columns:40mm 1fr; gap:5mm; padding:2.4mm 0; border-bottom:1px solid #dfe5ec; break-inside:avoid; }
.answer b { color:#315c88; }
.answer p { margin:0; }
.source { font-size:7.4pt; color:#52647a; margin-top:4mm; overflow-wrap:anywhere; }
a { color:#315c88; text-decoration:underline; }
footer { position:absolute; bottom:0; left:0; right:0; border-top:1px solid #cbd5e0; padding-top:2mm; display:flex; justify-content:space-between; font-size:7.2pt; color:#64748b; }
'''
    html = '<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body>'+"\n".join(sections)+'</body></html>'
    HTML_PATH.write_text(html,encoding="utf-8")
    return HTML_PATH


if __name__ == "__main__":
    print(make_html().relative_to(ROOT))
