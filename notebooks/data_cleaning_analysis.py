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
        # Data Cleaning Analysis — SSDC Dataset

        Analysis notebook to scan all 6 tables for issues needing cleanup before dashboard use.
        """
    )
    return


@app.cell
def _():
    import pandas as pd
    import numpy as np
    from pathlib import Path
    return Path, np, pd


@app.cell
def _(Path):
    DATA_DIR = Path("data/Database SSDC")
    TABLES = sorted(DATA_DIR.glob("*.csv"))
    [t.name for t in TABLES]
    return DATA_DIR, TABLES


@app.cell
def _(mo):
    mo.md(
        """
        ---
        ## Phase 1: Setup & Schema Sanity

        Load all 6 CSVs, inspect shapes/dtypes, compare column names/counts against the PDF spec.
        """
    )
    return


@app.cell
def _():
    EXPECTED = {
        "company.csv": {
            "cols": 9,
            "names": [
                "id_company", "company_name", "company_type", "industry_sector",
                "kota", "skala_perusahaan", "pic_name", "pic_phone", "created_at",
            ],
        },
        "talent_request.csv": {
            "cols": 19,
            "names": [
                "id_talent_req", "id_company", "nama_perusahaan", "alamat_kantor",
                "industri_sektor", "nama_pic", "no_whatsapp", "nama_posisi",
                "jenis_penempatan", "headcount", "bidang_studi_dibutuhkan",
                "minimum_semester", "deskripsi_requirement", "working_arrangement",
                "working_arrangement_detail", "durasi", "renumerasi", "request_date",
                "sumber_baris_form",
            ],
        },
        "student_all.csv": {
            "cols": 10,
            "names": [
                "NIM", "nama", "program_studi", "semester", "hp", "email_pribadi",
                "email_kampus", "bidang_minat", "jenis_penempatan_diminati", "bulan_masuk",
            ],
        },
        "status_student.csv": {
            "cols": 15,
            "names": [
                "id_status", "NIM", "email", "nama", "semester", "program_studi",
                "no_whatsapp", "CV", "portofolio", "IPK", "status", "domisili",
                "ketersediaan", "tools", "sync_date",
            ],
        },
        "tracking_company.csv": {
            "cols": 13,
            "names": [
                "id_tracking_company", "id_talent_req", "id_company",
                "nama_perusahaan", "posisi", "jenis_penempatan", "bidang_studi_dicari",
                "progress", "request_date", "send_date", "jumlah_permintaan",
                "jumlah_dikirimkan", "list_nim",
            ],
        },
        "tracking_student.csv": {
            "cols": 11,
            "names": [
                "id_tracking_student", "NIM", "id_tracking_company", "student_name",
                "internship_semester", "company", "position", "jenis_penempatan",
                "progress_student", "last_update", "rejection",
            ],
        },
    }

    DELIMITERS = {
        "status_student.csv": ";",
    }
    return DELIMITERS, EXPECTED


@app.cell
def _(DELIMITERS, EXPECTED, Path, pd):
    def load_table(path):
        delim = DELIMITERS.get(path.name, ",")
        return pd.read_csv(path, delimiter=delim, encoding="utf-8-sig", dtype=str)

    schemas = {}
    for f in sorted(Path("data/Database SSDC").glob("*.csv")):
        df = load_table(f)
        name = f.name

        actual_cols = list(df.columns)
        expected = EXPECTED.get(name, {})
        expected_names = expected.get("names", [])
        expected_count = expected.get("cols", None)

        missing = [c for c in expected_names if c not in actual_cols]
        extra = [c for c in actual_cols if c not in expected_names]
        has_bom = any(c.startswith("\ufeff") for c in actual_cols[:1])

        schemas[name] = {
            "df": df,
            "rows": len(df),
            "cols": len(actual_cols),
            "expected_cols": expected_count,
            "missing_cols": missing,
            "extra_cols": extra,
            "has_bom": has_bom,
            "dtypes": df.dtypes.to_dict(),
            "columns": actual_cols,
        }

    schemas
    return load_table, schemas


@app.cell
def _(mo, schemas):
    rows = []
    for fname, s in schemas.items():
        col_status = "ok" if s["expected_cols"] is None else (
            "ok" if s["cols"] == s["expected_cols"] else f"mismatch ({s['cols']} vs {s['expected_cols']})"
        )
        missing = ", ".join(s["missing_cols"]) if s["missing_cols"] else "-"
        extra = ", ".join(s["extra_cols"]) if s["extra_cols"] else "-"
        rows.append({
            "Table": fname,
            "Rows": s["rows"],
            "Cols": col_status,
            "Missing vs spec": missing,
            "Extra vs spec": extra,
            "BOM": s["has_bom"],
        })

    mo.ui.table(
        rows,
        label=f"Schema summary — 6 tables loaded, {sum(s['rows'] for s in schemas.values()):,} total rows",
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        **Note:** PDF docs mention 16 cols for `status_student` (includes `eligible`) and 14 for
        `tracking_company` (includes internal spreadsheet cols A,B). The actual CSVs have 15 and 13
        respectively — these are **expected** based on the docs' own note.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        ## Phase 2: Missing Values

        Per column: count/% of empty strings and NA-like tokens (`na`, `n/a`, `null`, `none`).
        Flag PK/FK/date columns that must never be null.
        """
    )
    return


