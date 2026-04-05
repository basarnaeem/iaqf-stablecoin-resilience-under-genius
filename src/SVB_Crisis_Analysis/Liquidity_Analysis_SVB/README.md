# Cryptocurrency Market Liquidity and Fragmentation During March 2023 USDC Depeg

**Author:** Yield Curve Surfers  
**Date:** February 2026  
**Notebook:** `Liquidity_Analysis_SVB.ipynb`

---

## Overview

This notebook analyzes market liquidity fragmentation across cryptocurrency exchanges during the March 2023 USDC depeg event triggered by the Silicon Valley Bank (SVB) collapse. It computes a comprehensive suite of microstructure metrics, compares their behavior across crisis regimes, and exports results for use in academic or competition papers.

**Exchanges covered:** Binance, Kraken  
**Quote currencies:** USD, USDC, USDT  
**Time period:** March 1–21, 2023  

> **Note on Coinbase:** Coinbase was excluded because its BTCUSDT pair averaged only ~843 BTC/day (vs. ~100,000 on Binance), with 18.1% of 1-min candles being LOCF-imputed. Including it would have noise-dominated all estimators and created a non-comparable exchange pair count. Binance and Kraken each contribute 5 clean pairs (3 BTC + 2 stablecoin).

---

## Prerequisites

### Environment
- Python 3.8+
- Google Colab (uses `google.colab.drive` for mounting)

### Libraries
```
pandas, numpy, matplotlib, seaborn, scipy, scikit-learn, pathlib
```

### Data
Cleaned 1-minute OHLCV CSV files must be present at:
```
/content/drive/MyDrive/Yield Curve Surfers/Data/
├── Binance/cleaned/*.csv
└── Kraken/cleaned/*.csv
```

Update `BASE_PATH` in the path configuration cell if your Drive structure differs.

#### Expected CSV filename format
Files are matched via regex: `_<PAIR>_1m_`. Example:
```
binance_BTCUSDC_1m_cleaned.csv
kraken_USDCUSD_1m_cleaned.csv
```

#### Supported timestamp column names
`timestamp`, `open_time_ms`, `start`, `time_period_start`, `timestamp_utc`, `open_time_utc`, `datetime`

---

## Notebook Structure

| Section | Description |
|---------|-------------|
| **1. Setup & Data Loading** | Mount Drive, import libraries, define paths, load all OHLCV data |
| **2. Transaction-Based Measures** | Number of transactions, dollar volume, weekend effect |
| **3. Price Impact Measures** | Amihud (2002) Illiquidity Ratio, Kyle's Lambda |
| **4. Spread Estimators** | Roll (1984), Corwin–Schultz (2012), Abdi–Ranaldo (2017) |
| **5. Advanced Illiquidity Index** | Kyle–Obizhaeva (2016) market-wide index |
| **6. Competition-Winning Metrics** | Flight-to-Safety Score, Cross-Exchange Arbitrage Gaps, Effective Spread, Price Efficiency Ratio, VPIN, Liquidity Resilience, MQI + SPQI |
| **7. Comprehensive Analysis** | `calculate_all_metrics` applied to every dataset → `all_metrics` dict |
| **8. Regime-Based Analysis** | Statistics by regime (pre-crisis, peak-crisis, recovery); crisis multipliers |
| **9. Competition Summary** | % change pre → peak for all metrics |
| **10. Visualizations** | Bar charts and time series with crisis regime shading |
| **11. Export Results** | Saves all outputs as CSV to `<CODE_PATH>/outputs/` |

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `parse_timestamp(df)` | Normalizes timestamps across all exchange schemas |
| `standardize_schema(df)` | Renames columns to a common OHLCV format |
| `load_one_csv(fp)` | Loads and filters a single CSV to the SVB window |
| `load_exchange_data(name, path)` | Loads all CSVs for one exchange into `all_data` |
| `compute_tx(df)` | Rolling transaction count and trade intensity |
| `compute_amihud_31(df)` | Amihud (2002) illiquidity ratio |
| `roll_spread(df)` | Roll (1984) covariance spread estimator |
| `corwin_schultz_spread(df)` | Corwin–Schultz (2012) HL spread estimator |
| `abdi_ranaldo_spread(df)` | Abdi–Ranaldo (2017) effective spread |
| `kyle_obizhaeva(df)` | Kyle–Obizhaeva (2016) illiquidity index |
| `calculate_vpin_adaptive(df)` | VPIN with per-pair adaptive bucket sizing |
| `price_efficiency_ratio(df)` | Kaufman Efficiency Ratio (60-min window) |
| `effective_spread(df)` | Quoted spread from high–low range |
| `liquidity_resilience(df)` | Recovery speed relative to baseline and shock |
| `zscore_normalize(s)` | Z-score normalization vs. pre-crisis baseline → [0, 1] |
| `efficiency_stress_norm(s)` | Absolute deviation of ER from baseline → [0, 1] |
| `compute_mqi(metrics_dict, filter_fn)` | Composite Market Quality Index (or SPQI) |

---

## Crisis Regimes

| Regime | Date Range |
|--------|-----------|
| `pre_crisis` | 2023-03-01 → 2023-03-09 |
| `peak_crisis` | 2023-03-10 → 2023-03-13 |
| `recovery` | 2023-03-14 → 2023-03-21 |

---

## MQI Weights

| Component | Weight |
|-----------|--------|
| Spread (CS) | 0.30 |
| Price Impact (Amihud) | 0.30 |
| Efficiency Stress | 0.20 |
| VPIN | 0.20 |

If VPIN data is insufficient for a given pair, the remaining three components are renormalized to sum to 1.0.

---

## Outputs

Running Section 11 saves the following to `<CODE_PATH>/outputs/`:

| File | Contents |
|------|---------|
| `regime_statistics.csv` | All metrics by pair and regime |
| `pre_vs_peak_comparison.csv` | Absolute values pre vs. peak |
| `percent_change_pre_vs_peak.csv` | % change for each metric |
| `crisis_multipliers.csv` | Peak/pre ratios for each metric |
| `<key>_mqi_timeseries.csv` | Per-pair MQI time series |
| `pair_metrics/<key>_full_metrics.csv` | Full per-minute metrics for every pair |

---

## Research Questions Addressed

1. How did liquidity differ by quote currency (USD / USDC / USDT) during the crisis?
2. What was the magnitude of liquidity deterioration (crisis multipliers)?
3. Did investors flee USDC for USDT — and when exactly?
4. How did markets fragment across Binance and Kraken?
5. How quickly did liquidity recover after regulatory intervention?
