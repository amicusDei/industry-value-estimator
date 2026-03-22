#!/usr/bin/env python3
"""Launch the AI Industry Value Estimator dashboard."""
import sys
from pathlib import Path

# Ensure project root is on sys.path (established convention from Phase 02-05)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard.app import app

if __name__ == "__main__":
    print("Starting AI Industry Value Estimator dashboard...")
    print("Open http://127.0.0.1:8050 in your browser")
    app.run(debug=True, host="127.0.0.1", port=8050)
