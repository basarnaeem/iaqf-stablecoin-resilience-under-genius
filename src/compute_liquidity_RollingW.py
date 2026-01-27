# src/refactored_compute_liquidity_stats.py
#
# What this does (no combined output files):
# - Reads 1) pre-SVB daily volume CSV (e.g., data/raw/volumes/coinbase_btc_usdc_pre_svb.csv)
# - Reads 2) SVB-period 1-min OHLCV CSV (e.g., data/raw/coinbase/btc/BTC-USDC_ONE_MINUTE.csv)
# - Aggregates BOTH to DAILY volume
# - Builds an "adaptive 60D baseline":
#     * expanding window until you have >=60 daily obs
#     * rolling 60D thereafter
# - For the IAQF window (Mar 1–Mar 21), plots:
#     (top) daily volume + shaded (median ± 1σ) baseline band + SVB/Bankruptcy/depeg annotations
#     (bottom) Z-score bars using mean/std baseline (with regime coloring)
#
# Output:
# - PNG chart saved into: data/processed/liquidity/<pair>_stress_dashboard.png
#
# Run from repo root:
#   python src/refactored_compute_liquidity_stats.py

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# =========================
# CONFIG & PATHS (EDIT THESE)
# =========================
PAIR_NAME = "coinbase_btc_usdc"

# Your files (based on your screenshots)
BASELINE_PATH = "data/raw/volumes/coinbase_btc_usdc_pre_svb.csv"
SVB_PATH      = "data/raw/coinbase/btc/BTC-USDC_ONE_MINUTE.csv"

OUT_DIR = "data/processed/liquidity"
os.makedirs(OUT_DIR, exist_ok=True)

# IAQF window
SVB_WINDOW_START = "2023-03-01"
SVB_WINDOW_END   = "2023-03-21"

# Rolling window length (conceptual)
ROLL_DAYS = 60

# Event annotations requested
SVB_FAILURE_DATE      = "2023-03-10"  # SVB placed into FDIC receivership (often used as “failure” marker)
SVB_BANKRUPTCY_DATE   = "2023-03-17"  # requested marker
# USDC depeg highlight window (common window around Mar 10–13). Adjust if you want.
USDC_DEPEG_START      = "2023-03-10"
USDC_DEPEG_END        = "2023-03-13"

# =========================
# LOADERS
# =========================
def load_baseline_daily(path: str) -> pd.DataFrame:
    """
    Expected baseline CSV format (your screenshot):
      timestamp, pair, close, volume
      2023-01-01 00:00:00, BTC/USDC, ..., 10.44...
    Already 1-min bars? Actually looks minute-level, but we aggregate to daily anyway.
    """
    df = pd.read_csv(path)
    if "timestamp" not in df.columns or "volume" not in df.columns:
        raise ValueError(f"Baseline file missing required columns. Found: {list(df.columns)}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["timestamp", "volume"])

    daily = (
        df.assign(date=df["timestamp"].dt.floor("D"))
          .groupby("date", as_index=False)["volume"].sum()
          .sort_values("date")
    )
    return daily

def load_svb_minute_to_daily(path: str) -> pd.DataFrame:
    """
    Expected SVB CSV format (your screenshot):
      start, low, high, open, close, volume, product_id, timestamp_utc
    We'll parse timestamp_utc (best), else derive from start (seconds).
    """
    df = pd.read_csv(path)

    if "volume" not in df.columns:
        raise ValueError(f"SVB file missing volume column. Found: {list(df.columns)}")

    if "timestamp_utc" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    elif "start" in df.columns:
        df["timestamp"] = pd.to_datetime(df["start"], unit="s", utc=True, errors="coerce")
    else:
        raise ValueError("SVB file needs either 'timestamp_utc' or 'start' column for timestamps.")

    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["timestamp", "volume"])

    daily = (
        df.assign(date=df["timestamp"].dt.floor("D"))
          .groupby("date", as_index=False)["volume"].sum()
          .sort_values("date")
    )
    return daily

# =========================
# BASELINE (ADAPTIVE) CONSTRUCTION
# =========================
def add_adaptive_baseline(daily_df: pd.DataFrame, roll_days: int) -> pd.DataFrame:
    """
    Adaptive baseline:
      - expanding window until >= roll_days available
      - rolling window thereafter

    Computes:
      roll_mean, roll_std (ddof=0), roll_median,
      band_low/high = median ± std
      z_score = (volume - roll_mean) / roll_std
    """
    df = daily_df.sort_values("date").copy()
    vols = df["volume"].to_numpy(dtype=float)

    roll_mean = np.empty(len(vols))
    roll_std = np.empty(len(vols))
    roll_median = np.empty(len(vols))

    for i in range(len(vols)):
        if i + 1 < roll_days:
            hist = vols[: i + 1]                 # expanding
        else:
            hist = vols[i + 1 - roll_days : i + 1]  # rolling

        roll_mean[i] = float(np.mean(hist))
        roll_std[i] = float(np.std(hist, ddof=0))
        roll_median[i] = float(np.median(hist))

    df["roll_mean"] = roll_mean
    df["roll_std"] = roll_std
    df["roll_median"] = roll_median

    # Avoid divide-by-zero
    df["z_score"] = (df["volume"] - df["roll_mean"]) / df["roll_std"].replace(0.0, np.nan)

    df["band_low"] = df["roll_median"] - df["roll_std"]
    df["band_high"] = df["roll_median"] + df["roll_std"]

    return df

