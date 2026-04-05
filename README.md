# Reserve-ior Dogs: The Great Stablecoin Standoff
**IAQF Student Competition 2026 | Team: YieldCurveSurfers | UCLA Anderson MFE**

> *Thin Cushions and False Security: Evaluating Stablecoin Resilience under the GENIUS Act*

## Overview

This repository contains the full research codebase for our IAQF 2026 submission. We study how issuer balance-sheet fundamentals shape stablecoin peg stability, market liquidity, and cross-market stress transmission, using the March 2023 SVB collapse as an exogenous shock. Our core finding: **reserve quality alone is insufficient for peg credibility under run-like conditions — loss-absorbing capital plays a distinct and irreplaceable role.**

---

## Research Questions

- Why did USDC depeg during the SVB crisis while USDT — by conventional metrics the *riskier* instrument — held its peg?
- Does the GENIUS Act (enacted July 2025) actually address the structural vulnerabilities exposed by SVB?
- What role does issuer equity buffer play, independent of reserve quality?

---

## Methodology

### Top-Down: Market-Level Analysis (March 2023 Crisis Window)
- **Cross-Exchange Arbitrage Gaps** — 1-minute OHLCV across Binance.US & Kraken for BTC/USD, BTC/USDC, BTC/USDT, USDC/USD, USDT/USD
- **Market Quality Index (MQI)** — composite of Corwin-Schultz spread, Amihud illiquidity ratio, VPIN, and efficiency stress
- **Stablecoin Peg Quality Index (SPQI)** — analogous framework applied to USDC/USD and USDT/USD pairs
- **Rolling Kyle's Lambda** — price impact via Order Flow Imbalance (OFI) on Coinbase Level-2 order book data (CoinAPI)
- **TVP-VAR with GFEVD** — 8-variable system (USDT, USDC, BTC, ETH, S&P500, DXY, XAU, KBW) over 1,604 trading days (Jan 2020–Feb 2026) to quantify directional volatility spillovers; Total Spillover Index: **41.43%**

### Bottom-Up: Issuer-Level Reserve Analysis
- **Daily MTM Reserve Reconstruction** — interpolate Circle and Tether quarterly disclosures using duration-based mark-to-market (T-bills via 3M Treasury yield, Repo via SOFR, Corporate Bonds via Bloomberg BVAL AA curves, BTC/XAU via market prices)
- **Panel Regressions** — log peg deviations regressed on Equity Buffer Ratio, Liquidity Ratio, T-bill Share, VIX, and exchange FEs across calm, high-VIX, and SVB-window regimes
- **Basel III-Style Stress Tests** — three scenarios applied to reconstructed daily portfolios:
  - *Scenario A (Liquidity Run)*: 30% redemption shock with 2% fire-sale penalty
  - *Scenario B (Flash Crash)*: 50% BTC drop, 15% gold drop, 300bps rate shock
  - *Scenario C (Doomsday Contagion)*: 10% corporate bond default, 25% secured loan haircut, 50% "other investment" haircut

---

## Key Findings

| Finding | Result |
|---|---|
| USDC cross-exchange arb gap during SVB | ~900–1,000 bps vs. <100 bps for USDT |
| Total Spillover Index (TVP-VAR) | 41.43% — stablecoins are **net transmitters** |
| Circle stress test (Scenario A) | **FAILS** — equity cushion goes negative |
| Tether stress test (Scenario A) | Passes — equity buffer absorbs the shock |
| GENIUS Act compliance | Circle: compliant. Tether: non-compliant. Yet Tether is more resilient to the scenario that actually occurred. |

**Central thesis:** The GENIUS Act's reserve mandates address asset quality but not loss-absorbing capital. A mandatory minimum equity buffer ratio (analogous to Basel III Leverage Ratio) is the missing complement.

---

## Repository Structure
YieldCurveSurfers/
├── data/                   # Raw and processed data (see note below)
├── src/                    # Jupyter notebooks (Google Colab-based)
│   ├── 01_data_collection.ipynb
│   ├── 02_market_microstructure.ipynb   # Arb gaps, MQI, SPQI, Kyle's lambda
│   ├── 03_tvp_var_spillovers.ipynb      # TVP-VAR, GFEVD, spillover tables
│   ├── 04_reserve_reconstruction.ipynb  # MTM reserve portfolios
│   ├── 05_panel_regressions.ipynb       # Peg deviation regressions
│   └── 06_stress_tests.ipynb            # Basel III-style stress scenarios
├── results/                # Output figures and tables
└── README.md


> **Note on reproducibility:** Notebooks were developed in Google Colab. Data sources requiring Bloomberg Terminal access (DXY, KBW, XAU rates) and CoinAPI (Level-2 order book) are not redistributable. Exchange OHLCV data was collected via REST APIs (Binance.US, Kraken, Coinbase). See each notebook for data sourcing details.

---

## Data Sources

| Data | Source |
|---|---|
| 1-min OHLCV (BTC, ETH pairs) | Binance.US, Kraken, Coinbase REST APIs |
| Level-2 order book (BTC/USD, BTC/USDT) | CoinAPI (Coinbase) |
| Traditional market data (DXY, KBW, S&P, XAU) | Bloomberg Terminal |
| Stablecoin market cap / mint-burn proxy | CoinGecko |
| Circle reserve disclosures | Circle attestation reports (quarterly) |
| Tether reserve disclosures | Tether attestation reports (quarterly) |

---

## Dependencies
- numpy 
- pandas 
- scipy 
- statsmodels 
- matplotlib seaborn
requests jupyter

---

## Team

UCLA Anderson MFE — IAQF Student Competition 2026


