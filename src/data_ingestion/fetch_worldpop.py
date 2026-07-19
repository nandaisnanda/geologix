"""Download + sampling WorldPop untuk Pipeline 4 (SPEC.md Bagian 3 Pipeline 4).

Kriteria [1] Pipeline 4 = "kepadatan populasi terdampak (proxy WorldPop)".
Sumber: WorldPop Population Density Indonesia 2020, resolusi 1 km, versi
UN-adjusted (idn_pd_2020_1km_UNadj.tif, ~10MB, lisensi CC BY 4.0) — nilai
piksel = jiwa/km2. GeoTIFF didownload sekali dan di-cache di ``data/raw/``
(idempotent, pola sama dengan ``ensure_shp_zip`` Pipeline 2).

``sample_density(lons, lats)`` membaca nilai raster di titik temuan
(rasterio ``sample``); nodata (laut/luar cakupan, sentinel negatif WorldPop)
dikembalikan sebagai NaN — TIDAK diam-diam 0, supaya keputusan buang/isi
terjadi eksplisit di runner P4 (konsisten prinsip NaN Pipeline 3).

Download dicatat ke ``pipeline_logs`` (SPEC 5.3 poin 3) sebagai
``worldpop_ingestion``; pemakaian sampling per run dicatat oleh runner P4.
"""

import numpy as np
import rasterio
import requests

from src import config
from src.db.writer import log_pipeline_run

PIPELINE_NAME = "worldpop_ingestion"

WORLDPOP_TIF_PATH = config.RAW_DATA_DIR / "idn_pd_2020_1km_UNadj.tif"


def ensure_worldpop_tif(force: bool = False):
    """Download GeoTIFF WorldPop kalau belum ada (idempotent). Return path."""
    if WORLDPOP_TIF_PATH.exists() and not force:
        return WORLDPOP_TIF_PATH
    try:
        with requests.get(config.WORLDPOP_TIF_URL, stream=True, timeout=600) as resp:
            resp.raise_for_status()
            tmp = WORLDPOP_TIF_PATH.with_suffix(".tif.part")
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
            tmp.replace(WORLDPOP_TIF_PATH)
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    size_mb = WORLDPOP_TIF_PATH.stat().st_size / 1e6
    log_pipeline_run(
        PIPELINE_NAME, 0, "success", detail=f"downloaded {size_mb:.1f}MB -> {WORLDPOP_TIF_PATH.name}"
    )
    return WORLDPOP_TIF_PATH


def sample_density(lons, lats, tif_path=None) -> np.ndarray:
    """Kepadatan populasi (jiwa/km2) di tiap titik lon/lat; nodata -> NaN.

    Raster WorldPop ber-CRS EPSG:4326 — koordinat temuan (SRID 4326) bisa
    dipakai langsung tanpa reproyeksi.
    """
    lons = np.asarray(lons, dtype=float)
    lats = np.asarray(lats, dtype=float)
    if lons.shape != lats.shape or lons.ndim != 1:
        raise ValueError("lons dan lats harus array 1D dengan panjang sama")
    tif_path = tif_path or ensure_worldpop_tif()
    with rasterio.open(tif_path) as src:
        values = np.array(
            [v[0] for v in src.sample(zip(lons, lats))], dtype=float
        )
        nodata = src.nodata
    if nodata is not None:
        values[np.isclose(values, nodata)] = np.nan
    # Sentinel WorldPop kadang tak terdaftar sebagai nodata — densitas < 0
    # tidak bermakna fisik, perlakukan sebagai tanpa data.
    values[values < 0] = np.nan
    return values
