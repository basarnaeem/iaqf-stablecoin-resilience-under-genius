# Reserve-ior Dogs: The Great Stablecoin Standoff
**IAQF Student Competition 2026 | Team: YieldCurveSurfers | UCLA Anderson MFE**

> *Thin Cushions and False Security: Evaluating Stablecoin Resilience under the GENIUS Act*

## Overview

This repository contains the full research codebase for our IAQF 2026 submission. We study how issuer balance-sheet fundamentals shape stablecoin peg stability, market liquidity, and cross-market stress transmission, using the March 2023 SVB collapse as an exogenous shock.

**Core finding:** Reserve quality alone is insufficient for peg credibility under run-like conditions — loss-absorbing capital plays a distinct and irreplaceable role. Circle satisfied every standard the GENIUS Act mandates yet failed the one stress scenario that actually occurred. Tether — non-compliant by conventional metrics — passed. The difference was equity buffer, not reserve quality.

---

## Research Questions

- Why did USDC depeg during the SVB crisis while USDT — by conventional metrics the *riskier* instrument — held its peg?
- Does the GENIUS Act (enacted July 2025) actually address the structural vulnerabilities exposed by SVB?
- What role does issuer equity buffer play, independent of reserve quality?

---

## Methodology

### Top-Down: Market-Level Analysis (March 2023 Crisis Window)
- **Cross-Exchange Arbitrage Gaps** — 1-min OHLCV across Binance.US, Kraken, Coinbase, Crypto.com for BTC/USD, BTC/USDC, BTC/USDT, USDC/USD, USDT/USD
- **Market Quality Index (MQI)** — composite of Corwin-Schultz spread, Amihud illiquidity ratio, VPIN, and efficiency stress
- **Stablecoin Peg Quality Index (SPQI)** — MQI framework applied to USDC/USD and USDT/USD pairs
- **Rolling Kyle's Lambda** — price impact via Order Flow Imbalance (OFI) on Coinbase Level-2 order book data; 1,440-min rolling OLS window
- **TVP-VAR with GFEVD** — 8-variable system (USDT, USDC, BTC, ETH, S&P500, DXY, XAU, KBW) over 1,604 trading days (Jan 2020–Feb 2026); Total Spillover Index: **41.43%**

### Bottom-Up: Issuer-Level Reserve Analysis
- **Daily MTM Reserve Reconstruction** — interpolate Circle and Tether quarterly disclosures using duration-based mark-to-market (T-bills via 3M Treasury yield, Repo via SOFR, Corporate Bonds via Bloomberg BVAL AA curves, BTC/XAU via market prices)
- **Panel Regressions** — log peg deviations on Equity Buffer Ratio, Liquidity Ratio, T-bill Share, VIX, exchange FEs across calm, high-VIX, and SVB-window regimes (Newey-West HAC)
- **Basel III-Style Stress Tests** — three scenarios on reconstructed daily portfolios:
  - *Scenario A (Liquidity Run)*: 30% redemption shock with 2% fire-sale penalty
  - *Scenario B (Flash Crash)*: 50% BTC drop, 15% gold drop, 300bps rate shock
  - *Scenario C (Doomsday Contagion)*: 10% corporate bond default, 25% secured loan haircut, 50% "other investments" haircut

---

## Key Findings

| Finding | Result |
|---|---|
| USDC cross-exchange arb gap during SVB | ~900–1,000 bps vs. <100 bps for USDT |
| Total Spillover Index (TVP-VAR) | 41.43% — stablecoins are **net transmitters** of volatility |
| Circle stress test — Scenario A (Liquidity Run) | **FAILS** — equity cushion goes negative |
| Tether stress test — Scenario A (Liquidity Run) | **Passes** — equity buffer absorbs the shock |
| GENIUS Act compliance | Circle: compliant. Tether: non-compliant. Tether is more resilient to the scenario that actually occurred. |

**Central thesis:** The GENIUS Act's reserve mandates address asset quality but not loss-absorbing capital. A mandatory minimum equity buffer ratio — analogous to the Basel III Leverage Ratio — is the missing complement.

---

## Submission Paper

