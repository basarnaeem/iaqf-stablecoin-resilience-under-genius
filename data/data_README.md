# Data

This folder contains all datasets used in the analysis. Bloomberg data and CoinAPI order book data are **not committed** due to licensing restrictions.

---

## Folder Structure

```
data/
├── Binance/                          # Raw 1-min OHLCV, Binance.US, Mar 1–21 2023
├── Coinbase/                         # Raw 1-min OHLCV, Coinbase, Mar 1–21 2023
├── Crypto.com/                       # Raw 1-min OHLCV, Crypto.com, Mar 1–21 2023
├── Cleaned/                          # Gap-filled CSVs across all exchanges
├── Bloomberg data/                   # ⚠️ NOT COMMITTED — proprietary
├── Currency Exchange Rates/          # EUR/USD 1-min data
├── Reserves/
│   └── Reserves information USDC_values.xlsx
├── circleassets.csv                  # Circle reserve asset inputs for MTM
├── tetherassets.csv                  # Tether reserve asset inputs for MTM
├── Reserves_Analysis3.xlsx          # Reserve composition workbook
├── T-bill holdings.xlsx             # Tether T-bill holdings by quarter
├── Treasury holders.xlsx            # Treasury holder breakdown
├── USDCReg.xlsx                     # USDC peg deviation regression inputs
├── USDTReg.xlsx                     # USDT peg deviation regression inputs
├── crypto_ohlcv_data.xlsx           # Daily OHLCV for TVP-VAR (Jan 2020–Feb 2026)
└── traditional_market_data.xlsx     # ⚠️ Bloomberg-sourced — not redistributable
```

---

## File Inventory

### Binance/ (raw)
| File | Description |
|---|---|
| `binance_BTCUSD_1m_20230301_20230321.csv` | BTC/USD 1-min OHLCV |
| `binance_BTCUSDC_1m_20230301_20230321.csv` | BTC/USDC 1-min OHLCV |
| `binance_BTCUSDT_1m_20230301_20230321.csv` | BTC/USDT 1-min OHLCV |
| `binanceus_USDCUSD_1m_20230301_20230321.csv` | USDC/USD 1-min OHLCV |
| `binanceus_USDTUSD_1m_20230301_20230321.csv` | USDT/USD 1-min OHLCV |

### Coinbase/ (raw)
| File | Description |
|---|---|
| `coinbase_BTCEUR_1m_20230301_20230321.csv` | BTC/EUR 1-min OHLCV |
| `coinbase_BTCUSD_1m_20230301_20230321.csv` | BTC/USD 1-min OHLCV |
| `coinbase_BTCUSDC_1m_20230301_20230321.csv` | BTC/USDC 1-min OHLCV |
| `coinbase_BTCUSDT_1m_20230301_20230321.csv` | BTC/USDT 1-min OHLCV |
| `coinbase_USDCEUR_1m_20230301_20230321.csv` | USDC/EUR 1-min OHLCV |
| `coinbase_USDTEUR_1m_20230301_20230321.csv` | USDT/EUR 1-min OHLCV |
| `coinbase_USDTUSDC_1m_20230301_20230321.csv` | USDT/USDC 1-min OHLCV |

### Crypto.com/ (raw)
| File | Description |
|---|---|
| `crypto_com_BTCUSD_1m_20230301_20230321.csv` | BTC/USD 1-min OHLCV |
| `crypto_com_BTCUSDC_1m_20230301_20230321.csv` | BTC/USDC 1-min OHLCV |
| `crypto_com_BTCUSDT_1m_20230301_20230321.csv` | BTC/USDT 1-min OHLCV |
| `crypto_com_USDTUSDC_1m_20230301_20230321.csv` | USDT/USDC 1-min OHLCV |

### Cleaned/
Gap-filled versions of all raw files above:
- **LOCF** for gaps ≤5 minutes
- **ETS** (trained on pre-gap data only) for gaps 6–30 minutes
- **Dropped** for gaps >30 minutes

### Bloomberg data/ ⚠️ NOT COMMITTED
Contains: `traditional_market_data.xlsx`, `Countrydata_riskindicator.xlsx`, `Data values_longer.xlsx`, `Large country dataset_values.xlsx`, `currency_stress_results.xlsx`

Bloomberg-sourced (DXY, KBW Bank Index, S&P 500, XAU, VIX, SOFR, BVAL AA yield curves) — excluded due to licensing. To reproduce: pull from Bloomberg Terminal. DXY and S&P 500 can alternatively be sourced from FRED and Yahoo Finance.

### Currency Exchange Rates/
| File | Description |
|---|---|
| `DAT_ASCII_EURUSD_M1_2023.csv` | Raw EUR/USD 1-min data, 2023 |
| `eurusd_clean_march_2023.csv` | Cleaned EUR/USD for March 2023 window |

### Reserves/
| File | Description |
|---|---|
| `Reserves information USDC_values.xlsx` | Circle quarterly reserve disclosures, manually compiled from public attestation reports (Q3 2022–Q4 2025) |

### Root-level files
| File | Description | Used In |
|---|---|---|
| `circleassets.csv` | Circle reserve asset time series for MTM reconstruction | `Reserve_StressTesting.ipynb` |
| `tetherassets.csv` | Tether reserve asset time series for MTM reconstruction | `Reserve_StressTesting.ipynb` |
| `Reserves_Analysis3.xlsx` | Reserve composition analysis workbook | `Reserve_StressTesting.ipynb` |
| `T-bill holdings.xlsx` | Tether T-bill holdings by quarter | `Reserve_StressTesting.ipynb` |
| `Treasury holders.xlsx` | Treasury holder breakdown for duration-based MTM | `Reserve_StressTesting.ipynb` |
| `USDCReg.xlsx` | USDC peg deviation regression inputs | `Latest_Regressions.ipynb` |
| `USDTReg.xlsx` | USDT peg deviation regression inputs | `Latest_Regressions.ipynb` |
| `crypto_ohlcv_data.xlsx` | Daily OHLCV for 8-variable TVP-VAR (Jan 2020–Feb 2026) | `Volatility_Spillover.ipynb` |
| `traditional_market_data.xlsx` | Bloomberg daily data — S&P, DXY, XAU, KBW, VIX | `Volatility_Spillover.ipynb` |

---

## Data Sources

| Source | How to access |
|---|---|
| Binance.US REST API | `GET /api/v3/klines` — public, no auth |
| Coinbase REST API | `GET /products/{id}/candles` — public, no auth |
| Crypto.com REST API | `GET /public/get-candlestick` — public, no auth |
| CoinGecko API | Free tier — market cap / mint-burn proxy |
| CoinAPI | Paid — Coinbase L2 order book for Kyle's λ |
| Bloomberg Terminal | DXY, KBW, XAU, VIX, SOFR, BVAL AA curves |
| Circle attestation reports | circle.com/transparency |
| Tether attestation reports | tether.to/transparency |