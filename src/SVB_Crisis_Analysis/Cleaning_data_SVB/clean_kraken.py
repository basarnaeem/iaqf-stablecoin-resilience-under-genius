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
EXPECTED_FREQ_MS = 60_000

A_TIME   = "datetime"
A_OPEN   = "open"
A_HIGH   = "high"
A_LOW    = "low"
A_CLOSE  = "close"
A_VOLUME = "volume"
A_TRADES = "trades"

B_TIME_S = "time_period_start"
B_TIME_E = "time_period_end"
B_OPEN   = "price_open"
B_HIGH   = "price_high"
B_LOW    = "price_low"
B_CLOSE  = "price_close"
B_VOLUME = "volume_traded"
B_TRADES = "trades_count"


def detect_schema(df):
    cols = set(df.columns)
    if A_TIME in cols and A_OPEN in cols:
        return "A"
    elif B_TIME_S in cols and B_OPEN in cols:
        return "B"
    return None


def get_ts_ms(df, schema):
    if schema == "A":
        return (pd.to_datetime(df[A_TIME], utc=True)
                  .astype("int64") // 10**6).values
    return (pd.to_datetime(df[B_TIME_S], utc=True)
              .astype("int64") // 10**6).values


def get_price_cols(schema):
    if schema == "A":
        return [A_OPEN, A_HIGH, A_LOW, A_CLOSE]
    return [B_OPEN, B_HIGH, B_LOW, B_CLOSE]


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
    n          = gap["n_missing"]
    after_idx  = gap["after_idx"]
    pre        = df.iloc[: after_idx + 1]
    price_cols = get_price_cols(schema)

    new_ms       = [gap["gap_start_ms"] + i * EXPECTED_FREQ_MS for i in range(n)]
    new_dt_start = pd.to_datetime(new_ms, unit="ms", utc=True)
    new_dt_end   = pd.to_datetime([x + EXPECTED_FREQ_MS for x in new_ms], unit="ms", utc=True)

    row = {
        "symbol":        [df["symbol"].iloc[0]] * n,
        "_ts_ms":        new_ms,
        "imputed":       True,
        "gap_size":      n,
        "impute_method": "",
    }

    if schema == "A":
        row[A_TIME]   = new_dt_start.strftime("%Y-%m-%d %H:%M:%S+00:00").tolist()
        row[A_VOLUME] = [0.0] * n
        row[A_TRADES] = [0]   * n
    else:
        row[B_TIME_S] = new_dt_start.strftime("%Y-%m-%dT%H:%M:%S.0000000Z").tolist()
        row[B_TIME_E] = new_dt_end.strftime("%Y-%m-%dT%H:%M:%S.0000000Z").tolist()
        row[B_VOLUME] = [0.0] * n
        row[B_TRADES] = [0]   * n

    if n <= SHORT_GAP_MAX:
        last = df.iloc[after_idx]
        for col in price_cols:
            row[col] = [float(last[col])] * n
        row["impute_method"] = "LOCF"
    else:
        for col in price_cols:
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
    print(f"  Schema     : {schema}")

    df["_ts_ms"] = get_ts_ms(df, schema)
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
                "schema":         schema,
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

    if schema == "A":
        col_order = ["symbol", A_TIME, A_OPEN, A_HIGH, A_LOW, A_CLOSE,
                     A_VOLUME, A_TRADES, "imputed", "gap_size", "impute_method"]
    else:
        col_order = ["symbol", B_TIME_S, B_TIME_E, B_OPEN, B_HIGH, B_LOW, B_CLOSE,
                     B_VOLUME, B_TRADES, "imputed", "gap_size", "impute_method"]

    df = df[[c for c in col_order if c in df.columns]]

    out_name = os.path.splitext(filename)[0] + "_cleaned.csv"
    out_path = os.path.join(output_dir, out_name)
    df.to_csv(out_path, index=False)

    n_imputed = int(df["imputed"].sum())
    print(f"  Saved      : {out_name}")
    print(f"  Summary    : {len(df)} total rows | {n_imputed} imputed | "
          f"{len(df) - n_imputed} original")


def main():
    parser = argparse.ArgumentParser(description="Kraken OHLCV Data Cleaner")
    parser.add_argument("--input",  required=True, help="Directory containing kraken_*.csv files")
    parser.add_argument("--output", required=True, help="Directory to write cleaned CSV files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    all_files = sorted(glob.glob(os.path.join(args.input, "kraken_*.csv")))

    if not all_files:
        print(f"\n  ERROR: No kraken_*.csv files found in:\n  {args.input}")
        return

    print(f"\n{'='*60}")
    print(f"  Kraken OHLCV Cleaner (Multi-Schema Version)")
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