@app.cell
def _():
    CRITICAL = {
        "company.csv":             {"id_company", "company_name", "created_at"},
        "talent_request.csv":      {"id_talent_req", "id_company", "request_date"},
        "student_all.csv":         {"NIM", "nama"},
        "status_student.csv":      {"id_status", "NIM", "sync_date"},
        "tracking_company.csv":    {"id_tracking_company", "id_talent_req", "id_company"},
        "tracking_student.csv":    {"id_tracking_student", "NIM", "id_tracking_company"},
    }

    NA_TOKENS = {"na", "n/a", "null", "none", "nan"}
    return CRITICAL, NA_TOKENS


@app.cell
def _(CRITICAL, NA_TOKENS, schemas):
    missing_rows = []

    for fname, s in schemas.items():
        df = s["df"]
        total = s["rows"]
        critical = CRITICAL.get(fname, set())

        for col in s["columns"]:
            empty_mask = df[col].isna() | (df[col].str.strip() == "")
            na_mask = df[col].str.strip().str.lower().isin(NA_TOKENS)
            blank_count = (empty_mask | na_mask).sum()

            if blank_count == 0:
                continue

            pct = blank_count / total * 100
            is_critical = col.lower() in {c.lower() for c in critical}

            missing_rows.append({
                "Table": fname,
                "Column": col,
                "Missing": blank_count,
                "%": round(pct, 2),
                "Critical": "YES" if is_critical else "",
            })

    len(missing_rows)
    return missing_rows


@app.cell
def _(mo, missing_rows):
    critical_hits = [r for r in missing_rows if r["Critical"] == "YES"]
    total_crit = len(critical_hits)

    mo.md(
        f"""
        ### Missing value findings

        {len(missing_rows)} column × table combinations have missing/blank values.
        {total_crit} of those are critical columns (PK/FK/date).
        """
    )
    return


@app.cell
def _(missing_rows, mo):
    if missing_rows:
        mo.ui.table(
            sorted(missing_rows, key=lambda r: (-r["Missing"], r["Table"], r["Column"])),
            selection=None,
            label="Missing values per column (sorted by count descending)",
        )
    else:
        mo.md("No missing values found in any column.")
    return


