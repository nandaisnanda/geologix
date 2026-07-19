"""Runner Pipeline 3 — Weather-Risk Overlay (SPEC.md Bagian 2 Pipeline 3).

Orkestrasi seluruh rumus Bagian 3 Pipeline 3, urutan internal SPEC 5.2:
1. Muat snapshot hujan real-time (``fetch_openmeteo.py``) dan baseline
   historis CHIRPS (``fetch_chirps.py``), gabung per ``h3_index``.
2. Getis-Ord Gi* pada baseline historis (Bagian 3.4) -> z-score per sel;
   sel tanpa data baseline (NaN) dibuang SEBELUM uji supaya Xbar/S tidak bias.
3. Normalisasi Min-Max kedua kriteria (Bagian 3.1): curah hujan real-time
   dan z-score Gi* (baseline historis).
4. Bobot AHP dari ``PAIRWISE_MATRIX_P3`` (Bagian 3.2, CR <= 0.1 diverifikasi
   setiap run — raise kalau matriks diubah jadi tidak konsisten).
5. WLC (Bagian 3.3): RiskIndex = sum(wi * xi_norm) per sel, di [0, 1].
6. Simpan ke tabel ``weather_risk_grid`` (riwayat antar-jam menumpuk lewat
   ``computed_at``) + log ``pipeline_logs`` (SPEC 5.3).

``jumlah_temuan`` di log = jumlah sel hotspot Gi* signifikan (p < 0.05) —
"temuan" P3 adalah hotspot teruji statistik, bukan sekadar jumlah sel ditulis
(jumlah sel dicatat di ``detail``). File runner (``__main__.py``) di luar
daftar SPEC 5.1 — keputusan minimal yang sama dengan Pipeline 1 & 2.

Pemakaian::

    python -m src.pipeline_3_weather_risk
    python -m src.pipeline_3_weather_risk --openmeteo-csv X --chirps-csv Y
"""

import argparse

import pandas as pd

from src.data_ingestion.fetch_chirps import BASELINE_OUTPUT_PATH
from src.data_ingestion.fetch_openmeteo import RAINFALL_OUTPUT_PATH
from src.db.writer import log_pipeline_run, save_weather_risk_grid
from src.pipeline_3_weather_risk.ahp_weights import (
    PAIRWISE_MATRIX_P3,
    compute_ahp_weights,
)
from src.pipeline_3_weather_risk.h3_grid import cell_to_polygon
from src.pipeline_3_weather_risk.hotspot_gi_star import gi_star
from src.pipeline_3_weather_risk.normalize import min_max_normalize
from src.pipeline_3_weather_risk.wlc_combine import wlc_combine

PIPELINE_NAME = "pipeline_3_weather_risk"


def run(rainfall: pd.DataFrame, baseline: pd.DataFrame, engine=None) -> dict:
    """Gi* -> normalisasi -> AHP -> WLC -> simpan + log. Return ringkasan.

    ``rainfall``: kolom h3_index, rainfall_mm, weather_time (fetch_openmeteo).
    ``baseline``: kolom h3_index, rainfall_hist_mm (fetch_chirps).
    """
    df = rainfall.merge(
        baseline[["h3_index", "rainfall_hist_mm"]], on="h3_index", how="inner"
    )
    df = df.dropna(subset=["rainfall_mm", "rainfall_hist_mm"]).reset_index(drop=True)
    n_dropped = len(rainfall) - len(df)  # tanpa pasangan baseline atau NaN
    if df.empty:
        raise ValueError("tidak ada sel dengan data hujan real-time DAN baseline")

    hotspot = gi_star(list(df["h3_index"]), df["rainfall_hist_mm"].to_numpy())
    df = df.merge(hotspot, on="h3_index")

    ahp = compute_ahp_weights(PAIRWISE_MATRIX_P3)  # raise kalau CR > 0.1
    risk = wlc_combine(
        criteria=[
            min_max_normalize(df["rainfall_mm"].to_numpy()),
            min_max_normalize(df["gi_star_z"].to_numpy()),
        ],
        weights=ahp.weights,
    )
    df["risk_index"] = risk

    rows = [
        {
            "h3_index": r.h3_index,
            "geom_wkt": cell_to_polygon(r.h3_index).wkt,
            "rainfall_realtime_mm": r.rainfall_mm,
            "hotspot_gi_star_z": r.gi_star_z,
            "risk_index": r.risk_index,
        }
        for r in df.itertuples()
    ]
    n_saved = save_weather_risk_grid(rows, engine=engine)

    n_hotspot = int(df["is_hotspot"].sum())
    summary = {
        "cells": len(df),
        "dropped": n_dropped,
        "hotspots": n_hotspot,
        "weights": [round(float(w), 4) for w in ahp.weights],
        "cr": round(ahp.consistency_ratio, 4),
        "risk_min": round(float(df["risk_index"].min()), 4),
        "risk_max": round(float(df["risk_index"].max()), 4),
        "weather_time": str(df["weather_time"].iloc[0]),
        "saved": n_saved,
    }
    log_pipeline_run(
        PIPELINE_NAME,
        n_hotspot,
        "success",
        detail=(
            f"cells={summary['cells']} dropped={n_dropped} "
            f"hotspots={n_hotspot} weights={summary['weights']} "
            f"cr={summary['cr']} risk_max={summary['risk_max']} "
            f"weather_time={summary['weather_time']}"
        ),
        engine=engine,
    )
    return summary


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Pipeline 3 - Weather-Risk Overlay")
    parser.add_argument(
        "--openmeteo-csv",
        default=str(RAINFALL_OUTPUT_PATH),
        help="snapshot hujan real-time (default: data/raw/openmeteo_latest.csv)",
    )
    parser.add_argument(
        "--chirps-csv",
        default=str(BASELINE_OUTPUT_PATH),
        help="baseline historis CHIRPS (default: data/raw/chirps_baseline.csv)",
    )
    args = parser.parse_args(argv)

    try:
        rainfall = pd.read_csv(args.openmeteo_csv)
        baseline = pd.read_csv(args.chirps_csv)
        summary = run(rainfall, baseline)
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    print(summary)
    return summary


if __name__ == "__main__":
    main()
