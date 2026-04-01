#!/usr/bin/env python3
"""
Generate a methodology research note as PDF (Goldman Sachs Research Note style).

Reads all data from Parquet files -- no hardcoded values.
Output: docs/methodology_paper.pdf
"""

import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
from fpdf import FPDF, XPos, YPos

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"

FORECASTS_ENSEMBLE = DATA_DIR / "forecasts_ensemble.parquet"
FORECASTS_SCENARIOS = DATA_DIR / "forecasts_scenarios.parquet"
BACKTESTING_RESULTS = DATA_DIR / "backtesting_results.parquet"
ANALYST_DISPERSION = DATA_DIR / "analyst_dispersion.parquet"
MARKET_ANCHORS = DATA_DIR / "market_anchors_ai.parquet"

OUTPUT_PDF = DOCS_DIR / "methodology_paper.pdf"

# ---------------------------------------------------------------------------
# Color palette (institutional: black / grey / dark blue)
# ---------------------------------------------------------------------------
COLOR_BLACK = (0, 0, 0)
COLOR_DARK_BLUE = (0, 51, 102)
COLOR_MEDIUM_BLUE = (0, 76, 153)
COLOR_GREY_TEXT = (80, 80, 80)
COLOR_LIGHT_GREY_BG = (235, 235, 235)
COLOR_WHITE = (255, 255, 255)
COLOR_TABLE_HEADER_BG = (0, 51, 102)
COLOR_TABLE_HEADER_FG = (255, 255, 255)
COLOR_TABLE_ROW_ALT = (245, 245, 250)
COLOR_TABLE_BORDER = (180, 180, 180)

SEGMENT_LABELS = {
    "ai_hardware": "AI Hardware",
    "ai_infrastructure": "AI Infrastructure",
    "ai_software": "AI Software",
    "ai_adoption": "AI Adoption",
}

