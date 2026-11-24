"""Exploratory K-Means performance profiles; no supervised auction prediction."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def _cluster(frame: pd.DataFrame, features: list[str], role: str) -> tuple[pd.DataFrame, dict]:
    clean = frame.dropna(subset=features).copy()
    if len(clean) < 12:
        return pd.DataFrame(), {"role": role, "status": "not_run", "reason": "fewer than 12 complete player profiles", "n_players": int(len(clean))}
    X = StandardScaler().fit_transform(clean[features])
    results = []
    max_k = min(5, len(clean)-1)
    for k in range(2, max_k+1):
        model = KMeans(n_clusters=k, random_state=2027, n_init=30)
        labels = model.fit_predict(X)
        if len(np.unique(labels)) > 1:
            results.append((float(silhouette_score(X, labels)), k, labels))
    if not results:
        return pd.DataFrame(), {"role": role, "status": "not_run", "reason": "no valid cluster partition", "n_players": int(len(clean))}
    score, k, labels = max(results, key=lambda z: z[0])
    clean["cluster"] = labels + 1
    means = clean.groupby("cluster")[features].mean().round(2).to_dict("index")
    status = "exploratory" if score >= 0.15 else "weak_separation"
    if score < 0.15:
        return pd.DataFrame(), {"role": role, "status": status, "reason": "best silhouette below 0.15; no player profile labels reported", "n_players": int(len(clean)), "best_k": int(k), "best_silhouette": score, "candidate_silhouettes": {str(a[1]): a[0] for a in results}}
    clean["profile_role"] = role
    return clean, {"role": role, "status": status, "n_players": int(len(clean)), "best_k": int(k), "best_silhouette": score, "candidate_silhouettes": {str(a[1]): a[0] for a in results}, "cluster_means": means, "features": features}


def cluster_profiles(batting: pd.DataFrame, bowling: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    b = batting[batting.balls_faced.ge(150)].copy()
    w = bowling[bowling.legal_balls.ge(120)].copy()
    # Stable, interpretable per-player rates; pressure features are not used to define clusters.
    bframe, bs = _cluster(b, ["strike_rate", "batting_average", "boundary_run_share_pct", "dot_ball_pct"], "batter")
    w = w.copy()
    w["wickets_per_100_balls"] = np.where(w.legal_balls.gt(0), 100*w.wickets/w.legal_balls, np.nan)
    wframe, ws = _cluster(w, ["economy", "wickets_per_100_balls", "dot_ball_pct"], "bowler")
    frames=[f for f in [bframe,wframe] if not f.empty]
    combined=pd.concat(frames,ignore_index=True,sort=False) if frames else pd.DataFrame()
    return combined, {"supervised_prediction": "not implemented: no auction success or future performance target is supplied", "batters":bs,"bowlers":ws}

