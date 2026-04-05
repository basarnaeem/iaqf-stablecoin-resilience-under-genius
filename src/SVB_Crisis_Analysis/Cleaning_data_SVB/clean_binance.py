import os
import glob
import argparse
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

warnings.filterwarnings("ignore")

SHORT_GAP_MAX    = 5
MEDIUM_GAP_MAX   = 30

PRICE_COLS       = ["open", "high", "low", "close"]
TIME_MS_COL      = "open_time_ms"
TIME_UTC_COL     = "open_time_utc"
VOLUME_COL       = "volume"
TRADES_COL       = "num_trades"
CLOSE_TIME_COL   = "close_time_ms"
EXPECTED_FREQ_MS = 60_000

REQUIRED_COLS = {"open_time_ms", "open", "high", "low", "close", "volume"}


def detect_gaps(ts_ms):
    gaps = []
    for i in range(1, len(ts_ms)):
        delta = int(round((ts_ms[i] - ts_ms[i - 1]) / EXPECTED_FREQ_MS)) - 1
        if delta > 0:
            gaps.append({
                "after_idx":    i - 1,
                "n_missing":    delta,
                "gap_start_ms": ts_ms[i - 1] + EXPECTED_FREQ_MS,
                "gap_end_ms":   ts_ms[i]     - EXPECTED_FREQ_MS,
            })
    return gaps


def ets_forecast(series, n_steps):
    if len(series) < 4:
        return np.full(n_steps, series.iloc[-1])
    model = SimpleExpSmoothing(series.values, initialization_method="estimated")
    return model.fit(optimized=True).forecast(n_steps)


def build_imputed_rows(gap, df):
    n         = gap["n_missing"]
    after_idx = gap["after_idx"]
    pre       = df.iloc[: after_idx + 1]

    new_ms  = [gap["gap_start_ms"] + i * EXPECTED_FREQ_MS for i in range(n)]
    new_utc = (pd.to_datetime(new_ms, unit="ms", utc=True)
                 .strftime("%Y-%m-%d %H:%M:%S")
                 .tolist())
    new_close_ms = [x + 59999 for x in new_ms]

    row = {
        "symbol":        [df["symbol"].iloc[0]] * n,
        TIME_MS_COL:     new_ms,
        TIME_UTC_COL:    new_utc,
        VOLUME_COL:      [0.0] * n,
        CLOSE_TIME_COL:  new_close_ms,
        TRADES_COL:      [0]   * n,
        "_ts_ms":        new_ms,
        "imputed":       True,
        "gap_size":      n,
        "impute_method": "",
    }

    if n <= SHORT_GAP_MAX:
        last = df.iloc[after_idx]
        for col in PRICE_COLS:
            row[col] = [float(last[col])] * n
        row["impute_method"] = "LOCF"
    else:
        for col in PRICE_COLS:
            row[col] = ets_forecast(pre[col], n).tolist()
        row["impute_method"] = "ETS"

    return pd.DataFrame(row)


def clean_file(filepath, output_dir, long_gap_log):
    filename = os.path.basename(filepath)
    print(f"\n  {'─'*55}")
    print(f"  Processing : {filename}")

    df = pd.read_csv(filepath)
    print(f"  Columns    : {list(df.columns)}")
    print(f"  Rows       : {len(df)}")

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        print(f"  ERROR  Missing essential columns: {missing} -- skipping.")
        return

    df["_ts_ms"] = df[TIME_MS_COL].values.astype(np.int64)
    df = df.sort_values("_ts_ms").reset_index(drop=True)

    df["imputed"]       = False
    df["gap_size"]      = 0
    df["impute_method"] = "none"

    gaps = detect_gaps(df["_ts_ms"].values)
    print(f"  Gaps found : {len(gaps)}")

    synthetic = []
    for gap in gaps:
        n = gap["n_missing"]
        if n > MEDIUM_GAP_MAX:
            long_gap_log.append({
                "file":           filename,
                "gap_start_utc":  str(pd.Timestamp(gap["gap_start_ms"], unit="ms", tz="UTC")),
                "gap_end_utc":    str(pd.Timestamp(gap["gap_end_ms"],   unit="ms", tz="UTC")),
                "n_missing_bars": n,
                "action":         "DROPPED -- not imputed",
            })
            print(f"  DROPPED    Long gap : {n} bars "
                  f"({pd.Timestamp(gap['gap_start_ms'], unit='ms', tz='UTC')} -> "
                  f"{pd.Timestamp(gap['gap_end_ms'], unit='ms', tz='UTC')})")
        else:
            method = "LOCF" if n <= SHORT_GAP_MAX else "ETS"
            print(f"  {method:<4} fill   : {n} bar(s) at "
                  f"{pd.Timestamp(gap['gap_start_ms'], unit='ms', tz='UTC')}")
            synthetic.append(build_imputed_rows(gap, df))

    if synthetic:
        df = pd.concat([df] + synthetic, ignore_index=True)

    df = df.sort_values("_ts_ms").reset_index(drop=True)
    df = df.drop(columns=["_ts_ms"])

    col_order = ["symbol", TIME_MS_COL, TIME_UTC_COL, "open", "high", "low",
                 "close", VOLUME_COL, CLOSE_TIME_COL, TRADES_COL,
                 "imputed", "gap_size", "impute_method"]
    df = df[[c for c in col_order if c in df.columns]]

    out_name = os.path.splitext(filename)[0] + "_cleaned.csv"
    out_path = os.path.join(output_dir, out_name)
    df.to_csv(out_path, index=False)

    n_imputed = int(df["imputed"].sum())
    print(f"  Saved      : {out_name}")
    print(f"  Summary    : {len(df)} total rows | {n_imputed} imputed | "
          f"{len(df) - n_imputed} original")


def main():
    parser = argparse.ArgumentParser(description="Binance OHLCV Data Cleaner")
    parser.add_argument("--input",  required=True, help="Directory containing binance(us)_*.csv files")
    parser.add_argument("--output", required=True, help="Directory to write cleaned CSV files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    all_files = sorted(
        glob.glob(os.path.join(args.input, "binance_*.csv")) +
        glob.glob(os.path.join(args.input, "binanceus_*.csv"))
    )

    if not all_files:
        print(f"\n  ERROR: No binance(us)_*.csv files found in:\n  {args.input}")
        return

    print(f"\n{'='*60}")
    print(f"  Binance OHLCV Cleaner")
    print(f"  Input  : {args.input}")
    print(f"  Output : {args.output}")
    print(f"  Found  : {len(all_files)} file(s)")
    for f in all_files:
        print(f"           {os.path.basename(f)}")
    print(f"{'='*60}")

    long_gap_log = []
    for filepath in all_files:
        clean_file(filepath, args.output, long_gap_log)

    print(f"\n{'='*60}")
    if long_gap_log:
        log_path = os.path.join(args.output, "long_gaps_dropped.csv")
        pd.DataFrame(long_gap_log).to_csv(log_path, index=False)
        print(f"  {len(long_gap_log)} long gap(s) dropped.")
        print(f"  Audit log -> long_gaps_dropped.csv")
    else:
        print(f"  No long gaps found.")

    print(f"\n  Done. {len(all_files)} files processed.\n")


if __name__ == "__main__":
    main()
