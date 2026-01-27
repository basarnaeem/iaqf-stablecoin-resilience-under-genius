import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ============================================================
# PATHS (match your repo)
# ============================================================
BASELINE_PATH = "data/raw/volumes/coinbase_btc_usdc_pre_svb.csv"
SVB_PATH      = "data/raw/coinbase/btc/BTC-USDC_ONE_MINUTE.csv"

OUT_DIR  = "data/processed/liquidity"
PAIR_NAME = "coinbase_btc_usdc"
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# IAQF WINDOW
# ============================================================
SVB_WINDOW_START = "2023-03-01"
SVB_WINDOW_END   = "2023-03-21"   # inclusive

# ============================================================
# EVENTS (for annotation)
# ============================================================
SVB_FAILURE_DATE     = "2023-03-10"
SVB_BANKRUPTCY_DATE  = "2023-03-17"

# USDC de-peg highlight window (adjust if you want)
USDC_DEPEG_START = "2023-03-10"
USDC_DEPEG_END   = "2023-03-13"

# Z-score regime thresholds
Z_ELEVATED = 1.0
Z_CRISIS   = 2.0


# ============================================================
# LOADERS
# ============================================================
def load_volume_file(path: str) -> pd.DataFrame:
    """
    Loads either:
      - pre_svb csv with columns: timestamp,pair,close,volume
      - minute csv with columns: start,low,high,open,close,volume,product_id,timestamp_utc
    Returns df with: timestamp (UTC tz-aware), volume (float)
    """
    df = pd.read_csv(path)

    if "timestamp_utc" in df.columns:
        ts = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    elif "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    elif "start" in df.columns:
        ts = pd.to_datetime(df["start"], unit="s", utc=True, errors="coerce")
    else:
        raise ValueError(f"No timestamp column found in {path}. Columns={list(df.columns)}")

    vol = pd.to_numeric(df["volume"], errors="coerce")

    out = pd.DataFrame({"timestamp": ts, "volume": vol}).dropna(subset=["timestamp", "volume"])
    return out


def to_daily_volume(df: pd.DataFrame) -> pd.DataFrame:
    """
    Minute-level -> daily aggregated volume (sum).
    Returns columns: date (UTC), volume
    """
    d = df.copy()
    d["date"] = d["timestamp"].dt.floor("D")
    daily = d.groupby("date", as_index=False)["volume"].sum()
    return daily.sort_values("date")


# ============================================================
# FIXED BASELINE (computed ONCE from pre-SVB)
# ============================================================
def compute_fixed_baseline_stats(baseline_daily: pd.DataFrame):
    med = float(baseline_daily["volume"].median())
    std = float(baseline_daily["volume"].std(ddof=1))

    # guard against weird std
    if not np.isfinite(std) or std == 0:
        std = np.nan

    return med, std


def attach_fixed_baseline(win_daily: pd.DataFrame, med: float, std: float) -> pd.DataFrame:
    out = win_daily.copy()
    out["base_median"] = med
    out["base_std"] = std
    out["base_upper"] = med + std
    out["base_lower"] = med - std
    out["z_score"] = (out["volume"] - med) / std
    return out


# ============================================================
# PLOTTING
# ============================================================
def z_color(z):
    if not np.isfinite(z):
        return "gray"
    if z > Z_CRISIS:
        return "#d62728"  # red
    if z > Z_ELEVATED:
        return "#ff7f0e"  # orange
    return "#2ca02c"      # green


