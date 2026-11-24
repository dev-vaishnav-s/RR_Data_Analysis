"""Run the complete Cricket Pressure Performance Analytics project."""
from __future__ import annotations

import json

from src.pipeline import run_pipeline


if __name__ == "__main__":
    result = run_pipeline()
    print(json.dumps({
        "primary_eligible_matches": result["prep"]["eligible_primary_matches"],
        "pressure_deliveries": result["prep"]["primary_pressure_deliveries"],
        "top_batters": result["top_bat"]["player_name"].tolist(),
        "top_bowlers": result["top_bowl"]["player_name"].tolist(),
        "ml": result["ml"],
        "source_hashes_unchanged": result["source_hashes_unchanged"],
        "presentation": result["presentation"],
    }, indent=2, ensure_ascii=False, default=str))