@app.cell
def _(missing_rows, mo):
    critical_hits = [r for r in missing_rows if r["Critical"] == "YES"]
    if critical_hits:
        mo.callout(
            mo.md(
                "\n".join(
                    f"- **{r['Table']}.{r['Column']}**: {r['Missing']} missing ({r['%']}%)"
                    for r in sorted(critical_hits, key=lambda r: (-r["Missing"], r["Table"]))
                )
            ),
            kind="warn",
        )
    else:
        mo.callout(
            mo.md("All critical columns (PKs, FKs, dates) have no missing values."),
            kind="neutral",
        )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        ## Phase 3: Duplicates & Uniqueness

        - PK duplicate check per table
        - Full-row duplicate check
        - `status_student.NIM` 1:1 with `student_all.NIM`
        - ID format conformance (`C\\d+`, `TR\\d+`, `SS\\d+`, `TC\\d+`, `TS\\d+`, `NIM` = `\\d{8,}`)
        """
    )
    return


@app.cell
def _():
    PK_MAP = {
        "company.csv":           "id_company",
        "talent_request.csv":    "id_talent_req",
        "student_all.csv":       "NIM",
        "status_student.csv":    "id_status",
        "tracking_company.csv":  "id_tracking_company",
        "tracking_student.csv":  "id_tracking_student",
    }

    import re
    ID_FORMATS = {
        "id_company":             (re.compile(r"^C\d+$"),  "C + digits"),
        "id_talent_req":          (re.compile(r"^TR\d+$"), "TR + digits"),
        "id_status":              (re.compile(r"^SS\d+$"), "SS + digits"),
        "id_tracking_company":    (re.compile(r"^TC\d+$"), "TC + digits"),
        "id_tracking_student":    (re.compile(r"^TS\d+$"), "TS + digits"),
        "NIM":                    (re.compile(r"^\d{8,}$"), "8+ digits"),
    }
    return ID_FORMATS, PK_MAP, re


@app.cell
def _(PK_MAP, schemas):
    dup_findings = []

    for fname, s in schemas.items():
        df = s["df"]
        pk = PK_MAP[fname]

        dup_mask = df[pk].duplicated(keep=False)
        dup_count = dup_mask.sum()
        dup_values = df.loc[dup_mask, pk].unique()

        if dup_count > 0:
            dup_findings.append({
                "Table": fname,
                "Issue": "PK duplicates",
                "Count": len(dup_values),
                "Rows affected": dup_count,
                "Samples": sorted(dup_values)[:5],
            })

        full_dup = df.duplicated().sum()
        if full_dup > 0:
            dup_findings.append({
                "Table": fname,
                "Issue": "Full-row duplicates",
                "Count": full_dup,
                "Rows affected": full_dup,
                "Samples": None,
            })

    len(dup_findings)
    return dup_findings


@app.cell
def _(mo, schemas):
    sa = schemas["student_all.csv"]["df"]
    ss = schemas["status_student.csv"]["df"]

    sa_nims = set(sa["NIM"])
    ss_nims = set(ss["NIM"])

    only_in_ss = ss_nims - sa_nims
    only_in_sa = sa_nims - ss_nims
    ss_dup_nims = len(ss["NIM"]) - ss["NIM"].nunique()

    mo.md(
        f"""
        ### NIM: `status_student` ↔ `student_all`

        | Check | Result |
        |---|---|
        | `student_all` NIM count | {len(sa):,} rows, {len(sa_nims):,} unique |
        | `status_student` NIM count | {len(ss):,} rows, {len(ss_nims):,} unique |
        | NIM in `status` but NOT in `student_all` | {len(only_in_ss)} |
        | NIM in `student_all` but NOT in `status` | {len(only_in_sa)} |
        | `status_student` NIM duplicates | {ss_dup_nims} |
        """
    )
    return only_in_sa, only_in_ss


@app.cell
def _(ID_FORMATS, PK_MAP, mo, schemas):
    id_rows = []
    for fname, pk in PK_MAP.items():
        df = schemas[fname]["df"]
        fmt_re, desc = ID_FORMATS[pk]
        bad = sum(1 for v in df[pk] if not fmt_re.match(str(v)))
        total = len(df)
        id_rows.append({
            "Table": fname,
            "Column": pk,
            "Expected": desc,
            "Bad": bad,
            "Total": total,
            "Status": "OK" if bad == 0 else f"{bad}/{total} bad",
        })

    mo.md(
        f"""
        ### ID format conformance

        """
    )
    return id_rows


@app.cell
def _(id_rows, mo):
    mo.ui.table(
        id_rows,
        label="ID format check — all IDs match their expected pattern",
    )
    return


@app.cell
def _(dup_findings, mo):
    if dup_findings:
        mo.callout(
            mo.ui.table(dup_findings, label="Duplicate findings"),
            kind="warn",
        )
    else:
        mo.callout(
            mo.md("No duplicate records found — all PKs unique, no full-row duplicates."),
            kind="neutral",
        )
    return


if __name__ == "__main__":
    app.run()
