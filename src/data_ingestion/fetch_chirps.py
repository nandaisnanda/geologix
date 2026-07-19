"""Tarik histori curah hujan CHIRPS untuk baseline Pipeline 3 — Weather-Risk.

SPEC.md Bagian 6 (sumber "Curah hujan historis", CHIRPS) dan Bagian 2
Pipeline 3 (baseline riwayat rawan banjir dari CHIRPS historis 5 tahun).
Output modul ini (``rainfall_hist_mm`` per sel H3) adalah input Getis-Ord Gi*
(Bagian 3.4) untuk hotspot historis; z-score-nya lalu jadi kriteria kedua
di normalisasi (3.1) + WLC (3.3). Khusus data historis; real-time ditangani
terpisah oleh ``fetch_openmeteo.py``.

Sumber & keputusan akses (verifikasi 2026-07-19):
- CHIRPS v2.0 global annual GeoTIFF, resolusi 0.05 derajat (~5,5 km),
  ``chirps-v2.0.<tahun>.tif`` di data.chc.ucsb.edu (config.CHIRPS_BASE_URL).
- File .tif polos + server dukung HTTP range -> dibaca REMOTE via GDAL
  ``/vsicurl/`` hanya pada koordinat sel Jabodetabek (ratusan KB per tahun,
  bukan download 57MB/file). Fallback: kalau baca remote gagal, download
  penuh ke ``data/raw/chirps/`` (cache idempotent) lalu baca lokal.
- Jendela baseline: 2020-2024 (5 tahun penuh terakhir yang tersedia —
  CHIRPS final terbit dengan lag; annual 2025 belum ada per 2026-07).
- Metrik baseline (keputusan proyek, SPEC tidak merinci): rata-rata total
  hujan TAHUNAN 5 tahun per sel. Pola spasial (gradien orografis Bogor vs
  pesisir Jakarta) itulah yang diuji signifikansinya oleh Gi*; resolusi
  temporal lebih halus tidak mengubah rata-rata.
- Nodata CHIRPS (-9999) -> NaN, dirata-rata dengan nanmean per sel.

Alur: grid H3 (cache h3_grid) -> sample nilai annual di pusat sel per tahun
-> rata-rata -> ``data/raw/chirps_baseline.csv`` + log ``pipeline_logs``
(SPEC.md Bagian 5.3).
"""

import argparse

import numpy as np
import pandas as pd
import rasterio
import requests

from src import config
from src.data_ingestion.fetch_openmeteo import load_grid
from src.db.writer import log_pipeline_run

PIPELINE_NAME = "chirps_ingestion"

# 5 tahun penuh terakhir yang tersedia (lihat docstring).
BASELINE_YEARS = tuple(range(2020, 2025))
CHIRPS_CACHE_DIR = config.RAW_DATA_DIR / "chirps"
BASELINE_OUTPUT_PATH = config.RAW_DATA_DIR / "chirps_baseline.csv"


def annual_url(year: int) -> str:
    return f"{config.CHIRPS_BASE_URL}/chirps-v2.0.{year}.tif"


def local_annual_path(year: int):
    return CHIRPS_CACHE_DIR / f"chirps-v2.0.{year}.tif"


def download_annual(year: int):
    """Fallback: download file annual penuh ke cache lokal (idempotent)."""
    path = local_annual_path(year)
    if path.exists():
        return path
    CHIRPS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with requests.get(annual_url(year), stream=True, timeout=600) as resp:
        resp.raise_for_status()
        tmp = path.with_suffix(path.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(path)
    return path


def sample_tif(tif_path, lats, lngs) -> np.ndarray:
    """Nilai raster di tiap koordinat (rasterio sample pakai x=lng, y=lat).

    Nodata (CHIRPS: -9999) -> NaN.
    """
    with rasterio.open(tif_path) as ds:
        values = np.array(
            [v[0] for v in ds.sample(zip(lngs, lats))], dtype=float
        )
        if ds.nodata is not None:
            values[values == ds.nodata] = np.nan
    return values


def sample_year(year: int, lats, lngs, tif_path=None) -> np.ndarray:
    """Sample 1 tahun: cache lokal kalau ada -> remote /vsicurl/ -> fallback download."""
    if tif_path is not None:
        return sample_tif(tif_path, lats, lngs)
    local = local_annual_path(year)
    if local.exists():
        return sample_tif(local, lats, lngs)
    try:
        return sample_tif(f"/vsicurl/{annual_url(year)}", lats, lngs)
    except rasterio.errors.RasterioIOError:
        return sample_tif(download_annual(year), lats, lngs)


def build_baseline(grid: pd.DataFrame, years=BASELINE_YEARS) -> pd.DataFrame:
    """Rata-rata hujan tahunan (mm/tahun) per sel H3 selama ``years``."""
    lats, lngs = list(grid["lat"]), list(grid["lng"])
    per_year = np.column_stack([sample_year(y, lats, lngs) for y in years])
    out = grid[["h3_index", "lat", "lng"]].reset_index(drop=True).copy()
    out["rainfall_hist_mm"] = np.nanmean(per_year, axis=1)
    out["n_years_valid"] = np.sum(~np.isnan(per_year), axis=1)
    return out


def main(output_path=None, years=BASELINE_YEARS) -> int:
    """Bangun baseline CHIRPS + simpan CSV + log. Return jumlah sel."""
    output_path = output_path or BASELINE_OUTPUT_PATH
    try:
        grid = load_grid()
        baseline = build_baseline(grid, years=years)
        baseline.to_csv(output_path, index=False)
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    log_pipeline_run(
        PIPELINE_NAME,
        len(baseline),
        "success",
        detail=(
            f"cells={len(baseline)} years={years[0]}-{years[-1]} "
            f"hist_mean_mm={baseline['rainfall_hist_mm'].mean():.0f} "
            f"-> {output_path.name}"
        ),
    )
    return len(baseline)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bangun baseline historis CHIRPS per grid H3 (SPEC P3)"
    )
    parser.parse_args()
    n = main()
    print(f"Baseline CHIRPS tersimpan: {n} sel -> {BASELINE_OUTPUT_PATH}")
