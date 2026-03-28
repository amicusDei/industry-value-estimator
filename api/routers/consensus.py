"""Analyst consensus scope visualization endpoint."""

import yaml
from pathlib import Path
from fastapi import APIRouter

from api.data_loader import get_forecasts

router = APIRouter(prefix="/api/v1", tags=["consensus"])

DATA_RAW = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "industries"


@router.get("/analyst-consensus")
def analyst_consensus():
    """Return analyst firm estimates grouped by firm with scope metadata."""
    registry_path = DATA_RAW / "market_anchors" / "ai_analyst_registry.yaml"
    config_path = CONFIG_DIR / "ai.yaml"

    with open(registry_path) as f:
        registry = yaml.safe_load(f)
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Build scope mapping
    scope_map = {}
    for entry in config.get("scope_mapping_table", []):
        scope_map[entry["firm"]] = {
            "scope_alignment": entry.get("scope_alignment", "unknown"),
            "scope_coefficient": entry.get("scope_coefficient", 1.0),
            "includes": entry.get("includes", ""),
            "excludes": entry.get("excludes", ""),
        }

    # Group estimates by firm
    firms_data: dict[str, list] = {}
    for entry in registry.get("entries", []):
        firm = entry["source_firm"]
        if firm not in firms_data:
            firms_data[firm] = []
        firms_data[firm].append({
            "year": entry["estimate_year"],
            "value": entry["as_published_usd_billions"],
        })

    # Build response
    firms = []
    for firm, estimates in sorted(firms_data.items()):
        scope = scope_map.get(firm, {})
        firms.append({
            "firm": firm,
            "scope_alignment": scope.get("scope_alignment", "unknown"),
            "scope_coefficient": scope.get("scope_coefficient", 1.0),
            "estimates": sorted(estimates, key=lambda e: e["year"]),
            "scope_includes": scope.get("includes", ""),
            "scope_excludes": scope.get("excludes", ""),
        })

    # Our median for 2024 (from forecast data)
    df = get_forecasts()
    our_median = None
    if not df.empty and "quarter" in df.columns:
        q4_2024 = df[(df["year"] == 2024) & (df["quarter"] == 4)]
        if not q4_2024.empty:
            our_median = round(float(q4_2024["point_estimate_nominal"].sum()), 1)

    return {"firms": firms, "our_median_2024": our_median}
