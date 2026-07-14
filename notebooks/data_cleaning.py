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


if __name__ == "__main__":
    app.run()
