# Volatility Spillover Analysis — Stablecoins & Traditional Markets

**Notebook:** `Volatility_Spillover.ipynb`

## Overview

This notebook analyses volatility spillover effects between stablecoins (USDT, USDC) and a set of traditional and crypto market factors. The methodology follows the **TVP-VAR Dynamic Connectedness Framework** (Koop & Korobilis, 2014; Antonakakis & Gabauer, 2017), using Generalized Forecast Error Variance Decomposition (GFEVD) to quantify how volatility shocks transmit across markets.

**Assets covered:**
- Stablecoins: USDT/USD, USDC/USD
- Crypto: Bitcoin (BTC), Ethereum (ETH)
- Traditional: S&P 500, DXY, Gold (XAU), KBW Bank Index, VIX

---

## Requirements

### Python Version
Python 3.9+

### Dependencies
```bash
pip install pandas numpy matplotlib statsmodels scipy openpyxl
```

| Package | Purpose |
|---|---|
| pandas | Data loading and manipulation |
| numpy | Numerical computation |
| matplotlib | Plotting |
| statsmodels | ADF, Ljung-Box, Jarque-Bera, OLS, VAR |
| scipy | Pearson correlation, statistical distributions |
| openpyxl | Reading .xlsx files |

---

## Data Requirements

Place the following two files in `data/` (already present in repo root `data/`):

### 1. `data/traditional_market_data.xlsx`
Daily OHLC data for traditional market instruments (Bloomberg-sourced — not committed, see `data/README.md`).

| Column | Description |
|---|---|
| Dates | Date (renamed to Date) |
| Open_DXY, Last_DXY, High_DXY, Low_DXY | US Dollar Index |
| Open_XAU, Last_XAU, High_XAU, Low_XAU | Gold |
| Open_VIX, High_VIX, Low_VIX | VIX volatility index |
| Open_SP, Last_SP, High_SP, Low_SP, Volume_SP | S&P 500 |
| Open_KBW, Last_KBW, High_KBW, Low_KBW, Volume_KBW | KBW Bank Index |

### 2. `data/crypto_ohlcv_data.xlsx`
Daily OHLCV data for crypto assets.

| Column | Description |
|---|---|
| Date | Date |
| USDT_USD_High, USDT_USD_Low | Tether OHLC |
| USDC_USD_High, USDC_USD_Low | USD Coin OHLC |
| BTC_USD_High, BTC_USD_Low | Bitcoin OHLC |
| ETH_USD_High, ETH_USD_Low | Ethereum OHLC |

> **Note:** Crypto data sourced from Binance.US → Coinbase → Kraken → CoinDesk (priority order). Both datasets are merged on Date with an outer join; weekends are dropped to align with traditional market trading days.

---

## Notebook Structure

| Section | Description |
|---|---|
| **1. Data Loading & Preprocessing** | Load both files, merge on Date, drop weekends, subset to High/Low columns |
| **2. Volatility Computation** | Parkinson (1980) extreme-value estimator for all series; VIX used as level variable |
| **3. Descriptive Statistics (Table I)** | N, mean, SD; ADF (stationarity), Jarque-Bera (normality), Ljung-Box Q(10) (autocorrelation) |
| **4. Data Quality Check** | Flag stablecoin observations with Parkinson volatility > 0.15 |
| **5. Correlation & Multicollinearity** | Pearson table with p-values; full correlation matrix; VIF; condition number |
| **6. OLS Regression (Table I)** | USDT and USDC volatility on all factors; Newey-West HAC SEs (maxlags=10); year FEs; Breusch-Pagan test |
| **7. Static Spillover Table (Table II)** | VAR with BIC lag selection; GFEVD at H=10; FROM/TO/NET table; Total Spillover Index |
| **8. TVP-VAR Dynamic Spillovers (Table II)** | Forgetting-factor Kalman filter (λ=0.99, κ=0.96); time-averaged GFEVD; run at p=1 and p=2 |

---

## Volatility Estimator

Parkinson (1980) extreme-value estimator:

$$V_t = \sqrt{\frac{(\ln P_{h,t} - \ln P_{l,t})^2}{4 \ln 2}}$$

where $P_{h,t}$ and $P_{l,t}$ are the daily high and low prices. VIX is used as a level variable (midpoint of High/Low) rather than a derived volatility.

---

## Key Parameters

| Parameter | Value | Description |
|---|---|---|
| H | 10 | Forecast horizon for GFEVD |
| λ (lam) | 0.99 | TVP-VAR coefficient forgetting factor |
| κ (kap) | 0.96 | TVP-VAR variance forgetting factor |
| init_obs | max(10% of T, N×p+5) | Kalman filter initialisation window |
| maxlags | 10 | Max lags for BIC selection in VAR |
| cov_type | HAC (maxlags=10) | OLS standard error correction |

---

## Outputs

| Output | Description |
|---|---|
| `stablecoin_volatility.png` | Time series of USDT and USDC Parkinson volatility |
| Console tables | Descriptive stats, correlations, VIF, regression results, spillover tables |

---

## References

- Parkinson, M. (1980). The Extreme Value Method for Estimating the Variance of the Rate of Return. *Journal of Business*, 53(1), 61–65.
- Pesaran, H.H., & Shin, Y. (1998). Generalized Impulse Response Analysis in Linear Multivariate Models. *Economics Letters*, 58(1), 17–29.
- Diebold, F.X., & Yilmaz, K. (2012). Better to Give than to Receive. *International Journal of Forecasting*, 28(1), 57–66.
- Koop, G., & Korobilis, D. (2014). A New Index of Financial Conditions. *European Economic Review*, 71, 101–116.
- Antonakakis, N., & Gabauer, D. (2017). Refined Measures of Dynamic Connectedness based on TVP-VAR. *MPRA Paper No. 78282*.
