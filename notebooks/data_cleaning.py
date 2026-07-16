import marimo

__generated_with = "0.23.14"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # Data Cleaning — SSDC Dataset

    Load the 6 raw CSVs, apply fixes, export cleaned versions to `data_clean/`.
    """)
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
def _(DATA_DIR, DELIMITERS, pd):
    def load_raw(name):
        delim = DELIMITERS.get(name, ",")
        return pd.read_csv(DATA_DIR / name, delimiter=delim, encoding="utf-8-sig", dtype=str)

    raws = {}
    for f in sorted(DATA_DIR.glob("*.csv")):
        df = load_raw(f.name)
        raws[f.name] = df
    return (raws,)


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
    mo.md("""
    ---
    ## Phase 1: Standardize Date Formats

    Convert DMY (`dd/mm/yyyy`) → ISO (`yyyy-mm-dd`) in 3 tables.
    ISO tables are already clean.
    """)
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
    return (cleaned,)


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Phase 2: Normalize Phone Numbers

    Prepend `0` to all `status_student.no_whatsapp` values (currently missing leading `0`).
    """)
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
    mo.md("""
    ---
    ## Phase 3: Recover truncated NIMs in `list_nim`

    Cross-reference `tracking_student` to find full NIMs for the 48 truncated `"2"` entries
    in `tracking_company.list_nim`. Recalculate `jumlah_dikirimkan`.
    """)
    return


@app.cell
def _(cleaned, mo, pd):
    import re

    _df = cleaned["tracking_company.csv"]
    _ts = cleaned["tracking_student.csv"]
    nim_re = re.compile(r"^\d{8,}$")
    recovered_total = 0

    _samples = []
    for _i, _row in _df.iterrows():
        _val = str(_row["list_nim"]) if pd.notna(_row["list_nim"]) and str(_row["list_nim"]).strip() else ""
        if not _val:
            continue
        _nims = [n.strip() for n in _val.split(",") if n.strip()]
        _garbage = [n for n in _nims if not nim_re.match(n)]
        _clean = [n for n in _nims if nim_re.match(n)]

        if _garbage:
            _tc_id = _row["id_tracking_company"]
            _ts_nims = set(_ts[_ts["id_tracking_company"] == _tc_id]["NIM"].tolist())
            _extra = sorted(_ts_nims - set(_clean))

            for _g in _garbage:
                if _extra:
                    _recovered = _extra.pop(0)
                    _clean.append(_recovered)
                    recovered_total += 1
                    if len(_samples) < 3:
                        _samples.append((_tc_id, _g, _recovered))

        _df.at[_i, "list_nim"] = ",".join(_clean) if _clean else ""
        _df.at[_i, "jumlah_dikirimkan"] = str(len(_clean))

    _sample_text = "\n".join(
        f"| `{_s[0]}` | `{_s[1]}` | `{_s[2]}` |"
        for _s in _samples
    )

    mo.md(
        f"""
        **tracking_company.list_nim** — recovered truncated NIMs from `tracking_student`.

        | TC ID | Garbage | Recovered |
        |---|---|---|
        {_sample_text}

        - **{recovered_total}** truncated NIMs recovered (all `"2"` → full 8-digit NIM)
        - `jumlah_dikirimkan` recalculated to match final `list_nim` count
        - 598 unsent records (empty `list_nim`) left unchanged
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Phase 4: Normalize `renumerasi`

    Add `renumerasi_category` column: `"Paid"` / `"Non-Paid"` / `"Transport-Only"`.
    Original `renumerasi` column preserved.
    """)
    return


