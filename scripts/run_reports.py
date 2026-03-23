"""
Report generation runner.

Produces both PDF reports from real forecast data:
    reports/executive_brief.pdf  (5-8 pages, normal mode)
    reports/full_report.pdf      (15-25 pages, expert mode)

Usage:
    uv run python scripts/run_reports.py
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.reports.executive_brief import generate_executive_brief
from src.reports.full_report import generate_full_report


def main():
    print("Generating executive brief...")
    brief_path = generate_executive_brief()
    print(f"  Saved: {brief_path} ({brief_path.stat().st_size / 1024:.0f} KB)")

    print("Generating full report...")
    full_path = generate_full_report()
    print(f"  Saved: {full_path} ({full_path.stat().st_size / 1024:.0f} KB)")

    print("\nDone. Reports:")
    print(f"  Executive brief: {brief_path}")
    print(f"  Full report:     {full_path}")


if __name__ == "__main__":
    main()