📄 **[YieldCurveSurfers — IAQF 2026 Submission (PDF)](./YieldCurveSurfers_IAQF2026_StablecoinResilience_GENIUS_Act.pdf)**

---

## Repository Structure

```
YieldCurveSurfers/
│
├── data/
│   ├── README.md                            # Data inventory, sources, access notes
│   ├── Binance/                             # Raw 1-min OHLCV: BTC/USD, BTC/USDC, BTC/USDT,
│   │                                        # USDC/USD, USDT/USD — Binance.US, Mar 1–21 2023
│   ├── Coinbase/                            # Raw 1-min OHLCV: BTC/USD, BTC/USDC, BTC/USDT,
│   │                                        # USDC/EUR, USDT/EUR, USDT/USDC — Mar 1–21 2023
│   ├── Crypto.com/                          # Raw 1-min OHLCV: BTC/USD, BTC/USDC, BTC/USDT,
│   │                                        # USDT/USDC — Mar 1–21 2023
│   ├── Cleaned/                             # Gap-filled CSVs across all exchanges
│   │                                        # (LOCF ≤5 min, ETS 6–30 min, drop >30 min)
│   ├── Bloomberg data/                      # ⚠️ NOT COMMITTED — proprietary
│   │                                        # DXY, KBW, S&P500, XAU, VIX, SOFR, BVAL AA yields
│   ├── Currency Exchange Rates/             # EUR/USD 1-min data (raw + cleaned)
│   ├── Reserves/
│   │   └── Reserves information USDC_values.xlsx  # Circle quarterly reserve disclosures
│   ├── circleassets.csv                     # Circle reserve asset inputs for MTM reconstruction
│   ├── tetherassets.csv                     # Tether reserve asset inputs for MTM reconstruction
│   ├── Reserves_Analysis3.xlsx             # Reserve composition analysis workbook
│   ├── T-bill holdings.xlsx                 # Tether T-bill holdings by quarter
│   ├── Treasury holders.xlsx                # Treasury holder breakdown for MTM
│   ├── USDCReg.xlsx                         # USDC peg deviation regression inputs
│   ├── USDTReg.xlsx                         # USDT peg deviation regression inputs
│   ├── crypto_ohlcv_data.xlsx               # Daily OHLCV for TVP-VAR (Jan 2020–Feb 2026)
│   └── traditional_market_data.xlsx         # ⚠️ Bloomberg-sourced — not redistributable
│
├── src/
│   │
│   ├── OHLCV_Collector/
│   │   └── OHLCV_Multi_Source_Collector.ipynb   # Pulls 1-min OHLCV from Binance.US, Kraken,
│   │                                             # Coinbase, Crypto.com REST APIs across all
│   │                                             # BTC and stablecoin pairs
│   │
│   ├── Stablecoin_OHLCV_Diagnostic/
│   │   └── Stablecoin_OHLCV_Quality_Audit.ipynb # Data quality checks: gap detection,
│   │                                             # timestamp alignment, coverage statistics
│   │                                             # across exchanges and pairs; justifies
│   │                                             # Coinbase exclusion from MQI analysis
│   │
│   ├── SVB_Crisis_Analysis/
│   │   ├── Cleaning_data_SVB/
│   │   │   ├── README.md                         # Gap-fill methodology and usage
│   │   │   ├── clean_binance.py                  # Gap-fill and clean Binance 1-min data
│   │   │   ├── clean_coinbase.py                 # Gap-fill and clean Coinbase 1-min data
│   │   │   ├── clean_crypto_com.py               # Gap-fill and clean Crypto.com 1-min data
│   │   │   └── clean_kraken.py                   # Gap-fill and clean Kraken 1-min data
│   │   │
│   │   ├── Liquidity_Analysis_SVB/
│   │   │   ├── README.md                         # Full methodology, function reference,
│   │   │   │                                     # regime definitions, MQI weights, outputs
│   │   │   ├── Liquidity_Analysis_SVB.ipynb      # Cross-exchange arbitrage gaps (Eq. 1);
│   │   │   │                                     # MQI construction (Corwin-Schultz, Amihud,
│   │   │   │                                     # VPIN, efficiency stress); SPQI for
│   │   │   │                                     # USDC/USD and USDT/USD — Fig. 1 & 2
│   │   │   └── Kyles_Lambda.ipynb                # Rolling Kyle's λ via OFI on Coinbase L2;
│   │   │                                         # 1,440-min rolling OLS; BTC/USD vs
│   │   │                                         # BTC/USDT substitution dynamics — Fig. 3
│   │   │
│   │   └── Basis_Analysis_SVB.ipynb              # Basis spread analysis across quote currencies
│   │                                             # during SVB window; USDC vs USDT cross-venue
│   │                                             # pricing divergence
│   │
│   ├── Volatility_Spillover/
│   │   ├── README.md                             # Full methodology: Parkinson estimator,
│   │   │                                         # TVP-VAR parameters, data schema, outputs
│   │   └── Volatility_Spillover.ipynb            # Stablecoin volatility OLS (Table I);
│   │                                             # 8-variable TVP-VAR (λ=0.99, κ=0.96);
│   │                                             # GFEVD at H=10; static spillover table
│   │                                             # (Table II); TSI = 41.43%
│   │
│   └── Code+DataRegression and BalanceSheet Analysis/
│       ├── Latest_Regressions.ipynb              # Panel regressions of log peg deviations
│       │                                         # (Eq. 11); full sample, calm, high-VIX,
│       │                                         # SVB-window regimes; Newey-West HAC SEs;
│       │                                         # exchange FEs — Tables III & IV
│       └── Reserve_StressTesting.ipynb           # Duration-based MTM reconstruction of Circle
│                                                 # and Tether daily reserve portfolios;
│                                                 # equity buffer, liquidity ratio, T-bill share;
│                                                 # Basel III-style stress scenarios A/B/C —
│                                                 # Fig. 4, 5, 6, 7
│
├── results/                                 # Output figures (see below)
├── .gitignore
├── requirements.txt
├── YieldCurveSurfers_IAQF2026_StablecoinResilience_GENIUS_Act.pdf
└── README.md
```