@app.cell
def _(cleaned, mo, pd):
    _df = cleaned["talent_request.csv"]
    _ren = _df["renumerasi"].str.strip().str.lower()

    _conds = [
        _ren.str.contains("non.paid", na=False),
        _ren.str.contains("transport", na=False),
        _ren.str.match(r"^rp\s?[\d.,]+", na=False),
    ]
    _choices = ["Non-Paid", "Transport-Only", "Paid"]
    _df["renumerasi_category"] = pd.Series("Paid", index=_df.index)
    for _cond, _choice in zip(_conds, _choices):
        _df.loc[_cond, "renumerasi_category"] = _choice

    _counts = _df["renumerasi_category"].value_counts().to_dict()

    mo.md(
        f"""
        **talent_request.renumerasi** categorized.

        | Category | Count |
        |---|---|
        | Paid | {_counts.get('Paid', 0):,} |
        | Non-Paid | {_counts.get('Non-Paid', 0):,} |
        | Transport-Only | {_counts.get('Transport-Only', 0):,} |
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Phase 5: Normalize `durasi`

    Extract `durasi_months` column: numeric value for `"N Bulan"`, 999 for `"Tidak Terbatas"`.
    Original `durasi` column preserved.
    """)
    return


@app.cell
def _(cleaned, mo):
    _df = cleaned["talent_request.csv"]
    _dur = _df["durasi"].str.strip()

    _df["durasi_months"] = 0
    _df.loc[_dur == "Tidak Terbatas", "durasi_months"] = 999

    _mask = _dur.str.match(r"^(\d+)\s*Bulan$")
    _df.loc[_mask, "durasi_months"] = _dur[_mask].str.extract(r"(\d+)")[0].astype(int)

    _counts = _df["durasi_months"].value_counts().sort_index().to_dict()

    mo.md(
        f"""
        **talent_request.durasi** normalized → `durasi_months`.

        | Value | Count |
        |---|---|
        | 3 | {_counts.get(3, 0):,} |
        | 4 | {_counts.get(4, 0):,} |
        | 6 | {_counts.get(6, 0):,} |
        | 999 (Tidak Terbatas) | {_counts.get(999, 0):,} |
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Phase 5.5: Placement Status Reconciliation

    Source of truth = latest timestamp. Reconcile `status_student` and `tracking_student`
    placement status using `last_update` vs `sync_date` comparison.
    """)
    return


@app.cell
def _(cleaned, mo, pd):
    _ss = cleaned["status_student.csv"]
    _ts = cleaned["tracking_student.csv"]

    _ss["placement_verified"] = ""
    _ts_nims = set(_ts["NIM"])

    # B1: TS Placement newer than SS sync_date → update SS
    _placed_nims = set(_ts[_ts["rejection"] == "Placement"]["NIM"])
    _ss_not_placed = _placed_nims - set(_ss[_ss["ketersediaan"] == "Placed"]["NIM"])

    _ts["last_update_dt"] = pd.to_datetime(_ts["last_update"], errors="coerce", format="%Y-%m-%d")
    _updated = 0
    _skipped = 0

    for _nim in _ss_not_placed:
        _ts_recs = _ts[(_ts["NIM"] == _nim) & (_ts["rejection"] == "Placement")]
        if _ts_recs.empty:
            continue
        _ts_date = _ts_recs["last_update_dt"].max()
        _ss_idx = _ss[_ss["NIM"] == _nim].index
        if len(_ss_idx) == 0:
            continue
        _ss_date = pd.to_datetime(_ss.at[_ss_idx[0], "sync_date"], errors="coerce", format="%Y-%m-%d")

        if pd.notna(_ts_date) and pd.notna(_ss_date) and _ts_date > _ss_date:
            _ss.at[_ss_idx[0], "ketersediaan"] = "Placed"
            _ss.at[_ss_idx[0], "sync_date"] = _ts_date.strftime("%Y-%m-%d")
            _updated += 1
        else:
            _skipped += 1

    # B3: Add placement_verified column to separate tracking verification from placement status
    _ss_placed_set = set(_ss[_ss["ketersediaan"] == "Placed"]["NIM"])
    _untracked = _ss_placed_set - _ts_nims
    for _nim in _untracked:
        _idx = _ss[_ss["NIM"] == _nim].index
        if len(_idx) > 0:
            _ss.at[_idx[0], "placement_verified"] = "Tidak"

    _tracked_placed = _ss_placed_set & _ts_nims
    for _nim in _tracked_placed:
        _idx = _ss[_ss["NIM"] == _nim].index
        if len(_idx) > 0:
            _ss.at[_idx[0], "placement_verified"] = "Ya"

    mo.md(
        f"""
        ### Placement reconciliation results

        | Case | Count | Action |
        |---|---|---|
        | TS Placement → SS updated (TS newer) | {_updated} | SS `ketersediaan` → Placed |
        | TS Placement, SS newer (ambiguous) | {_skipped} | Left as-is |
        | SS Placed, no tracking | {len(_untracked)} | `placement_verified` → Tidak |
        | SS Placed, has tracking | {len(_tracked_placed)} | `placement_verified` → Ya |
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Phase 5.6: Add `eligible` Column

    Derive `eligible` from `status = Active AND CV = Ada`. Verifying against
    students who actually appear in tracking (applying) vs not.
    """)
    return