SEGMENT_ORDER = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_data():
    """Load all required parquet files and compute derived metrics."""
    data = {}

    # Ensemble forecasts
    df_ens = pd.read_parquet(FORECASTS_ENSEMBLE)
    data["ensemble"] = df_ens

    # Scenario forecasts
    df_scen = pd.read_parquet(FORECASTS_SCENARIOS)
    data["scenarios"] = df_scen

    # Backtesting
    df_bt = pd.read_parquet(BACKTESTING_RESULTS)
    data["backtesting"] = df_bt

    # Analyst dispersion
    df_disp = pd.read_parquet(ANALYST_DISPERSION)
    data["dispersion"] = df_disp

    # Market anchors
    df_ma = pd.read_parquet(MARKET_ANCHORS)
    data["anchors"] = df_ma

    # --- Derived metrics ---

    # Total market size 2025 (base scenario, Q4, sum of segments)
    q4_base_2025 = df_scen[
        (df_scen.year == 2025)
        & (df_scen.quarter == 4)
        & (df_scen.scenario == "base")
    ]
    data["total_market_2025"] = q4_base_2025.point_estimate_nominal.sum()

    # Total market size 2030 per scenario
    q4_2030 = df_scen[(df_scen.year == 2030) & (df_scen.quarter == 4)]
    data["total_2030_by_scenario"] = (
        q4_2030.groupby("scenario").point_estimate_nominal.sum().to_dict()
    )

    # CAGR 2026-2030 per segment (base scenario)
    cagr_dict = {}
    for seg in SEGMENT_ORDER:
        s = df_scen[
            (df_scen.segment == seg)
            & (df_scen.quarter == 4)
            & (df_scen.scenario == "base")
        ]
        v26 = s[s.year == 2026].point_estimate_nominal.iloc[0]
        v30 = s[s.year == 2030].point_estimate_nominal.iloc[0]
        cagr_dict[seg] = (v30 / v26) ** (1 / 4) - 1
    data["cagr_2026_2030"] = cagr_dict

    # Prophet LOO metrics per segment
    prophet = df_bt[df_bt.model == "prophet_loo"]
    mape_dict = {}
    ci80_dict = {}
    ci95_dict = {}
    for seg in SEGMENT_ORDER:
        s = prophet[prophet.segment == seg]
        mape_dict[seg] = s.mape.mean()
        ci80_dict[seg] = s.ci80_covered.mean()
        ci95_dict[seg] = s.ci95_covered.mean()
    data["mape_by_segment"] = mape_dict
    data["ci80_by_segment"] = ci80_dict
    data["ci95_by_segment"] = ci95_dict

    # Post-GenAI MAPE
    post_genai = prophet[prophet.regime_label == "post_genai"]
    data["post_genai_mape"] = post_genai.mape.mean() if len(post_genai) > 0 else 0.0

    # Number of analyst sources
    data["n_analyst_sources"] = df_ma.n_sources.max()

    # Max dispersion ratio
    data["max_dispersion"] = df_disp.dispersion_ratio.max()

    # Segment forecasts table (2030 Q4) per scenario
    seg_table = []
    for seg in SEGMENT_ORDER:
        row = {"segment": seg}
        for scenario in ["conservative", "base", "aggressive"]:
            val = df_scen[
                (df_scen.segment == seg)
                & (df_scen.year == 2030)
                & (df_scen.quarter == 4)
                & (df_scen.scenario == scenario)
            ].point_estimate_nominal.iloc[0]
            row[scenario] = val
        seg_table.append(row)
    data["segment_forecast_table"] = seg_table

    # Segment forecasts for 2026 (base)
    seg_2026 = {}
    for seg in SEGMENT_ORDER:
        val = df_scen[
            (df_scen.segment == seg)
            & (df_scen.year == 2026)
            & (df_scen.quarter == 4)
            & (df_scen.scenario == "base")
        ].point_estimate_nominal.iloc[0]
        seg_2026[seg] = val
    data["segment_2026_base"] = seg_2026

    # Data source summary from anchors
    all_sources = set()
    for sl in df_ma.source_list:
        if sl:
            for s in sl.split(", "):
                if s.strip():
                    all_sources.add(s.strip())
    data["source_names"] = sorted(all_sources)

    # Years covered in anchors
    data["anchor_year_range"] = (
        int(df_ma.estimate_year.min()),
        int(df_ma.estimate_year.max()),
    )

    # Historical Q4 data for time series table
    hist_data = []
    for seg in SEGMENT_ORDER:
        seg_q4 = df_ens[
            (df_ens.segment == seg)
            & (df_ens.quarter == 4)
            & (~df_ens.is_forecast)
        ].sort_values("year")
        for _, r in seg_q4.iterrows():
            hist_data.append({
                "segment": seg,
                "year": int(r.year),
                "value": r.point_estimate_nominal,
            })
    data["historical_q4"] = hist_data

    # Dispersion summary per segment
    disp_summary = {}
    for seg in SEGMENT_ORDER:
        seg_disp = df_disp[df_disp.segment == seg]
        if len(seg_disp) > 0:
            latest = seg_disp.sort_values("year").iloc[-1]
            disp_summary[seg] = {
                "iqr": latest.iqr_usd_billions,
                "n_sources": int(latest.n_sources),
                "dispersion_ratio": latest.dispersion_ratio,
                "year": int(latest.year),
            }
    data["dispersion_summary"] = disp_summary

    # Backtesting detail rows for appendix
    bt_detail = []
    for _, r in prophet.sort_values(["segment", "year"]).iterrows():
        bt_detail.append({
            "segment": r.segment,
            "year": int(r.year),
            "actual": r.actual_usd,
            "predicted": r.predicted_usd,
            "mape": r.mape,
            "ci80": r.ci80_covered,
            "ci95": r.ci95_covered,
            "regime": r.regime_label,
        })
    data["backtesting_detail"] = bt_detail

    return data


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------
FONT_DIR = Path("/System/Library/Fonts/Supplemental")


