# Stablecoin OHLCV Quality Audit

**Notebook:** `Stablecoin_OHLCV_Quality_Audit.ipynb`

---

## Overview

This notebook identifies and corrects anomalous High/Low values in stablecoin (USDT/USD, USDC/USD) OHLCV data. Stablecoins are pegged to $1.00, so any daily High or Low outside a defined peg band is almost certainly a data artifact — typically caused by a single stale or erroneous order executing on a thin order book.

For each suspicious row, the notebook:

1. Re-fetches the **raw trade-level file** from Binance.US bulk data to compute the true daily High/Low from actual executed transactions
2. Re-fetches the **Binance.US daily kline** to confirm what the original aggregated source reported
3. Cross-checks against **Kraken** as an independent US-exchange reference
4. Cross-checks against **Coinbase** (USDT only) as a further independent reference
5. Assigns a corrected value using the best available source and writes fixes back into the OHLCV Excel file with colour-coded highlighting

---

## Requirements

### Python Version
Python 3.9+

### Dependencies
```bash
pip install pandas numpy requests openpyxl
```

| Package | Purpose |
|---|---|
| pandas | Data handling and output |
| numpy | Numerical comparisons |
| requests | HTTP calls to Binance.US, Kraken, Coinbase APIs |
| openpyxl | Reading and writing .xlsx files |

---

## Configuration

At the top of the first code cell, set these two path variables before running:

```python
DIAGNOSTIC_OUTPUT_CSV = "stablecoin_diagnostic.csv"  # where to save audit results
INPUT_EXCEL_FILE = "ohlcv_final.xlsx"                 # the OHLCV file to audit and fix
```

Both paths are relative to the notebook's working directory.

---

## Input File Requirements

### `INPUT_EXCEL_FILE` (e.g. `ohlcv_final.xlsx`)
A multi-sheet Excel workbook produced by the OHLCV collection pipeline.

| Sheet | Columns |
|---|---|
| `USDT_USD` | Date, Open, High, Low, Close, Volume, Source |
| `USDC_USD` | Date, Open, High, Low, Close, Volume, Source |

The `Source` column is updated with a note on every corrected row.

---

## Suspicious Row Format

The `SUSPICIOUS` list in Cell 1 contains pre-identified anomalous dates as tuples:

```python
(pair, date_str, reported_high, reported_low)
```

These were flagged based on High or Low values falling outside the peg band (`PEG_LOW = 0.86`, `PEG_HIGH = 1.14`). To audit different dates, update this list.

---

## Data Sources

| Source | API / URL | Used for |
|---|---|---|
| Binance.US trade bulk | `data.binance.us/public_data/spot/daily/trades` | Ground-truth High/Low from raw executions |
| Binance.US kline bulk | `data.binance.us/public_data/spot/daily/klines` | Confirm originally reported kline values |
| Kraken REST API | `api.kraken.com/0/public/OHLC` | Independent cross-check (USDT and USDC) |
| Coinbase Exchange API | `api.exchange.coinbase.com/products/{pair}/candles` | Independent cross-check (USDT only — USDC not listed) |

Binance.US trade files are verified via SHA-256 checksum before use.

---

## Notebook Structure

### Cell 1 — Configuration & Suspicious Row List
Defines all config variables, peg band thresholds, exchange symbol mappings, and the list of suspicious dates.

### Cell 2 — Section header (Markdown)

### Cell 3 — Fetch Functions

| Function | Purpose |
|---|---|
| `get_binance_trade_range(pair, date_str)` | Downloads raw trade file; returns OHLC and trade count from executed prices |
| `get_binance_kline(pair, date_str)` | Downloads daily kline to confirm reported OHLCV |
| `get_kraken_ohlcv(pair, date_str)` | Fetches daily OHLCV via Kraken REST API |
| `get_coinbase_ohlcv(pair, date_str)` | Fetches daily OHLCV via Coinbase Exchange API (USDT/USD only) |

### Cell 4 — Run Diagnostic
Iterates over every suspicious row. For each date, calls all four fetch functions then selects the best replacement using a priority cascade:

```
trade file → kline re-fetch → kraken → coinbase
```

First source whose High and Low both fall within the peg band is selected. If none qualify, the row is flagged for manual review.

### Cell 5 — Summary Table
Prints reported vs. corrected values from each source, and counts fixable vs. manual-review rows.

### Cell 6 — Export Diagnostic Results
Saves full `results_df` to `DIAGNOSTIC_OUTPUT_CSV`. Review before running the fix step.

### Cell 7 — Apply Fixes to Excel
Reads `INPUT_EXCEL_FILE`, locates each corrected row by date, and applies one of two correction strategies:

| Strategy | Trigger | Correction | Excel Highlight |
|---|---|---|---|
| **A — Cross-exchange replacement** | `Best_Source` is coinbase or kraken | Replaces High and Low with cross-exchange values | Pale blue (#D9E1F2) |
| **B — Close-anchor correction** | `Best_Source` is NaN (all sources outside band or unavailable) | Sets High = Close; Low = min(reported_Low, Close) | Pale orange (#FCE4D6) |

Strategy B handles the thin-market case where a stale order executed on a near-empty book but no independent exchange was available. It preserves the close price and removes the uninformative intraday spike.

---

## Outputs

| File | Description |
|---|---|
| `DIAGNOSTIC_OUTPUT_CSV` | Full audit table: reported values, all source values, best replacement, and verdict for every suspicious row |
| `INPUT_EXCEL_FILE` (updated in-place) | Original OHLCV file with corrected High/Low values and colour-coded highlighting on fixed cells |

---

## Suggested Workflow

1. Update `SUSPICIOUS` if needed and set `INPUT_EXCEL_FILE` to your OHLCV file
2. Run Cells 1–5 to run the diagnostic and review the summary table
3. Inspect `DIAGNOSTIC_OUTPUT_CSV` to confirm you are comfortable with the proposed replacements
4. Run Cell 6 (the fix cell) to write corrections back into the Excel file
5. Re-run the Parkinson volatility check from `Volatility_Spillover.ipynb` to confirm no remaining outliers