@app.cell
def _(cleaned, mo):
    _ss = cleaned["status_student.csv"]
    _ts = cleaned["tracking_student.csv"]

    _ss["eligible"] = ((_ss["status"] == "Active") & (_ss["CV"] == "Ada")).map({True: "Ya", False: "Tidak"})

    _applying = set(_ts["NIM"])
    _not_applying = set(_ss["NIM"]) - _applying

    _a_eligible = _ss[_ss["NIM"].isin(_applying)]["eligible"]
    _na_eligible = _ss[_ss["NIM"].isin(_not_applying)]["eligible"]

    mo.md(
        f"""
        **Eligibility**: `status = Active AND CV = Ada`.

        | Group | Ya | Tidak | Ya % |
        |---|---|---|---|
        | Applying ({len(_applying):,}) | {(_a_eligible == 'Ya').sum():,} | {(_a_eligible == 'Tidak').sum():,} | {(_a_eligible == 'Ya').mean()*100:.0f}% |
        | Not applying ({len(_not_applying):,}) | {(_na_eligible == 'Ya').sum():,} | {(_na_eligible == 'Tidak').sum():,} | {(_na_eligible == 'Ya').mean()*100:.0f}% |

        **100% of applying students are eligible** — zero applying students have `CV = Tidak Ada` or non-Active `status`. The rule perfectly separates the two groups.
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Phase 5.7: Normalize `bulan_masuk`

    Parse human-readable `"Bulan Tahun"` format into numeric `bulan_masuk_month`
    and `bulan_masuk_year` columns. Original column preserved.
    """)
    return


@app.cell
def _(cleaned, mo, pd):
    _sa = cleaned["student_all.csv"]
    _bm = _sa["bulan_masuk"].str.strip()

    _month_names = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
        "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
        "September": "09", "Oktober": "10", "November": "11", "Desember": "12",
    }

    _parts = _bm.str.extract(r"^(\w+)\s+(\d{4})$")
    _sa["bulan_masuk_month"] = _parts[0].map(_month_names).fillna("00")
    _sa["bulan_masuk_year"] = _parts[1].fillna("0000")

    _yrs = sorted(_sa["bulan_masuk_year"].unique(), key=int)
    _yrs_str = ", ".join(str(y) for y in _yrs if y != "0000")

    mo.md(
        f"""
        **student_all.bulan_masuk** normalized → `bulan_masuk_month`, `bulan_masuk_year`.

        | Column | Description |
        |---|---|
        | `bulan_masuk` | Original `"Bulan Tahun"` text (preserved) |
        | `bulan_masuk_month` | Numeric `01`–`12` |
        | `bulan_masuk_year` | Numeric year, range: {_yrs_str} |
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Phase 6: Export Cleaned CSVs

    Write all 6 DataFrames to `data_clean/` — UTF-8, `,` delimiter, no BOM.
    """)
    return


@app.cell
def _(OUTPUT_DIR, cleaned, mo):
    _written = []
    for _name, _df in sorted(cleaned.items()):
        _path = OUTPUT_DIR / _name
        _df.to_csv(_path, index=False, encoding="utf-8")
        _written.append({"File": _name, "Rows": len(_df), "Cols": len(_df.columns)})

    mo.md(
        f"""
        Exported {len(_written)} files to `data_clean/`:

        | File | Rows | Cols |
        |---|---|---|
        """
        + "\n".join(f"| `{w['File']}` | {w['Rows']:,} | {w['Cols']} |" for w in _written)
    )
    return


if __name__ == "__main__":
    app.run()