def plot_dashboard(df_win: pd.DataFrame, out_png: str, title: str):
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 9), sharex=True,
        gridspec_kw={"height_ratios": [1.6, 1.0]}
    )

    # --- TOP: volume line ---
    ax1.plot(df_win["date"], df_win["volume"], marker="o", linewidth=2, label="BTC/USDC Volume")

    # Fixed baseline band (median ± 1σ)
    ax1.fill_between(
        df_win["date"],
        df_win["base_lower"],
        df_win["base_upper"],
        alpha=0.15,
        label="Normal Range (median ± 1σ) [fixed baseline]"
    )

    # Baseline median + bounds as lines
    ax1.plot(df_win["date"], df_win["base_median"], linestyle="--", linewidth=2, label="Fixed median (baseline)")
    ax1.plot(df_win["date"], df_win["base_upper"], linestyle=":", linewidth=2, label="Median + 1σ")
    ax1.plot(df_win["date"], df_win["base_lower"], linestyle=":", linewidth=2, label="Median - 1σ")

    # Event lines
    svb_fail = pd.to_datetime(SVB_FAILURE_DATE, utc=True)
    svb_bk   = pd.to_datetime(SVB_BANKRUPTCY_DATE, utc=True)

    ax1.axvline(svb_fail, linestyle="--", linewidth=2)
    ax1.text(svb_fail, ax1.get_ylim()[1]*0.95, "SVB Failure (3/10)", va="top", fontweight="bold")

    ax1.axvline(svb_bk, linestyle="--", linewidth=2)
    ax1.text(svb_bk, ax1.get_ylim()[1]*0.90, "SVB Bankruptcy (3/17)", va="top", fontweight="bold")

    # USDC de-peg shaded window
    dep_s = pd.to_datetime(USDC_DEPEG_START, utc=True)
    dep_e = pd.to_datetime(USDC_DEPEG_END, utc=True)
    ax1.axvspan(dep_s, dep_e, alpha=0.10)
    ax1.text(dep_s, ax1.get_ylim()[1]*0.85, "USDC De-peg window", va="top", fontweight="bold")

    ax1.set_title(title)
    ax1.set_ylabel("Daily Aggregated Volume")
    ax1.legend(loc="upper right")

    # --- BOTTOM: z-score bars (vs FIXED baseline) ---
    colors = [z_color(z) for z in df_win["z_score"]]
    ax2.bar(df_win["date"], df_win["z_score"], color=colors, alpha=0.85)

    ax2.axhline(0, linewidth=1)
    ax2.axhline(Z_ELEVATED, linestyle=":", linewidth=1)
    ax2.axhline(Z_CRISIS, linestyle=":", linewidth=1)

    ax2.set_ylabel("Volume Z-Score\n(vs fixed baseline)")
    ax2.set_xlabel("Date (UTC)")

    handles = [
        Patch(facecolor="#2ca02c", label=f"Normal (Z ≤ {Z_ELEVATED})"),
        Patch(facecolor="#ff7f0e", label=f"Elevated ({Z_ELEVATED} < Z ≤ {Z_CRISIS})"),
        Patch(facecolor="#d62728", label=f"Crisis (Z > {Z_CRISIS})"),
        Patch(facecolor="gray", label="Undefined (std=0 / missing)")
    ]
    ax2.legend(handles=handles, loc="upper left")

    plt.xticks(rotation=35)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close(fig)


# ============================================================
# MAIN
# ============================================================
def main():
    # Load + aggregate baseline (pre-SVB)
    base_raw = load_volume_file(BASELINE_PATH)
    base_daily = to_daily_volume(base_raw)

    # Compute fixed baseline stats (ONCE)
    base_med, base_std = compute_fixed_baseline_stats(base_daily)

    # Load + aggregate SVB-period minute data -> daily
    svb_raw = load_volume_file(SVB_PATH)
    svb_daily = to_daily_volume(svb_raw)

    # Filter to IAQF March 1–21 window
    win_start = pd.to_datetime(SVB_WINDOW_START, utc=True)
    win_end   = pd.to_datetime(SVB_WINDOW_END, utc=True)

    df_win = svb_daily[(svb_daily["date"] >= win_start) & (svb_daily["date"] <= win_end)].copy()

    # Attach fixed baseline + z-score
    df_win = attach_fixed_baseline(df_win, base_med, base_std)

    # Plot
    title = "BTC/USDC Liquidity Stress Profile (March 2023) — FIXED baseline (pre-SVB)"
    out_png = os.path.join(OUT_DIR, f"{PAIR_NAME}_stress_dashboard_fixed.png")
    plot_dashboard(df_win, out_png, title)

    print(f"✅ Saved: {out_png}")
    print(f"[INFO] baseline days={len(base_daily)}  window days={len(df_win)}")
    print(f"[INFO] fixed baseline median={base_med:.4f}  std={base_std:.4f}")

if __name__ == "__main__":
    main()




