"""
Global pipeline settings.

This module loads industry YAML configs from config/industries/ and provides
global constants used across the pipeline. The architecture is config-driven:
adding a new industry means adding a YAML file, not changing code.
"""
from pathlib import Path
import yaml

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
INDUSTRIES_DIR = CONFIG_DIR / "industries"
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_INTERIM = DATA_DIR / "interim"
DATA_PROCESSED = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

# Global constants
BASE_YEAR = 2020  # All monetary series deflated to this year's constant USD
DEFLATOR_INDICATOR = "NY.GDP.DEFL.ZS"  # World Bank GDP deflator — fetch with EVERY nominal series


def load_industry_config(industry_id: str) -> dict:
    """
    Load an industry configuration from config/industries/{industry_id}.yaml.

    Parameters
    ----------
    industry_id : str
        The industry identifier (e.g., "ai"). Must match a YAML filename.

    Returns
    -------
    dict
        Parsed YAML configuration.

    Raises
    ------
    FileNotFoundError
        If the YAML file does not exist.
    yaml.YAMLError
        If the YAML is malformed.
    """
    config_path = INDUSTRIES_DIR / f"{industry_id}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Industry config not found: {config_path}. "
            f"Available: {[f.stem for f in INDUSTRIES_DIR.glob('*.yaml')]}"
        )
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def list_available_industries() -> list[str]:
    """Return list of industry IDs with YAML configs in config/industries/."""
    return [f.stem for f in INDUSTRIES_DIR.glob("*.yaml")]


def get_all_economy_codes(config: dict) -> list[str]:
    """
    Extract a flat list of all economy ISO3 codes from an industry config.
    Used to build the World Bank API query.
    """
    codes = []
    for region in config.get("regions", []):
        codes.extend(region.get("economy_codes", []))
    return sorted(set(codes))
