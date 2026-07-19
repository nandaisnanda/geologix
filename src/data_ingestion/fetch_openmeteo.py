"""Tarik curah hujan real-time Open-Meteo untuk Pipeline 3 — Weather-Risk Overlay.

SPEC.md Bagian 6 (sumber "Curah hujan real-time", update per jam) dan Bagian 2
Pipeline 3 (tarik data Open-Meteo tiap jam -> overlay ke grid H3). Nilai
``rainfall_mm`` per sel adalah kriteria input untuk normalisasi Min-Max
(Bagian 3.1) sebelum digabung WLC (Bagian 3.3). File ini khusus data
real-time; histori 5 tahun (baseline Gi*, Bagian 3.4) ditangani terpisah oleh
``fetch_chirps.py``.

Alur (idempotent, aman dijalankan per jam):
1. Grid H3 dari ``data/raw/h3_grid_jabodetabek.gpkg`` (cache statis; kalau
   belum ada, dibangun sekali via ``h3_grid.main()``).
2. Sampling per PUSAT sel H3 (kolom ``lat``/``lng`` grid) — resolusi grid
   (res 7, ~1,2 km) lebih halus dari model cuaca Open-Meteo (~11-25 km),
   jadi 1 titik pusat per sel sudah mewakili selnya.
3. Request batch (``BATCH_SIZE`` koordinat per call, format multi-lokasi
   ``latitude=a,b,c&longitude=...``) ke endpoint ``config.OPEN_METEO_BASE_URL``
   dengan ``current=precipitation`` — nilai presipitasi (mm) 1 jam terakhir.
4. Simpan snapshot ``data/raw/openmeteo_latest.csv`` (overwrite tiap run;
   riwayat antar-jam hidup di tabel ``weather_risk_grid``, bukan di CSV) +
   log run ke ``pipeline_logs`` (SPEC.md Bagian 5.3).
"""

import argparse
import time
from datetime import datetime, timezone

import geopandas as gpd
import pandas as pd
import requests

from src import config
from src.db.writer import log_pipeline_run
from src.pipeline_3_weather_risk import h3_grid

PIPELINE_NAME = "openmeteo_ingestion"

RAINFALL_OUTPUT_PATH = config.RAW_DATA_DIR / "openmeteo_latest.csv"
# Jumlah koordinat per request multi-lokasi. Free tier Open-Meteo menghitung
# tiap LOKASI sebagai 1 unit call (bukan per request): 1.079 sel res 7 =
# ~1.079 unit/run. PERHATIAN CI Fase 4: cron per jam = ~26k unit/hari,
# melebihi budget harian 10.000 unit — wajib turunkan frekuensi cron atau
# subset grid. Run manual Fase 3 aman.
BATCH_SIZE = 100
# Limit per menit ~600 unit -> maksimal 6 batch(100)/menit; jeda 10 dtk
# antar-batch menjaga run tetap di bawah limit (terverifikasi: burst tanpa
# jeda kena HTTP 429).
BATCH_PAUSE_S = 10
RETRY_MAX = 4  # retry HTTP 429 + timeout/gagal koneksi, backoff RETRY_BACKOFF_S
RETRY_BACKOFF_S = 30
REQUEST_TIMEOUT_S = 60


def load_grid() -> gpd.GeoDataFrame:
    """Grid H3 dari cache GPKG; bangun sekali (h3_grid.main) kalau belum ada."""
    if not h3_grid.GRID_OUTPUT_PATH.exists():
        h3_grid.main()
    return gpd.read_file(h3_grid.GRID_OUTPUT_PATH, layer=h3_grid.GRID_LAYER)


def _parse_locations(payload) -> list[dict]:
    """Response Open-Meteo: list utk multi-lokasi, dict tunggal utk 1 lokasi."""
    return payload if isinstance(payload, list) else [payload]


def _get_batch(params: dict) -> requests.Response:
    """GET dengan retry untuk dua mode gagal transient:
    - HTTP 429 (limit per menit ~600 unit lokasi, terverifikasi empiris);
    - timeout/gagal koneksi (Open-Meteo kadang lambat merespons IP shared
      GitHub Actions — insiden ReadTimeout run CI pertama, log id 25).
    Error lain (4xx/5xx non-429) tetap langsung raise.
    """
    for attempt in range(RETRY_MAX + 1):
        try:
            resp = requests.get(
                config.OPEN_METEO_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_S
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt < RETRY_MAX:
                time.sleep(RETRY_BACKOFF_S)
                continue
            raise
        if resp.status_code == 429 and attempt < RETRY_MAX:
            time.sleep(RETRY_BACKOFF_S)
            continue
        resp.raise_for_status()
        return resp
    raise AssertionError("unreachable")  # loop selalu return/raise


def fetch_rainfall(lats: list[float], lngs: list[float]) -> pd.DataFrame:
    """Presipitasi (mm, 1 jam terakhir) per koordinat, urutan input dipertahankan.

    Return DataFrame kolom ``rainfall_mm`` (float) dan ``weather_time``
    (timestamp jam data dari API, string ISO UTC).
    """
    if len(lats) != len(lngs):
        raise ValueError("lats dan lngs harus sama panjang")
    rows: list[dict] = []
    for start in range(0, len(lats), BATCH_SIZE):
        if start > 0:
            time.sleep(BATCH_PAUSE_S)
        batch_lat = lats[start : start + BATCH_SIZE]
        batch_lng = lngs[start : start + BATCH_SIZE]
        resp = _get_batch(
            {
                "latitude": ",".join(f"{v:.4f}" for v in batch_lat),
                "longitude": ",".join(f"{v:.4f}" for v in batch_lng),
                "current": "precipitation",
                "timezone": "UTC",
            }
        )
        locations = _parse_locations(resp.json())
        if len(locations) != len(batch_lat):
            raise ValueError(
                f"Open-Meteo mengembalikan {len(locations)} lokasi "
                f"untuk {len(batch_lat)} koordinat"
            )
        for loc in locations:
            rows.append(
                {
                    "rainfall_mm": float(loc["current"]["precipitation"]),
                    "weather_time": loc["current"]["time"],
                }
            )
    return pd.DataFrame(rows)


def fetch_rainfall_for_grid(grid: gpd.GeoDataFrame | pd.DataFrame) -> pd.DataFrame:
    """Curah hujan per sel H3: kolom h3_index, lat, lng, rainfall_mm, weather_time."""
    rainfall = fetch_rainfall(list(grid["lat"]), list(grid["lng"]))
    out = grid[["h3_index", "lat", "lng"]].reset_index(drop=True)
    return pd.concat([out, rainfall], axis=1)


def main(output_path=None) -> int:
    """Fetch hujan utk seluruh grid + simpan CSV + log. Return jumlah sel."""
    output_path = output_path or RAINFALL_OUTPUT_PATH
    try:
        grid = load_grid()
        hasil = fetch_rainfall_for_grid(grid)
        hasil["fetched_at"] = datetime.now(timezone.utc).isoformat()
        hasil.to_csv(output_path, index=False)
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    log_pipeline_run(
        PIPELINE_NAME,
        len(hasil),
        "success",
        detail=(
            f"cells={len(hasil)} weather_time={hasil['weather_time'].iloc[0]} "
            f"rain_max_mm={hasil['rainfall_mm'].max():.2f} -> {output_path.name}"
        ),
    )
    return len(hasil)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch curah hujan Open-Meteo per grid H3 (SPEC P3)"
    )
    parser.parse_args()
    n = main()
    print(f"Curah hujan tersimpan: {n} sel -> {RAINFALL_OUTPUT_PATH}")