# =========================
# PLOTTING
# =========================
def plot_stress_dashboard(win: pd.DataFrame, out_png: str):
    """
    Two-panel plot:
      Top: daily volume + (median ± 1σ) shaded band + lines for median±σ + markers for events
      Bottom: z-score bars with regime coloring + thresholds
    """
    # Ensure chronological
    win = win.sort_values("date").copy()

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 9), sharex=True,
        gridspec_kw={"height_ratios": [1.6, 1.0]}
    )

    # --- TOP: Volume + band ---
    ax1.plot(win["date"], win["volume"], marker="o", linewidth=2, label="BTC/USDC Volume")

    # shaded median ± 1σ band
    ax1.fill_between(
        win["date"], win["band_low"], win["band_high"],
        alpha=0.15, label="Normal Range (median ± 1σ)"
    )

    # optional band lines (helps readability)
    ax1.plot(win["date"], win["roll_median"], linestyle="--", linewidth=2, label=f"Rolling median ({ROLL_DAYS}D)")
    ax1.plot(win["date"], win["band_high"], linestyle=":", linewidth=2, label="Median + 1σ")
    ax1.plot(win["date"], win["band_low"], linestyle=":", linewidth=2, label="Median - 1σ")

    ax1.set_title("BTC/USDC Liquidity Stress Profile (March 2023)")
    ax1.set_ylabel("Daily Aggregated Volume")
    ax1.legend(loc="upper right")

    # --- Event markers (vertical) + depeg highlight (span) ---
    svb_fail = pd.to_datetime(SVB_FAILURE_DATE, utc=True)
    svb_bk   = pd.to_datetime(SVB_BANKRUPTCY_DATE, utc=True)
    depeg_s  = pd.to_datetime(USDC_DEPEG_START, utc=True)
    depeg_e  = pd.to_datetime(USDC_DEPEG_END, utc=True)

    ax1.axvline(svb_fail, linestyle="--", linewidth=2)
    ax1.text(svb_fail, ax1.get_ylim()[1]*0.95, "SVB Failure", ha="left", va="top", fontweight="bold")

    ax1.axvline(svb_bk, linestyle="--", linewidth=2)
    ax1.text(svb_bk, ax1.get_ylim()[1]*0.88, "SVB Bankruptcy (3/17)", ha="left", va="top", fontweight="bold")

    # highlight depeg window
    ax1.axvspan(depeg_s, depeg_e, alpha=0.12)
    ax1.text(depeg_s, ax1.get_ylim()[1]*0.80, "USDC De-peg window", ha="left", va="top", fontweight="bold")

    # --- BOTTOM: Z-score bars ---
    # Regimes:
    #   Normal: z <= 1
    #   Elevated: 1 < z <= 2
    #   Crisis: z > 2
    z = win["z_score"].to_numpy()
    bar_colors = []
    for zi in z:
        if np.isnan(zi):
            bar_colors.append("gray")
        elif zi > 2:
            bar_colors.append("#d62728")  # red
        elif zi > 1:
            bar_colors.append("#ff7f0e")  # orange
        else:
            bar_colors.append("#2ca02c")  # green

    ax2.bar(win["date"], win["z_score"], color=bar_colors, alpha=0.85)
    ax2.axhline(0, linewidth=1)
    ax2.axhline(1, linestyle=":", linewidth=1)
    ax2.axhline(2, linestyle=":", linewidth=1)

    ax2.set_ylabel("Volume Z-Score\n(vs rolling mean/std)")
    ax2.set_xlabel("Date (UTC)")

    legend_patches = [
        Patch(facecolor="#2ca02c", label="Normal (Z ≤ 1)"),
        Patch(facecolor="#ff7f0e", label="Elevated (1 < Z ≤ 2)"),
        Patch(facecolor="#d62728", label="Crisis (Z > 2)"),
        Patch(facecolor="gray", label="Undefined (std=0 / missing)"),
    ]
    ax2.legend(handles=legend_patches, loc="upper left")

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close(fig)

# =========================
# MAIN
# =========================
def main():
    # Load both sources -> daily
    baseline_daily = load_baseline_daily(BASELINE_PATH)
    svb_daily = load_svb_minute_to_daily(SVB_PATH)

    # Combine daily history (no output file; just for baseline calculation)
    full_daily = (
        pd.concat([baseline_daily, svb_daily], ignore_index=True)
          .drop_duplicates(subset=["date"])
          .sort_values("date")
          .reset_index(drop=True)
    )

    print(f"[DEBUG] daily rows={len(full_daily)} | range={full_daily['date'].min()} -> {full_daily['date'].max()}")

    # Add baseline + zscore (adaptive so it won't crash if <60 days)
    full = add_adaptive_baseline(full_daily, ROLL_DAYS)

    # Restrict to IAQF window (Mar 1–Mar 21)
    win = full[
        (full["date"] >= pd.to_datetime(SVB_WINDOW_START, utc=True)) &
        (full["date"] <= pd.to_datetime(SVB_WINDOW_END, utc=True))
    ].copy()

    # Basic sanity
    print(f"[DEBUG] window rows={len(win)} expected=21")
    if len(win) == 0:
        raise RuntimeError("No rows in IAQF window. Check your input files and date parsing.")

    out_png = os.path.join(OUT_DIR, f"{PAIR_NAME}_stress_dashboard.png")
    plot_stress_dashboard(win, out_png)
    print(f"✅ Saved: {out_png}")

if __name__ == "__main__":
    main()