---

## Results / Figures

Key figures saved to `results/`:

| File | Paper Figure | Description |
|---|---|---|
| `fig1_arb_gaps.png` | Fig. 1 | Cross-exchange arbitrage gaps — BTC pairs + USDC/USD vs USDT/USD |
| `fig2_mqi_spqi.png` | Fig. 2 | MQI and SPQI composite scores across exchanges |
| `fig3_kyle_lambda.png` | Fig. 3 | Rolling Kyle's λ — BTC/USD vs BTC/USDT |
| `fig4_reserve_equity_evolution.png` | Fig. 4 | USDC/USDT total assets, tokens issued, equity % over time |
| `fig5_reserve_composition.png` | Fig. 5 | Tether vs Circle reserve allocation (stacked bars) |
| `fig6_tether_stress_test.png` | Fig. 6 | Tether equity cushion under 3 stress scenarios |
| `fig7_circle_stress_test.png` | Fig. 7 | Circle equity cushion under 3 stress scenarios |

---

## Data Sources

| Data | Source | Access |
|---|---|---|
| 1-min OHLCV — Binance.US, Coinbase, Crypto.com | Exchange REST APIs | Free / public |
| Level-2 order book — Coinbase BTC/USD, BTC/USDT | CoinAPI | Paid |
| S&P 500, DXY, XAU, KBW, VIX, SOFR, BVAL AA yields | Bloomberg Terminal | Institutional |
| USDC / USDT market cap | CoinGecko API | Free |
| Circle reserve disclosures (Q3 2022–Q4 2025) | [circle.com/transparency](https://www.circle.com/transparency) | Public |
| Tether reserve disclosures (Q3 2022–Q4 2025) | [tether.to/transparency](https://tether.to/en/transparency) | Public |

> **Reproducibility:** Notebooks were developed in Google Colab. Bloomberg and CoinAPI data are not redistributable and excluded from this repository. Exchange OHLCV data is committed in `data/`. Reserve disclosures were manually compiled from public attestation reports.

---

## Dependencies

See `requirements.txt`. Core packages:
```
numpy, pandas, scipy, statsmodels, matplotlib, seaborn, openpyxl, requests, jupyter
```

---

## Team

UCLA Anderson MFE — IAQF Student Competition 2026
