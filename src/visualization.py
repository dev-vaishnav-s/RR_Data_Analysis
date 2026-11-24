"""Project charts based only on pipeline outputs."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


PURPLE = "#5A2A82"
PINK = "#E5007D"
BLUE = "#243B80"
GOLD = "#E7B43A"
PALETTE = [PURPLE, PINK, BLUE, GOLD, "#20A39E", "#6C757D"]
sns.set_theme(style="whitegrid", font_scale=0.95)


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def create_charts(outdir: Path, deliveries: pd.DataFrame, batter: pd.DataFrame, batter_pressure: pd.DataFrame,
                  bowler: pd.DataFrame, bowler_pressure: pd.DataFrame, top_bat: pd.DataFrame,
                  top_bowl: pd.DataFrame, death_bat: pd.DataFrame, death_bowl: pd.DataFrame,
                  innings_summary: pd.DataFrame, season_summary: pd.DataFrame, phase_summary: pd.DataFrame,
                  death_pressure_bat: pd.DataFrame, death_pressure_bowl: pd.DataFrame,
                  pressure_sensitivity: pd.DataFrame) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    if not season_summary.empty:
        fig, ax = plt.subplots(figsize=(10, 5.4))
        ax.plot(season_summary.season.astype(str), season_summary.mean_innings_runs, marker="o", lw=2.7, color=PURPLE, label="Mean innings total")
        ax.plot(season_summary.season.astype(str), season_summary.mean_runs_per_over, marker="o", lw=2.7, color=PINK, label="Mean runs per over")
        ax.set(title="IPL scoring environment by season", xlabel="Season", ylabel="Runs / runs per over")
        ax.legend(frameon=False); p=outdir/"season_scoring_environment.png"; _save(fig,p); paths.append(p)

    if not phase_summary.empty:
        fig,ax=plt.subplots(figsize=(10,5.5))
        view=phase_summary[phase_summary.scheduled_over_phase.isin(["Powerplay","Middle","Death"])]
        sns.lineplot(data=view,x="season",y="runs_per_over",hue="scheduled_over_phase",marker="o",linewidth=2.5,
                     palette={"Powerplay":GOLD,"Middle":BLUE,"Death":PINK},ax=ax)
        ax.set(title="IPL scoring by scheduled innings phase",xlabel="Season",ylabel="Runs per legal over")
        p=outdir/"phase_scoring_trends.png";_save(fig,p);paths.append(p)

    if not innings_summary.empty:
        fig, ax = plt.subplots(figsize=(10, 5.4))
        sns.histplot(innings_summary.team_runs, bins=25, kde=True, color=PURPLE, ax=ax)
        ax.axvline(innings_summary.team_runs.median(), color=PINK, ls="--", label=f"Median {innings_summary.team_runs.median():.0f}")
        ax.set(title="IPL innings totals (available delivery records)", xlabel="Reconstructed team runs", ylabel="Innings")
        ax.legend(frameon=False); p=outdir/"innings_total_distribution.png"; _save(fig,p); paths.append(p)

    for df, name, metric, title, color in [
        (top_bat,"top_pressure_batters","pressure_score","Top pressure batter composite (eligible sample)",PINK),
        (top_bowl,"top_pressure_bowlers","pressure_score","Top pressure bowler composite (eligible sample)",PURPLE),
    ]:
        if not df.empty:
            view=df.head(10).sort_values(metric)
            fig,ax=plt.subplots(figsize=(10,6))
            ax.barh(view.player_name,view[metric],color=color,alpha=.9)
            ax.set(title=title,xlabel="Opportunity-adjusted standardized composite",ylabel="")
            p=outdir/f"{name}.png"; _save(fig,p); paths.append(p)

    if not batter_pressure.empty and not batter.empty:
        z=batter.merge(batter_pressure,on=["player_id","player_name"],how="inner",validate="1:1",suffixes=("_overall","_pressure"))
        z=z[(z.balls_faced>=60)&(z.pressure_balls>=20)].dropna(subset=["strike_rate_overall","pressure_strike_rate"])
        if not z.empty:
            fig,ax=plt.subplots(figsize=(8,7))
            role_colors={r:PALETTE[i % len(PALETTE)] for i,r in enumerate(z.batting_role_overall.dropna().unique())}
            sns.scatterplot(data=z,x="strike_rate_overall",y="pressure_strike_rate",hue="batting_role_overall",size="pressure_balls",sizes=(25,240),alpha=.78,palette=role_colors,ax=ax)
            bounds=[min(z.strike_rate_overall.min(),z.pressure_strike_rate.min()),max(z.strike_rate_overall.max(),z.pressure_strike_rate.max())]
            ax.plot(bounds,bounds,ls="--",color="#777",lw=1)
            ax.set(title="Overall vs pressure strike rate",xlabel="Overall strike rate",ylabel="Pressure strike rate")
            p=outdir/"overall_vs_pressure_strike_rate.png"; _save(fig,p); paths.append(p)

    if not bowler_pressure.empty and not bowler.empty:
        z=bowler.merge(bowler_pressure,on=["player_id","player_name"],how="inner",validate="1:1",suffixes=("_overall","_pressure"))
        z=z[(z.legal_balls_overall>=120)&(z.pressure_legal_balls>=30)].dropna(subset=["economy_overall","pressure_economy"])
        if not z.empty:
            fig,ax=plt.subplots(figsize=(8,7))
            sns.scatterplot(data=z,x="economy_overall",y="pressure_economy",size="pressure_legal_balls",sizes=(25,240),color=PURPLE,alpha=.75,ax=ax)
            bounds=[min(z.economy_overall.min(),z.pressure_economy.min()),max(z.economy_overall.max(),z.pressure_economy.max())]
            ax.plot(bounds,bounds,ls="--",color=PINK,lw=1.5)
            ax.set(title="Overall vs pressure bowling economy",xlabel="Overall economy (runs per six legal balls)",ylabel="Pressure economy (classified extras)")
            p=outdir/"overall_vs_pressure_economy.png"; _save(fig,p); paths.append(p)

    for df, role, metric, label, title, color in [
        (death_bat,"batter","strike_rate","Strike rate","IPL death-over batting strike rate",PINK),
        (death_bowl,"bowler","economy","Economy","IPL death-over bowling economy",PURPLE),
    ]:
        if not df.empty:
            eligible=df[df.balls.ge(30)] if role=="batter" else df[df.legal_balls.ge(30)]
            if not eligible.empty:
                top=eligible.nlargest(12,metric).sort_values(metric)
                if role=="bowler": top=eligible.nsmallest(12,metric).sort_values(metric)
                fig,ax=plt.subplots(figsize=(10,6))
                ax.barh(top.player_name,top[metric],color=color)
                ax.set(title=title+" (minimum 30-ball sample)",xlabel=label,ylabel="")
                p=outdir/f"death_over_{role}_leaders.png"; _save(fig,p); paths.append(p)

    if not death_pressure_bat.empty or not death_pressure_bowl.empty:
        fig,(ax1,ax2)=plt.subplots(1,2,figsize=(13,6))
        vb=death_pressure_bat[(death_pressure_bat.balls>=20)&(death_pressure_bat.innings>=3)] if not death_pressure_bat.empty else pd.DataFrame()
        if not vb.empty:
            vb=vb.nlargest(8,"strike_rate").sort_values("strike_rate")
            ax1.barh(vb.player_name,vb.strike_rate,color=PINK);ax1.set_title("Batters · pressure death SR");ax1.set_xlabel("Strike rate")
        else: ax1.text(.5,.5,"No batter met the gate",ha="center",va="center",transform=ax1.transAxes)
        vw=death_pressure_bowl[(death_pressure_bowl.legal_balls>=30)&(death_pressure_bowl.innings>=3)] if not death_pressure_bowl.empty else pd.DataFrame()
        if not vw.empty:
            vw=vw.nsmallest(8,"economy").sort_values("economy")
            ax2.barh(vw.player_name,vw.economy,color=PURPLE);ax2.set_title("Bowlers · pressure death economy");ax2.set_xlabel("Runs per six legal balls")
        else: ax2.text(.5,.5,"No bowler met the gate",ha="center",va="center",transform=ax2.transAxes)
        fig.suptitle("Death overs under identified chase pressure",fontsize=15,fontweight="bold")
        p=outdir/"death_over_pressure_comparison.png";_save(fig,p);paths.append(p)

    if not batter.empty or not bowler.empty:
        fig,(ax1,ax2)=plt.subplots(1,2,figsize=(13,6))
        vb=batter[(batter.balls_faced>=120)&(batter.overall_innings_count>=10)].dropna(subset=["overall_innings_sr_sd"])
        if not vb.empty:
            sns.scatterplot(data=vb,x="strike_rate",y="overall_innings_sr_sd",size="balls_faced",sizes=(25,220),color=BLUE,alpha=.72,ax=ax1)
            ax1.set_title("Batters");ax1.set_xlabel("Overall strike rate");ax1.set_ylabel("SD of innings strike rate")
        vw=bowler[(bowler.legal_balls>=120)&(bowler.overall_bowling_innings>=10)].dropna(subset=["overall_innings_economy_sd"])
        if not vw.empty:
            sns.scatterplot(data=vw,x="economy",y="overall_innings_economy_sd",size="legal_balls",sizes=(25,220),color=PINK,alpha=.72,ax=ax2)
            ax2.set_title("Bowlers");ax2.set_xlabel("Overall economy");ax2.set_ylabel("SD of innings economy")
        fig.suptitle("Consistency across IPL innings (minimum ten innings)",fontsize=15,fontweight="bold")
        p=outdir/"player_consistency_profiles.png"; _save(fig,p); paths.append(p)

    state=deliveries[deliveries.state_valid_primary]
    if not state.empty:
        fig,ax=plt.subplots(figsize=(9,5.3))
        sns.histplot(state.pressure_margin.clip(-10,20),bins=32,color=PINK,ax=ax)
        ax.axvline(0,color=PURPLE,ls="--",label="Behind opening required rate")
        ax.set(title="Required-rate pressure margin in eligible IPL chases",xlabel="Current RRR minus opening RRR (runs/over; clipped for display)",ylabel="Pre-delivery states")
        ax.legend(frameon=False); p=outdir/"pressure_margin_distribution.png"; _save(fig,p); paths.append(p)

    if not pressure_sensitivity.empty:
        v=pressure_sensitivity[pressure_sensitivity.scenario.ne("primary_margin_gt_0")]
        if not v.empty:
            v=v.copy(); v["label"]=v.role+": "+v.scenario.str.replace("valid_state_top_quartile_margin_.*","top-quartile margin",regex=True)
            fig,ax=plt.subplots(figsize=(10,6))
            sns.barplot(data=v,x="top10_overlap",y="label",hue="role",palette=[PINK,PURPLE],dodge=False,ax=ax)
            ax.set(title="Top-10 overlap under alternative pressure definitions",xlabel="Players shared with primary top 10",ylabel="Sensitivity scenario")
            ax.set_xlim(0,10); p=outdir/"ranking_sensitivity_top10_overlap.png"; _save(fig,p); paths.append(p)

    return paths


def create_team_chart(outdir: Path, team_summary: pd.DataFrame) -> list[Path]:
    if team_summary.empty: return []
    name_col="team_name" if "team_name" in team_summary else "batting_team_name"
    v=team_summary.sort_values("runs_per_wicket",ascending=False).head(12).sort_values("runs_per_wicket")
    fig,ax=plt.subplots(figsize=(10,6))
    ax.barh(v[name_col],v.runs_per_wicket,color=[PINK if "Rajasthan" in x else PURPLE for x in v[name_col]])
    ax.set(title="IPL team batting productivity (2022-2026)",xlabel="Runs per recorded dismissal",ylabel="")
    p=outdir/"ipl_team_batting_productivity.png"; _save(fig,p); return [p]