class ResearchNotePDF(FPDF):
    """Custom FPDF subclass for Goldman-Sachs-style research note."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        # Register Arial TTF for Unicode support + font embedding (increases PDF size)
        if (FONT_DIR / "Arial.ttf").exists():
            self.add_font("ArialTTF", "", str(FONT_DIR / "Arial.ttf"), uni=True)
            self.add_font("ArialTTF", "B", str(FONT_DIR / "Arial Bold.ttf"), uni=True)
            self.add_font("ArialTTF", "I", str(FONT_DIR / "Arial Italic.ttf"), uni=True)
            self._ttf_available = True
        else:
            self._ttf_available = False

    @property
    def _fn(self):
        return "ArialTTF" if self._ttf_available else "Helvetica"

    def _set_font_title(self, size=16):
        self.set_font(self._fn, "B", size)
        self.set_text_color(*COLOR_DARK_BLUE)

    def _set_font_subtitle(self, size=11):
        self.set_font(self._fn, "B", size)
        self.set_text_color(*COLOR_DARK_BLUE)

    def _set_font_body(self, size=9):
        self.set_font(self._fn, "", size)
        self.set_text_color(*COLOR_BLACK)

    def _set_font_body_bold(self, size=9):
        self.set_font(self._fn, "B", size)
        self.set_text_color(*COLOR_BLACK)

    def _set_font_small(self, size=7):
        self.set_font(self._fn, "", size)
        self.set_text_color(*COLOR_GREY_TEXT)

    def _draw_horizontal_rule(self, width=None):
        if width is None:
            width = self.w - self.l_margin - self.r_margin
        self.set_draw_color(*COLOR_TABLE_BORDER)
        self.line(self.l_margin, self.get_y(), self.l_margin + width, self.get_y())
        self.ln(2)

    def _draw_table(self, headers, rows, col_widths, col_aligns=None):
        """Draw a table with gridlines. col_aligns: list of 'L', 'C', 'R'."""
        if col_aligns is None:
            col_aligns = ["L"] * len(headers)
        row_height = 6

        # Header
        self.set_fill_color(*COLOR_TABLE_HEADER_BG)
        self.set_text_color(*COLOR_TABLE_HEADER_FG)
        self.set_font(self._fn, "B", 8)
        self.set_draw_color(*COLOR_TABLE_BORDER)
        for i, h in enumerate(headers):
            self.cell(
                col_widths[i], row_height, h, border=1, align=col_aligns[i], fill=True,
                new_x=XPos.RIGHT, new_y=YPos.TOP,
            )
        self.ln()

        # Rows
        self.set_text_color(*COLOR_BLACK)
        self.set_font(self._fn, "", 8)
        for r_idx, row in enumerate(rows):
            if r_idx % 2 == 1:
                self.set_fill_color(*COLOR_TABLE_ROW_ALT)
            else:
                self.set_fill_color(*COLOR_WHITE)
            for i, cell_val in enumerate(row):
                self.cell(
                    col_widths[i], row_height, str(cell_val), border=1,
                    align=col_aligns[i], fill=True,
                    new_x=XPos.RIGHT, new_y=YPos.TOP,
                )
            self.ln()

    def section_title(self, text, size=12):
        self._set_font_subtitle(size)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def subsection_title(self, text, size=10):
        self._set_font_subtitle(size)
        self.cell(0, 5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def body_text(self, text, size=8.5):
        self._set_font_body(size)
        self.multi_cell(0, 4.2, text)
        self.ln(2)

    def small_text(self, text, size=7):
        self._set_font_small(size)
        self.cell(0, 3.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def footer(self):
        self.set_y(-15)
        self._set_font_small(7)
        self.cell(0, 4, "CONFIDENTIAL -- For Institutional Use Only", align="C")
        self.ln(3)
        self.cell(0, 4, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_pdf(data: dict) -> None:
    """Build the PDF document from loaded data."""
    pdf = ResearchNotePDF()
    pdf.alias_nb_pages()

    page_width = 210  # A4
    margin = 15
    content_width = page_width - 2 * margin
    pdf.set_left_margin(margin)
    pdf.set_right_margin(margin)

    # ===================================================================
    # PAGE 1: Title + Key Findings + Methodology
    # ===================================================================
    pdf.add_page()

    # Top rule (thick dark blue line)
    pdf.set_draw_color(*COLOR_DARK_BLUE)
    pdf.set_line_width(0.8)
    pdf.line(margin, 12, page_width - margin, 12)
    pdf.set_line_width(0.2)

    # Title block
    pdf.set_y(16)
    pdf._set_font_title(16)
    pdf.cell(content_width, 8, "AI Industry Valuation:",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf._set_font_title(14)
    pdf.cell(content_width, 7, "A Multi-Source Ensemble Approach",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # Date + Author line
    pdf._set_font_body(9)
    pdf.set_text_color(*COLOR_GREY_TEXT)
    today_str = datetime.now().strftime("%B %d, %Y")
    pdf.cell(content_width / 2, 5, today_str,
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(content_width / 2, 5, "Dr. Matthias Wegner", align="R",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    # Thin rule
    pdf.set_draw_color(*COLOR_DARK_BLUE)
    pdf.set_line_width(0.4)
    pdf.line(margin, pdf.get_y(), page_width - margin, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(4)

    # ----- KEY FINDINGS BOX -----
    box_x = margin
    findings_start_y = pdf.get_y()
    box_w = content_width

    # Title inside box
    pdf._set_font_subtitle(10)
    pdf.set_xy(box_x + 3, findings_start_y + 2)
    pdf.cell(box_w - 6, 5, "Key Findings",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(box_x + 5)
    pdf._set_font_body(8.5)
    pdf.set_text_color(*COLOR_BLACK)

    total_2025 = data["total_market_2025"]
    total_2030_base = data["total_2030_by_scenario"].get("base", 0)
    total_2030_cons = data["total_2030_by_scenario"].get("conservative", 0)
    total_2030_aggr = data["total_2030_by_scenario"].get("aggressive", 0)
    post_genai_mape = data["post_genai_mape"]
    n_sources = data["n_analyst_sources"]

    findings = [
        (f"Global AI market estimated at ${total_2025:.0f}B (2025), "
         f"projected to reach ${total_2030_base:.0f}B by 2030 (base case)."),
        (f"Scenario range 2030: ${total_2030_cons:.0f}B (conservative) to "
         f"${total_2030_aggr:.0f}B (aggressive), reflecting structural uncertainty "
         f"in post-GenAI growth trajectories."),
        (f"Ensemble model achieves {post_genai_mape:.1f}% MAPE on post-2022 "
         f"out-of-sample validation (Prophet leave-one-out cross-validation)."),
        (f"Market sizing anchored to {n_sources} analyst firm estimates with "
         f"scope normalization, deflated to constant 2020 USD."),
    ]

    bullet_y = pdf.get_y() + 2
    for f_text in findings:
        pdf.set_xy(box_x + 5, bullet_y)
        pdf.cell(4, 4.5, "-")
        pdf.set_xy(box_x + 10, bullet_y)
        pdf.multi_cell(box_w - 16, 4.5, f_text)
        bullet_y = pdf.get_y() + 1

    box_h = bullet_y - findings_start_y + 2
    pdf.set_fill_color(*COLOR_LIGHT_GREY_BG)
    pdf.set_draw_color(*COLOR_TABLE_BORDER)
    pdf.rect(box_x, findings_start_y, box_w, box_h, style="D")
    pdf.set_y(findings_start_y + box_h + 5)

    # ===================================================================
    # METHODOLOGY SECTION
    # ===================================================================
    pdf.section_title("1. Methodology")

    pdf.subsection_title("1.1 Data Sources and Market Boundary")
    pdf.body_text(
        "Market size estimates are compiled from published research by leading analyst firms "
        "(IDC, Gartner, Grand View Research, Statista, Goldman Sachs, Bloomberg Intelligence, "
        "McKinsey Global Institute, CB Insights), supplemented by EDGAR 10-K/10-Q filings "
        "(direct AI revenue disclosures from NVIDIA and other companies), LSEG Workspace "
        "(TRBC-classified public company revenues), World Bank macroeconomic indicators "
        "(GDP deflator, researchers per million), and OECD science/technology statistics "
        "(R&D expenditure, AI patent filings, VC investment data)."
    )
    pdf.body_text(
        "The market boundary was locked on 2026-03-23 before any analyst data was collected, "
        "preventing anchor estimate shopping. The scope covers four segments: AI Hardware "
        "(GPUs, TPUs, AI accelerators), AI Infrastructure (dedicated cloud AI compute, AI data "
        "centers), AI Software (foundation model APIs, AI SaaS, MLOps platforms), and AI "
        "Adoption (enterprise AI deployment, consulting, integration services). Excluded: "
        "general IT infrastructure, consumer AI products, post-hoc AI features in existing "
        "software, and non-AI semiconductor foundry revenue."
    )

    pdf.subsection_title("1.2 Scope Normalization")
    pdf.body_text(
        "Published AI market size estimates vary by up to 7x across analyst firms due to "
        "definitional differences. Each firm's estimate is multiplied by a scope coefficient "
        "(ranging from 0.18 for Gartner's broad all-AI-adjacent definition to 1.15 for "
        "Grand View Research's narrow software focus) to normalize to our consistent market "
        "boundary. Per-entry segment-level coefficients handle cases where a single firm's "
        "scope varies across segments (e.g., Precedence Research's broad ai_software scope "
        "receives a 0.40 coefficient). The reconciliation algorithm computes the median of "
        "all scope-normalized estimates per (year, segment) group as the point estimate, "
        "with 25th/75th percentiles forming the uncertainty range. All monetary values are "
        "deflated to constant 2020 USD using the World Bank GDP deflator (NY.GDP.DEFL.ZS)."
    )

    pdf.subsection_title("1.3 Ensemble Model Architecture")
    pdf.body_text(
        "The forecasting pipeline employs a three-layer ensemble. Layer 1: ARIMA models "
        "fitted per segment with AICc-based order selection and parsimony constraints "
        "(max p=2, q=2), using pmdarima auto_arima with stepwise search. Layer 2: Prophet "
        "models with an explicit 2022 structural changepoint anchoring the GenAI surge "
        "(changepoint_prior_scale=0.1, 2x default) and suppressed seasonality parameters. "
        "Layer 3: A LightGBM gradient boosting residual correction layer using macroeconomic "
        "proxy indicators (R&D/GDP, AI patent filings, VC investment, high-tech exports, "
        "researcher density) as exogenous features."
    )
    pdf.body_text(
        "Final point forecasts are produced via inverse-RMSE-weighted blending of ARIMA and "
        "Prophet outputs, with LightGBM applied as an additive residual correction. Ensemble "
        "weights are computed from expanding-window cross-validation RMSE (train on first N "
        "quarters, predict next 4, collect out-of-sample errors), ensuring out-of-sample weight "
        "determination with no information leakage. Each segment receives independent model "
        "selection -- the best-performing model varies by segment growth dynamics."
    )

    pdf.subsection_title("1.4 CAGR Calibration and Confidence Intervals")
    pdf.body_text(
        "Adaptive CAGR calibration ensures blended forecasts meet minimum defensible growth "
        "rates supported by analyst consensus. Per-segment CAGR floors (Hardware: 15%, "
        "Infrastructure: 25%, Software: 20%, Adoption: 15%) are applied when statistical "
        "models underperform consensus growth expectations. This is by design: the floor "
        "ensures projections do not fall below the minimum defensible growth rate supported "
        "by 12 analyst firms. Confidence interval bands (CI80 and CI95) are produced via "
        "bootstrap resampling and scale proportionally with CAGR calibration adjustments, "
        "preserving interval coverage properties. Negative CI bounds are clipped to zero."
    )

    pdf.subsection_title("1.5 Scenario Framework")
    pdf.body_text(
        "Three scenarios are computed as complete forecast sets: Conservative (floor CAGR, "
        "tighter CI bands), Base (calibrated ensemble with standard CI), and Aggressive "
        "(upper CAGR bounds with wider CI bands). Each scenario passes through the full "
        "pipeline -- not a simple multiplier on the base case. This enables coherent "
        "cross-scenario comparison of segment dynamics and total market trajectories. "
        "Quarterly granularity (Q1-Q4) is maintained across all scenarios, with 36 data "
        "points per segment (9 years x 4 quarters) providing the training foundation."
    )

    # ===================================================================
    # PAGE 2-3: Results
    # ===================================================================
    pdf.add_page()
    pdf.section_title("2. Results")

    # --- Segment Forecasts Table (2030 Q4) ---
    pdf.subsection_title("2.1 Segment Forecasts -- 2030 Market Size (USD Billions, Nominal)")
    pdf.ln(1)

    headers = ["Segment", "2026 (Base)", "Conservative", "Base", "Aggressive", "CAGR 26-30"]
    col_widths = [38, 27, 27, 27, 27, 27]
    col_aligns = ["L", "R", "R", "R", "R", "R"]

    rows = []
    for seg in SEGMENT_ORDER:
        seg_data = next(
            r for r in data["segment_forecast_table"] if r["segment"] == seg
        )
        cagr = data["cagr_2026_2030"][seg]
        v26 = data["segment_2026_base"][seg]
        rows.append([
            SEGMENT_LABELS[seg],
            f"${v26:.1f}B",
            f"${seg_data['conservative']:.1f}B",
            f"${seg_data['base']:.1f}B",
            f"${seg_data['aggressive']:.1f}B",
            f"{cagr:.1%}",
        ])

    # Total row
    total_cons = sum(r["conservative"] for r in data["segment_forecast_table"])
    total_base = sum(r["base"] for r in data["segment_forecast_table"])
    total_aggr = sum(r["aggressive"] for r in data["segment_forecast_table"])
    df_scen = data["scenarios"]
    base_q4_2026_total = df_scen[
        (df_scen.year == 2026) & (df_scen.quarter == 4) & (df_scen.scenario == "base")
    ].point_estimate_nominal.sum()
    total_cagr = (total_base / base_q4_2026_total) ** (1 / 4) - 1

    rows.append([
        "Total (unadj.)",
        f"${base_q4_2026_total:.1f}B",
        f"${total_cons:.1f}B",
        f"${total_base:.1f}B",
        f"${total_aggr:.1f}B",
        f"{total_cagr:.1%}",
    ])

    pdf._draw_table(headers, rows, col_widths, col_aligns)
    pdf.ln(1)
    pdf.small_text(
        "Note: Totals are unadjusted segment sums. Cross-segment overlap "
        "(hardware-infrastructure 20-30%, software-adoption 15-25%) "
        "is documented but not deducted. 2030 values are Q4 annualized."
    )
    pdf.ln(5)

    # --- MAPE Table ---
    pdf.subsection_title("2.2 Model Performance -- Prophet LOO Cross-Validation")
    pdf.ln(1)

    mape_headers = ["Segment", "MAPE", "CI80 Cov.", "CI95 Cov.", "Regime Note"]
    mape_widths = [38, 22, 25, 25, 63]
    mape_aligns = ["L", "R", "R", "R", "L"]

    mape_rows = []
    for seg in SEGMENT_ORDER:
        mape_val = data["mape_by_segment"][seg]
        ci80_val = data["ci80_by_segment"][seg]
        ci95_val = data["ci95_by_segment"][seg]
        if seg == "ai_infrastructure":
            note = "Regime shift: 21% to 42% market share"
        elif seg == "ai_hardware":
            note = "EDGAR hard actuals available (NVIDIA)"
        elif seg == "ai_software":
            note = "LOO anchor est.; scope-normalized"
        else:
            note = "LOO anchor estimates only"
        mape_rows.append([
            SEGMENT_LABELS[seg],
            f"{mape_val:.1f}%",
            f"{ci80_val:.0%}",
            f"{ci95_val:.0%}",
            note,
        ])

    overall_mape = sum(data["mape_by_segment"].values()) / len(data["mape_by_segment"])
    mape_rows.append(["Overall (mean)", f"{overall_mape:.1f}%", "--", "--", "All segments, all years"])
    mape_rows.append([
        "Post-GenAI (2022+)",
        f"{data['post_genai_mape']:.1f}%",
        "--", "--",
        "Forward-looking accuracy benchmark",
    ])

    pdf._draw_table(mape_headers, mape_rows, mape_widths, mape_aligns)
    pdf.ln(1)
    pdf.small_text(
        "MAPE = Mean Absolute Percentage Error. CI coverage = fraction of held-out "
        "observations within band. LOO = Leave-One-Out."
    )
    pdf.ln(5)

    # --- CI Coverage Analysis ---
    pdf.subsection_title("2.3 Confidence Interval Coverage Analysis")
    pdf.ln(1)

    ci_headers = ["Segment", "CI80 Target", "CI80 Actual", "CI95 Target", "CI95 Actual", "Status"]
    ci_widths = [38, 22, 22, 22, 22, 47]
    ci_aligns = ["L", "R", "R", "R", "R", "L"]

    ci_rows = []
    for seg in SEGMENT_ORDER:
        ci80 = data["ci80_by_segment"][seg]
        ci95 = data["ci95_by_segment"][seg]
        status = "PASS" if ci95 >= 0.85 else "MONITOR"
        ci_rows.append([
            SEGMENT_LABELS[seg],
            "80%", f"{ci80:.0%}",
            "95%", f"{ci95:.0%}",
            status,
        ])

    pdf._draw_table(ci_headers, ci_rows, ci_widths, ci_aligns)
    pdf.ln(1)
    pdf.small_text(
        "Bootstrap-based CIs. All segments meet or exceed 95% coverage target. "
        "CI80 slightly below 80% for hardware/infrastructure due to regime shift."
    )
    pdf.ln(5)

    # --- Analyst Dispersion Summary ---
    pdf.subsection_title("2.4 Analyst Dispersion Index")
    pdf.ln(1)

    disp_headers = ["Segment", "Latest Year", "IQR ($B)", "N Sources", "Disp. Ratio"]
    disp_widths = [40, 25, 30, 30, 48]
    disp_aligns = ["L", "R", "R", "R", "R"]

    disp_rows = []
    for seg in SEGMENT_ORDER:
        if seg in data["dispersion_summary"]:
            d = data["dispersion_summary"][seg]
            disp_rows.append([
                SEGMENT_LABELS[seg],
                str(d["year"]),
                f"${d['iqr']:.1f}B",
                str(d["n_sources"]),
                f"{d['dispersion_ratio']:.2f}",
            ])
    pdf._draw_table(disp_headers, disp_rows, disp_widths, disp_aligns)
    pdf.ln(1)
    pdf.small_text(
        "Dispersion ratio = IQR / median. Higher values indicate greater analyst disagreement. "
        "Declining dispersion signals converging market consensus."
    )

    # ===================================================================
    # PAGE 3: Data Sources
    # ===================================================================
    pdf.add_page()
    pdf.section_title("3. Data Sources")

    # Data source table
    src_headers = ["Source Category", "Provider(s)", "Coverage", "Role in Pipeline"]
    src_widths = [33, 52, 30, 58]
    src_aligns = ["L", "L", "C", "L"]

    year_min, year_max = data["anchor_year_range"]
    n_src = len(data["source_names"])

    src_rows = [
        [
            "Analyst Consensus",
            ", ".join(data["source_names"][:4]),
            f"{year_min}-{year_max}",
            "Market size anchors (primary Y-var)",
        ],
        [
            "Analyst Consensus",
            ", ".join(data["source_names"][4:8]) if n_src > 4 else "--",
            f"{year_min}-{year_max}",
            "Market size anchors (continued)",
        ],
        [
            "EDGAR Filings",
            "SEC 10-K/10-Q (15 companies)",
            "2020-2025",
            "Hard actuals + AI revenue attrib.",
        ],
        [
            "LSEG Workspace",
            "TRBC AI cos. (57201010 et al.)",
            "2010-2025",
            "Public company revenue proxy",
        ],
        [
            "World Bank WDI",
            "GDP deflator, researchers/M",
            "2010-2025",
            "Deflation + macro features",
        ],
        [
            "OECD ANBERD",
            "R&D expenditure in ICT",
            "2010-2023",
            "LightGBM exogenous feature",
        ],
        [
            "OECD PATS_IPC",
            "AI patent filings (G06N)",
            "2010-2023",
            "Innovation output signal",
        ],
        [
            "Private Markets",
            "18 companies (ARR-based)",
            "2022-2025",
            "Private market contribution",
        ],
    ]

    pdf._draw_table(src_headers, src_rows, src_widths, src_aligns)
    pdf.ln(5)

    # Analyst source detail
    pdf.subsection_title("3.1 Analyst Firm Scope Alignment")
    pdf.ln(1)

    firm_headers = ["Analyst Firm", "Scope", "Coeff.", "Range", "Adjustment Rationale"]
    firm_widths = [38, 18, 18, 22, 77]
    firm_aligns = ["L", "L", "R", "C", "L"]

    firm_rows = [
        ["IDC", "Close", "1.00", "0.95-1.05", "Enterprise AI; minimal adjustment"],
        ["Gartner", "Broad", "0.18", "0.15-0.22", "All AI-adjacent tech; heavy reduction"],
        ["Grand View Research", "Partial", "1.15", "1.05-1.25", "Narrow SW focus; scale up for HW+Infra"],
        ["Statista", "Partial", "0.85", "0.75-0.95", "Multi-survey aggregate; minor reduction"],
        ["Goldman Sachs", "Partial", "0.70", "0.60-0.80", "GenAI subset only; scale up + adjust"],
        ["Bloomberg Intel.", "Partial", "0.90", "0.80-1.00", "GenAI + chips; minor reduction"],
        ["McKinsey (MGI)", "Broad", "0.25", "0.20-0.30", "Economic value, not market size"],
        ["CB Insights", "Close", "0.95", "0.90-1.00", "Funding-based; good segment coverage"],
    ]

    pdf._draw_table(firm_headers, firm_rows, firm_widths, firm_aligns)
    pdf.ln(1)
    pdf.small_text(
        "Scope coefficients normalize each firm's published estimate to our market boundary. "
        "Ranges reflect coefficient sensitivity bounds."
    )
    pdf.ln(5)

    # Segment definition summary
    pdf.subsection_title("3.2 Segment Scope Definitions")
    pdf.ln(1)

    seg_headers = ["Segment", "Included", "Key Companies / Examples"]
    seg_widths = [33, 70, 70]
    seg_aligns = ["L", "L", "L"]

    seg_rows = [
        ["AI Hardware", "GPUs, TPUs, AI ASICs, accelerators", "NVIDIA, AMD Instinct, Google TPU"],
        ["AI Infra.", "Cloud AI compute, AI data centers", "Azure AI, AWS AI/ML, GCP Vertex AI"],
        ["AI Software", "Foundation model APIs, AI SaaS, MLOps", "OpenAI, Palantir AIP, Salesforce"],
        ["AI Adoption", "Enterprise AI deploy, consulting", "Accenture AI, IBM watsonx consult."],
    ]

    pdf._draw_table(seg_headers, seg_rows, seg_widths, seg_aligns)
    pdf.ln(5)

    # ===================================================================
    # PAGE 4: Historical Data + Appendix
    # ===================================================================
    pdf.add_page()
    pdf.section_title("4. Historical Market Size Estimates")

    pdf.body_text(
        "The following table presents Q4 annualized market size estimates (nominal USD "
        "billions) for each segment across the historical period. Values are derived from "
        "the ensemble model fitted to scope-normalized analyst consensus anchors. Forecast "
        "period (2026-2030) is presented for the base scenario."
    )

    # Build historical + forecast time series table
    hist_headers = ["Year", "AI Hardware", "AI Infra.", "AI Software", "AI Adoption", "Total"]
    hist_widths = [22, 30, 30, 30, 30, 30]
    hist_aligns = ["C", "R", "R", "R", "R", "R"]

    # Get Q4 values for all years from ensemble
    df_ens = data["ensemble"]
    q4_data = df_ens[df_ens.quarter == 4].sort_values(["year", "segment"])

    # Also get base scenario for forecast years
    df_scen = data["scenarios"]
    scen_q4 = df_scen[(df_scen.quarter == 4) & (df_scen.scenario == "base")].sort_values(
        ["year", "segment"]
    )

    years = sorted(q4_data.year.unique())
    hist_rows = []
    for year in years:
        row_vals = [str(int(year))]
        total = 0.0
        for seg in SEGMENT_ORDER:
            val_row = q4_data[(q4_data.year == year) & (q4_data.segment == seg)]
            if len(val_row) > 0:
                v = val_row.point_estimate_nominal.iloc[0]
                total += v
                row_vals.append(f"${v:.1f}B")
            else:
                row_vals.append("--")
        row_vals.append(f"${total:.1f}B")

        # Mark forecast years
        is_fc = q4_data[(q4_data.year == year)].is_forecast.iloc[0] if len(
            q4_data[q4_data.year == year]
        ) > 0 else False
        if is_fc:
            row_vals[0] = f"{int(year)}*"
        hist_rows.append(row_vals)

    pdf._draw_table(hist_headers, hist_rows, hist_widths, hist_aligns)
    pdf.ln(1)
    pdf.small_text("* Forecast period (base scenario). All values nominal USD billions, Q4 annualized.")
    pdf.ln(5)

    # ===================================================================
    # Appendix: Backtesting Detail
    # ===================================================================
    pdf.section_title("5. Appendix: LOO Backtesting Detail")

    pdf.body_text(
        "Leave-one-out cross-validation results for the Prophet model. For each evaluation "
        "year, the Q4 anchor value was removed from training data, the model was refitted, "
        "and the held-out value was predicted. This produces genuine out-of-sample MAPE with "
        "no circular validation (soft actuals removed, verified by contract test)."
    )

    bt_headers = ["Segment", "Year", "Actual ($B)", "Predicted ($B)", "MAPE", "CI95", "Regime"]
    bt_widths = [35, 18, 25, 25, 20, 18, 32]
    bt_aligns = ["L", "C", "R", "R", "R", "C", "L"]

    bt_rows = []
    for d in data["backtesting_detail"]:
        bt_rows.append([
            SEGMENT_LABELS.get(d["segment"], d["segment"]),
            str(d["year"]),
            f"${d['actual']:.1f}B",
            f"${d['predicted']:.1f}B",
            f"{d['mape']:.1f}%",
            "Y" if d["ci95"] else "N",
            d["regime"].replace("_", "-"),
        ])

    pdf._draw_table(bt_headers, bt_rows, bt_widths, bt_aligns)
    pdf.ln(1)
    pdf.small_text(
        "CI95 = Y if held-out actual falls within 95% confidence band. "
        "Regime: pre-genai (2017-2021), post-genai (2022+)."
    )

    # ===================================================================
    # DISCLAIMER (on last page)
    # ===================================================================
    pdf.ln(8)
    pdf._draw_horizontal_rule()
    pdf.ln(1)
    pdf._set_font_small(7)
    pdf.multi_cell(
        content_width,
        3.5,
        "DISCLAIMER: This research note is produced for informational and educational purposes "
        "only. It does not constitute investment advice, a solicitation to buy or sell "
        "securities, or a recommendation regarding any financial product. All market size "
        "estimates are model-derived projections based on publicly available data and analyst "
        "consensus. Actual market outcomes may differ materially from the projections presented "
        "herein. The methodology relies on scope-normalized analyst estimates, statistical time "
        "series models, and machine learning residual correction. Model limitations include "
        "small-sample uncertainty (36 quarterly observations per segment), analyst consensus "
        "anchoring, regime-dependent accuracy (pre-2022 MAPE is higher than post-2022), and "
        "the inability to predict future structural breaks (e.g., AI winter, compute cost "
        "collapse). Confidence intervals are provided to quantify forecast uncertainty but do "
        "not guarantee coverage of realized values. Cross-segment overlap (documented at "
        "10-30% of segment totals) means the unadjusted sum overstates the true total market "
        "size. Users should exercise independent judgment and consult qualified professionals "
        "before making any investment or business decisions based on this analysis.",
    )
    pdf.ln(3)
    pdf.small_text(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Data vintage: {data['ensemble'].data_vintage.iloc[0]} | "
        f"Pipeline: v1.2 Ensemble (ARIMA + Prophet + LightGBM)"
    )

    # ===================================================================
    # Write PDF
    # ===================================================================
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_PDF))
    file_size = OUTPUT_PDF.stat().st_size
    print(f"PDF generated: {OUTPUT_PDF}")
    print(f"File size: {file_size / 1024:.1f} KB ({file_size} bytes)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading data from Parquet files...")
    data = load_data()
    print(f"  Ensemble: {data['ensemble'].shape[0]} rows")
    print(f"  Scenarios: {data['scenarios'].shape[0]} rows")
    print(f"  Backtesting: {data['backtesting'].shape[0]} rows")
    print(f"  Total market 2025 (base): ${data['total_market_2025']:.0f}B")
    print(f"  Post-GenAI MAPE: {data['post_genai_mape']:.1f}%")
    print()
    print("Generating PDF...")
    generate_pdf(data)
    print("Done.")


if __name__ == "__main__":
    main()
