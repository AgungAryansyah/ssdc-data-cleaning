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


if __name__ == "__main__":
    app.run()
