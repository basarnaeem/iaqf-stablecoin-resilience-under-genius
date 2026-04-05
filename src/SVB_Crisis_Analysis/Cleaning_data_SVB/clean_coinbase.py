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
EXPECTED_FREQ_MS = 60_000


def detect_schema(df):
    cols = set(df.columns)
    if "open_time_ms" in cols:
        return {
            "type":    "A",
            "ts_col":  "open_time_ms",
            "utc_col": "open_time_utc",
            "ts_unit": "ms",
            "id_col":  "exchange",
        }
    elif "start" in cols:
        return {
            "type":    "B",
            "ts_col":  "start",
            "utc_col": "timestamp_utc",
            "ts_unit": "s",
            "id_col":  "product_id",
        }
    return None


def to_ms(df, schema):
    if schema["ts_unit"] == "ms":
        return df[schema["ts_col"]].values.astype(np.int64)
    return (df[schema["ts_col"]].values.astype(np.int64)) * 1000


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


def build_imputed_rows(gap, df, schema):
    n         = gap["n_missing"]
    after_idx = gap["after_idx"]
    pre       = df.iloc[: after_idx + 1]

    new_ms = [gap["gap_start_ms"] + i * EXPECTED_FREQ_MS for i in range(n)]

    row = {
        "volume":        [0.0] * n,
        "imputed":       True,
        "gap_size":      n,
        "impute_method": "",
        "_ts_ms":        new_ms,
    }

    if "symbol" in df.columns:
        row["symbol"] = [df["symbol"].iloc[0]] * n
    if schema["id_col"] in df.columns:
        row[schema["id_col"]] = [df[schema["id_col"]].iloc[0]] * n

    if schema["ts_unit"] == "ms":
        row[schema["ts_col"]] = new_ms
    else:
        row[schema["ts_col"]] = [int(x // 1000) for x in new_ms]

    new_utc = (pd.to_datetime(new_ms, unit="ms", utc=True)
                 .strftime("%Y-%m-%d %H:%M:%S+00:00")
                 .tolist())
    row[schema["utc_col"]] = new_utc

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

    schema = detect_schema(df)
    if schema is None:
        print(f"  ERROR  Unrecognised schema -- skipping.")
        return
    print(f"  Schema     : {schema['type']} (time col = '{schema['ts_col']}')")

    missing = set(PRICE_COLS + ["volume"]) - set(df.columns)
    if missing:
        print(f"  ERROR  Missing essential columns: {missing} -- skipping.")
        return

    df["_ts_ms"] = to_ms(df, schema)
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
                "schema":         schema["type"],
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
            synthetic.append(build_imputed_rows(gap, df, schema))

    if synthetic:
        df = pd.concat([df] + synthetic, ignore_index=True)

    df = df.sort_values("_ts_ms").reset_index(drop=True)
    df = df.drop(columns=["_ts_ms"])

    out_name = os.path.splitext(filename)[0] + "_cleaned.csv"
    out_path = os.path.join(output_dir, out_name)
    df.to_csv(out_path, index=False)

    n_imputed = int(df["imputed"].sum())
    print(f"  Saved      : {out_name}")
    print(f"  Summary    : {len(df)} total rows | {n_imputed} imputed | "
          f"{len(df) - n_imputed} original")


def main():
    parser = argparse.ArgumentParser(description="Coinbase OHLCV Data Cleaner")
    parser.add_argument("--input",  required=True, help="Directory containing coinbase_*.csv files")
    parser.add_argument("--output", required=True, help="Directory to write cleaned CSV files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    all_files = sorted(glob.glob(os.path.join(args.input, "coinbase_*.csv")))

    if not all_files:
        print(f"\n  ERROR: No coinbase_*.csv files found in:\n  {args.input}")
        return

    print(f"\n{'='*60}")
    print(f"  Coinbase OHLCV Cleaner (Multi-Schema Version)")
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
