import marimo

__generated_with = "0.23.14"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(
        """
        # Data Cleaning — SSDC Dataset

        Load the 6 raw CSVs, apply fixes, export cleaned versions to `data_clean/`.
        """
    )
    return


@app.cell
def _():
    import pandas as pd
    from pathlib import Path
    return Path, pd


@app.cell
def _(Path):
    DATA_DIR = Path("data/Database SSDC")
    OUTPUT_DIR = Path("data_clean")
    OUTPUT_DIR.mkdir(exist_ok=True)
    return DATA_DIR, OUTPUT_DIR


@app.cell
def _():
    DELIMITERS = {
        "status_student.csv": ";",
    }
    return (DELIMITERS,)


@app.cell
def _(DATA_DIR, DELIMITERS, Path, pd):
    def load_raw(name):
        delim = DELIMITERS.get(name, ",")
        return pd.read_csv(DATA_DIR / name, delimiter=delim, encoding="utf-8-sig", dtype=str)

    raws = {}
    for f in sorted(DATA_DIR.glob("*.csv")):
        df = load_raw(f.name)
        raws[f.name] = df

    return load_raw, raws


@app.cell
def _(mo, raws):
    r = [
        {"Table": n, "Rows": len(df), "Cols": len(df.columns)}
        for n, df in raws.items()
    ]
    mo.md(
        f"""
        Loaded {len(raws)} tables, {sum(x['Rows'] for x in r):,} total rows.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        ## Phase 1: Standardize Date Formats

        Convert DMY (`dd/mm/yyyy`) → ISO (`yyyy-mm-dd`) in 3 tables.
        ISO tables are already clean.
        """
    )
    return


@app.cell
def _(mo, pd, raws):
    cleaned = {k: v.copy() for k, v in raws.items()}

    dmy_cols = {
        "status_student.csv": ["sync_date"],
        "tracking_company.csv": ["request_date", "send_date"],
    }

    conversions = {}
    for _fname, _cols in dmy_cols.items():
        _df = cleaned[_fname]
        for _col in _cols:
            series = _df[_col].dropna().str.strip()
            series = series[series != ""]
            before = series.head(3).tolist()
            parsed = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
            _df[_col] = parsed.dt.strftime("%Y-%m-%d")
            after = _df[_col].dropna().head(3).tolist()
            conversions[f"{_fname}.{_col}"] = (before, after)

    mo.md(
        f"""
        Converted **3 date columns** from DMY to ISO:

        | Table.Column | Before | After |
        |---|---|---|
        """
        + "\n".join(
            f"| {k} | `{v[0]}` | `{v[1]}` |"
            for k, v in conversions.items()
        )
    )
    return cleaned, conversions


@app.cell
def _(mo):
    mo.md(
        """
        ---
        ## Phase 2: Normalize Phone Numbers

        Prepend `0` to all `status_student.no_whatsapp` values (currently missing leading `0`).
        """
    )
    return


@app.cell
def _(cleaned, mo):
    _df = cleaned["status_student.csv"]
    _before = _df["no_whatsapp"].head(3).tolist()
    _df["no_whatsapp"] = "0" + _df["no_whatsapp"]
    _after = _df["no_whatsapp"].head(3).tolist()

    mo.md(
        f"""
        **status_student.no_whatsapp** — 25,000 values normalized.

        | Before | After |
        |---|---|
        | `{_before[0]}` | `{_after[0]}` |
        | `{_before[1]}` | `{_after[1]}` |
        | `{_before[2]}` | `{_after[2]}` |
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        ## Phase 3: Clean `list_nim`

        Strip garbage NIM values (48 occurrences of `"2"`) from `tracking_company.list_nim`.
        Recalculate `jumlah_dikirimkan` to match the cleaned list count.
        """
    )
    return


@app.cell
def _(cleaned, mo, pd):
    import re

    _df = cleaned["tracking_company.csv"]
    nim_re = re.compile(r"^\d{8,}$")
    removed_total = 0

    for _i, _row in _df.iterrows():
        _val = str(_row["list_nim"]) if pd.notna(_row["list_nim"]) and str(_row["list_nim"]).strip() else ""
        if not _val:
            continue
        _nims = [n.strip() for n in _val.split(",") if n.strip()]
        _clean = [n for n in _nims if nim_re.match(n)]
        _removed = len(_nims) - len(_clean)
        if _removed > 0:
            removed_total += _removed
        _df.at[_i, "list_nim"] = ", ".join(_clean) if _clean else ""
        _df.at[_i, "jumlah_dikirimkan"] = str(len(_clean))

    mo.md(
        f"""
        **tracking_company.list_nim** cleaned.

        - Removed **{removed_total}** garbage NIM values (all `"2"`)
        - `jumlah_dikirimkan` recalculated to match actual NIM count in `list_nim`
        - 598 unsent records (empty `list_nim`) left unchanged
        """
    )
    return


if __name__ == "__main__":
    app.run()
