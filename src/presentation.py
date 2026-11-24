"""Build the final 26-slide academic/recruitment PowerPoint."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


NAVY=RGBColor(18,18,42)
PURPLE=RGBColor(92,42,130)
PINK=RGBColor(229,0,125)
GOLD=RGBColor(232,183,61)
WHITE=RGBColor(250,248,255)
MUTED=RGBColor(197,194,213)
PALE=RGBColor(239,231,248)


def _text(slide, x, y, w, h, text, size=18, color=WHITE, bold=False, font="Aptos", align=None):
    box=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=box.text_frame; tf.clear(); tf.word_wrap=True
    p=tf.paragraphs[0]; p.text=str(text); p.font.name=font; p.font.size=Pt(size); p.font.bold=bold; p.font.color.rgb=color
    if align is not None: p.alignment=align
    return box


def _base(prs: Presentation, title: str, section: str="SupeRR Selector Season 2"):
    slide=prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid(); slide.background.fill.fore_color.rgb=NAVY
    band=slide.shapes.add_shape(1,0,0,prs.slide_width,Inches(.13)); band.fill.solid(); band.fill.fore_color.rgb=PINK; band.line.fill.background()
    _text(slide,.55,.28,12.2,.25,section.upper(),9,GOLD,True)
    _text(slide,.55,.62,12.1,.65,title,27,WHITE,True)
    line=slide.shapes.add_shape(1,Inches(.55),Inches(1.33),Inches(1.15),Inches(.045)); line.fill.solid(); line.fill.fore_color.rgb=GOLD; line.line.fill.background()
    _text(slide,.55,7.13,12.2,.18,"Historical IPL 2022-2026 | Availability and 2027 auction eligibility not verified",8,MUTED)
    return slide


def _bullets(slide, items, x=.8, y=1.65, w=11.8, h=4.9, size=19):
    box=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=box.text_frame; tf.clear(); tf.word_wrap=True
    for i,item in enumerate(items):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text=str(item); p.level=0; p.font.name="Aptos"; p.font.size=Pt(size); p.font.color.rgb=WHITE
        p.space_after=Pt(14); p.bullet=True
    return box


def _metric_card(slide,x,y,w,h,label,value,sub=""):
    shape=slide.shapes.add_shape(1,Inches(x),Inches(y),Inches(w),Inches(h)); shape.fill.solid(); shape.fill.fore_color.rgb=PURPLE; shape.line.color.rgb=GOLD
    _text(slide,x+.18,y+.18,w-.36,.28,label.upper(),10,GOLD,True)
    _text(slide,x+.18,y+.56,w-.36,.55,value,26,WHITE,True)
    if sub:_text(slide,x+.18,y+1.13,w-.36,.42,sub,10,PALE)


def _chart_slide(prs,title,image: Path|None,caption: str):
    slide=_base(prs,title)
    if image and image.exists():
        slide.shapes.add_picture(str(image),Inches(.65),Inches(1.55),width=Inches(8.4),height=Inches(5.15))
        _text(slide,9.35,1.78,3.35,4.7,caption,15,PALE)
    else:
        _bullets(slide,[caption],x=.85,y=1.8,w=11.5,h=4.4)
    return slide


def _ranking_slide(prs,title,frame,role:str,columns:list[str],note:str):
    slide=_base(prs,title)
    if frame.empty:
        _bullets(slide,["No player met the pre-registered sample requirements.",note]); return slide
    top=frame.head(10).reset_index(drop=True)
    headers=columns
    table=slide.shapes.add_table(min(11,len(top)+1),len(headers),Inches(.58),Inches(1.65),Inches(12.2),Inches(4.95)).table
    widths=[1.3,3.5]+[7.4/max(1,len(headers)-2)]*(len(headers)-2)
    for c,w in enumerate(widths): table.columns[c].width=Inches(w)
    for j,h in enumerate(headers):
        cell=table.cell(0,j); cell.text=h.replace("_"," ").title(); cell.fill.solid(); cell.fill.fore_color.rgb=PURPLE
        cell.text_frame.vertical_anchor=MSO_ANCHOR.MIDDLE
        for p in cell.text_frame.paragraphs:p.font.name="Aptos";p.font.size=Pt(11);p.font.bold=True;p.font.color.rgb=GOLD
    for i,(_,row) in enumerate(top.iterrows(),start=1):
        for j,c in enumerate(headers):
            value=row.get(c,"")
            if isinstance(value,float): value=f"{value:.2f}"
            cell=table.cell(i,j);cell.text=str(value);cell.fill.solid();cell.fill.fore_color.rgb=RGBColor(33,31,61) if i%2 else RGBColor(43,39,73)
            cell.text_frame.vertical_anchor=MSO_ANCHOR.MIDDLE
            for p in cell.text_frame.paragraphs:p.font.name="Aptos";p.font.size=Pt(11);p.font.color.rgb=WHITE
    _text(slide,.72,6.7,11.7,.27,note,9,MUTED)
    return slide


def create_deck(path: Path, chart_paths: list[Path], prep: dict, top_bat: pd.DataFrame,
                top_bowl: pd.DataFrame, sensitivity: pd.DataFrame, ml_report: dict,
                season: pd.DataFrame, rr_summary: pd.DataFrame, death_bat: pd.DataFrame,
                death_bowl: pd.DataFrame, pressure_death_bat: pd.DataFrame,
                pressure_death_bowl: pd.DataFrame, batter_consistency: pd.DataFrame,
                bowler_consistency: pd.DataFrame, auction_text: str) -> None:
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    charts={p.stem:p for p in chart_paths}
    # 1 Title
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=NAVY
    rect=s.shapes.add_shape(1,0,0,Inches(.25),prs.slide_height);rect.fill.solid();rect.fill.fore_color.rgb=PINK;rect.line.fill.background()
    _text(s,.85,1.0,11.5,.4,"RAJASTHAN ROYALS | IPL 2027 AUCTION ANALYSIS",13,GOLD,True)
    _text(s,.85,1.75,11.8,1.55,"Cricket Pressure\nPerformance Analytics",34,WHITE,True)
    _text(s,.9,4.05,10.9,.65,"SupeRR Selector · Season 2",22,PALE)
    _text(s,.9,5.25,11.4,.8,"A transparent historical screen of regulation-chase performance, death overs and player consistency.",16,MUTED)
    _text(s,.9,6.8,11,.25,"IPL 2022-2026 | Auction availability not verified",10,GOLD,True)
    # 2 executive snapshot
    s=_base(prs,"Executive snapshot")
    _metric_card(s,.75,1.75,2.7,1.65,"IPL matches",str(prep["ipl_matches"]),"2022-2026")
    _metric_card(s,3.75,1.75,2.7,1.65,"With deliveries",str(prep["ipl_matches_with_deliveries"]),"4 abandoned without ball records")
    _metric_card(s,6.75,1.75,2.7,1.65,"Primary cohort",str(prep["eligible_primary_matches"]),"Regulation chases")
    _metric_card(s,9.75,1.75,2.7,1.65,"Pressure states",f"{prep['primary_pressure_deliveries']:,}","RRR above opening RRR")
    _bullets(s,["Pressure means a chase has fallen behind its opening required pace.","The rankings are historical, sample-gated and sensitive to the chosen pressure threshold.","No 2027 player pool, RR purse or availability list was supplied."],y=4.0,size=16)
    # 3 problem
    s=_base(prs,"Problem and project questions");_bullets(s,["Find repeatable batting and bowling evidence in difficult chase states; keep pressure distinct from death overs.","Identify eligible pressure performers and compare pressure rates with overall and death-over rates.","Describe consistency and historical team/player profiles.","Develop RR role-fit research leads without inferring 2027 availability or price."],size=18)
    # 5 dataset inventory
    s=_base(prs,"Data inventory: six related tables");_bullets(s,["200,999 ball-by-ball deliveries; 883 matches; 141 competitions.","28,381 playing-eleven rows; 6,413 competition-player mappings; 353 competition-team rows.","IPL seasons 2022-2026: 371 scheduled matches, 367 with delivery records.","Data includes match state, delivery runs/extras, wickets, players, teams, stages and results."],size=18)
    # 6 relations
    s=_base(prs,"Integration and grain");_bullets(s,["Competition → match → delivery; team labels join on competition and team ID.","Delivery-to-match and match-to-competition joins were validated many-to-one.","Playing-eleven rows were not joined to delivery rows, preventing row multiplication.","Player IDs and names remain anchored to the delivery records; unmatched roster membership remains flagged."],size=17)
    # 7 data quality
    s=_base(prs,"Data-quality decisions");_bullets(s,["35 repeated player-match roster groups contain 40 excess rows; striker-level batting order corroborates one candidate order per group.","All source roster rows remain in the exception table with selection flags; groups occur only in three T20Is.","Five missing player-map rows are Bashir Ahmad listed as unplayed Afghanistan A squad entries.","All 16 matches without deliveries are marked abandoned; retained for schedule coverage only."],size=16)
    # 8 cleaning integration
    s=_base(prs,"Cleaning without losing provenance");_bullets(s,["No original CSV was changed; analytical copies add parsed dates and derived fields.","No exact duplicate records or invalid match/team foreign references were removed.","Unclear extras, revised-overs units, and dismissal-ID inconsistencies are explicitly flagged.","The integrated delivery export preserves 200,999 rows after cardinality-checked joins."],size=17)
    # 9 scoring accounting
    s=_base(prs,"Cricket scoring: validation checks");_bullets(s,["Candidate team runs = batter runs + extras1 + extras_2.","Reconstructed totals match the stated run margin in 399 of 399 non-DLS run victories.","Wides and likely no-balls are excluded from legal balls; batter balls faced exclude wides.","Bowler runs exclude byes/leg-byes; unknown `other` and extras_2 treatment is exposed as a sensitivity.","Rule reference: ICC T20I Playing Conditions, Clauses 17-22 and 38; feed-specific encoding still requires confirmation."],size=14)
    # 10 state
    s=_base(prs,"Pre-delivery match state");_bullets(s,["Only prior deliveries contribute to the current state: score, wickets lost and legal balls used.","Target = validated first-innings total + 1 in a standard chase.","Required runs = target - score; required rate = required runs × 6 / balls remaining.","Wickets remaining = 10 - wickets lost. DLS/revised state and Super Overs are outside the primary cohort."],size=17)
    # 11 pressure definition
    s=_base(prs,"Pressure definition: pace deficit");_bullets(s,["Pressure margin = current required run rate − opening required run rate.","Primary pressure label: margin > 0, meaning the chase is behind its required pace.","This is an observable match-state proxy, not a psychological label or win-probability model.","Alternative thresholds (≥2 runs/over and top quartile) are tested; rank stability is limited."],size=17)
    # 12 cohort chart
    _chart_slide(prs,"IPL scoring environment",charts.get("season_scoring_environment"),"Season totals and run rates describe the five-year environment. The display includes regulation innings with recorded deliveries; schedules and no-result exclusions are listed in the data-quality report.")
    # 13 team chart
    _chart_slide(prs,"Team-level scoring context",charts.get("ipl_team_batting_productivity"),"Team run-per-wicket summaries provide context only. Workload, opposition, season and incomplete source coverage differ by team.")
    # 14 batter metrics
    s=_base(prs,"Batter metrics and safeguards");_bullets(s,["Runs use the `runs` field; balls faced exclude wides and include likely no-balls.","Pressure strike rate, batting average, boundary share and dot-ball rate are shown beside sample size.","Batting roles use striker-only batting_order observations; the field is not read from non-striker rows.","Ranking gate: at least 30 pressure balls across five pressure innings; rates shrink toward the cohort mean."],size=16)
    # 15 batter top ten
    _ranking_slide(prs,"Top pressure-performing batters",top_bat,"batter",["rank","player_name","batting_role","pressure_runs","pressure_balls","pressure_innings","pressure_strike_rate","pressure_average"],"Equal-weight composite of adjusted strike rate, boundary-run share and dot avoidance. Read the rates with opportunities and dismissals.")
    # 16 overall vs pressure chart
    _chart_slide(prs,"Overall vs pressure batting",charts.get("overall_vs_pressure_strike_rate"),"Players above the diagonal have a higher observed strike rate in the pressure cohort. Bubble size represents pressure-ball opportunity; low-sample players are excluded from the chart.")
    # 17 bowler metrics
    s=_base(prs,"Bowler metrics and caveats");_bullets(s,["Legal balls exclude wides and likely no-balls; one-based overs 16-20 define death overs.","Credited wickets are Caught, Bowled, LBW, Stump and Hit Wicket; run-outs are not credited.","Byes and leg-byes are excluded from conceded runs. Unknown `other` rows are omitted from pressure bowling rates.","Ranking gate: at least 60 classified pressure legal balls across five pressure innings."],size=16)
    # 18 bowler top ten
    _ranking_slide(prs,"Top pressure-performing bowlers",top_bowl,"bowler",["rank","player_name","pace_or_spin","pressure_legal_balls","pressure_innings","pressure_economy","pressure_wickets","pressure_wickets_per_100_balls"],"Equal-weight composite of lower adjusted economy, higher wicket rate and higher legal dot rate. Economy remains provisional for unclear extras.")
    # 19 economy comparison
    _chart_slide(prs,"Overall vs pressure bowling economy",charts.get("overall_vs_pressure_economy"),"Lower values indicate fewer classified bowler runs per six legal balls. Unknown extra labels remain a limitation and are tested with alternate accounting.")
    # 20 death batting
    _chart_slide(prs,"Death-over batting leaders",charts.get("death_over_batter_leaders"),"Death overs are one-based scheduled overs 16-20. This chart is separate from pressure and uses a minimum 30-ball sample.")
    # 21 death bowling
    _chart_slide(prs,"Death-over bowling leaders",charts.get("death_over_bowler_leaders"),"Death-over bowling is a scheduled phase, not a pressure label. Economy uses classified bowler runs and legal balls.")
    _chart_slide(prs,"Death-over performance under pressure",charts.get("death_over_pressure_comparison"),"Only deliveries already labelled pressure by pre-delivery chase state are included. Death over alone is not the pressure criterion.")
    # Consistency
    _chart_slide(prs,"Consistency across IPL innings",charts.get("player_consistency_profiles"),"Lower variation in innings strike rate or economy indicates steadier observed rates. The chart requires ten innings and should be interpreted with each player's mean and workload.")
    # Sensitivity
    _chart_slide(prs,"Sensitivity: pressure threshold matters",charts.get("ranking_sensitivity_top10_overlap"),"Overlap compares each alternative top ten with the primary margin>0 screen. Low overlap is a warning against over-reading ranks; full rank correlations are in the report.")
    # 24 ML
    s=_base(prs,"Machine learning: exploratory profiles only")
    b=ml_report.get("batters",{});w=ml_report.get("bowlers",{})
    _bullets(s,[f"Batters: {b.get('status','not run')} — {b.get('reason','silhouette-selected exploratory profiles')}; eligible players {b.get('n_players','—')}.",f"Bowlers: {w.get('status','not run')} — {w.get('reason','silhouette-selected exploratory profiles')}; eligible players {w.get('n_players','—')}.","K-Means was evaluated on scaled performance rates with silhouette checks.","No supervised prediction: no auction-success target is present; predicting auction success would be unsupported."],size=15)
    # 25 RR history & conditional recs
    s=_base(prs,"Rajasthan Royals: conditional evidence screen")
    _bullets(s,["Historical pressure leaders are research leads only; verify each name against the official 2027 auction pool and availability.","Historical RR pressure exposure is summarized in processed outputs; it is not a current squad assessment.","Verify retained/released players, purse, overseas/roster slots and role needs before a target list or price recommendation."],size=15)
    # 26 limits & conclusion
    s=_base(prs,"Conclusion, limitations and next evidence")
    _bullets(s,["The dataset supports retrospective IPL chase-state analysis after transparent exclusions.","Pressure rankings are cohort-relative and sensitive to threshold, sample and extra treatment.","No auction availability, prices, 2027 squad constraints or future success can be inferred from these six files.","Use the leaderboards as historical research leads; validate role fit and availability against official 2027 information."],size=16)
    path.parent.mkdir(parents=True,exist_ok=True);prs.save(path)

