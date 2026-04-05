# Crypto OHLCV Data Cleaners

Four independent scripts to clean 1-minute OHLCV (candlestick) data from Binance, Coinbase, Crypto.com, and Kraken. Each script detects missing bars (gaps), imputes them using a causal strategy (no lookahead bias), and writes cleaned CSV files to a specified output directory.

---

## Requirements

```bash
pip install pandas statsmodels numpy
```

---

## Usage

Every script takes two required arguments:

| Argument   | Description                              |
|------------|------------------------------------------|
| `--input`  | Directory containing the raw CSV files   |
| `--output` | Directory where cleaned CSVs are written |

The output directory is created automatically if it does not exist.

---

## Scripts

### `clean_binance.py`

Processes files matching `binance_*.csv` and `binanceus_*.csv`.

**Expected columns:** `symbol, open_time_ms, open_time_utc, open, high, low, close, volume, close_time_ms, num_trades`

```bash
python clean_binance.py --input /path/to/raw --output /path/to/cleaned
```

---

### `clean_coinbase.py`

Processes files matching `coinbase_*.csv`. Automatically detects and handles two schemas:

| Schema | Identifier column | Time column     | Time unit   |
|--------|-------------------|-----------------|-------------|
| A      | `exchange`        | `open_time_ms`  | milliseconds |
| B      | `product_id`      | `start`         | seconds      |

```bash
python clean_coinbase.py --input /path/to/raw --output /path/to/cleaned
```

---

### `clean_crypto_com.py`

Processes files matching `crypto_com_*.csv`.

**Expected columns:** `symbol, open_time_ms, open_time_utc, open, high, low, close, volume`

```bash
python clean_crypto_com.py --input /path/to/raw --output /path/to/cleaned
```

---

### `clean_kraken.py`

Processes files matching `kraken_*.csv`. Automatically detects and handles two schemas:

| Schema | Time column          | Price columns                                    |
|--------|----------------------|--------------------------------------------------|
| A      | `datetime`           | `open, high, low, close`                         |
| B      | `time_period_start`  | `price_open, price_high, price_low, price_close` |

```bash
python clean_kraken.py --input /path/to/raw --output /path/to/cleaned
```

---

## Gap Imputation Strategy

All four scripts use the same fully causal imputation strategy (no lookahead bias):

| Gap Size (bars) | Method                                                                                   |
|-----------------|------------------------------------------------------------------------------------------|
| 1 – 5           | **LOCF** — Last Observation Carried Forward. The last known price is repeated.           |
| 6 – 30          | **ETS** — Simple Exponential Smoothing forecast trained only on pre-gap data.            |
| 31+             | **Dropped** — The gap is not imputed and is logged to `long_gaps_dropped.csv`.           |

Volume and trade count are always set to `0` for imputed bars.

---

## Output

Each input file produces a corresponding `*_cleaned.csv` in the output directory. Three audit columns are appended to every row:

| Column          | Type    | Description                                         |
|-----------------|---------|-----------------------------------------------------|
| `imputed`       | bool    | `True` if the row was synthetically generated       |
| `gap_size`      | int     | Number of bars in the gap this row belongs to       |
| `impute_method` | string  | `"LOCF"`, `"ETS"`, or `"none"` for original rows   |

If any gaps longer than 30 bars were encountered, a `long_gaps_dropped.csv` audit log is written to the output directory with the fields: `file`, `gap_start_utc`, `gap_end_utc`, `n_missing_bars`, `action`.

---

## Configuration

The following constants can be adjusted at the top of each script:

| Constant          | Default  | Description                             |
|-------------------|----------|-----------------------------------------|
| `SHORT_GAP_MAX`   | `5`      | Maximum gap size for LOCF imputation    |
| `MEDIUM_GAP_MAX`  | `30`     | Maximum gap size for ETS imputation     |
| `EXPECTED_FREQ_MS`| `60000`  | Expected bar frequency in milliseconds  |
