"""Unit test fetch_chirps.py — SPEC.md Bagian 6 (baseline historis CHIRPS P3)."""

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from src.data_ingestion import fetch_chirps

NODATA = -9999.0


def make_tif(path, fill_value, nodata_cell=False):
    """Raster 4x4 (0.5 derajat/piksel) area 106-108 BT, -8 sampai -6 LS."""
    data = np.full((4, 4), fill_value, dtype="float32")
    if nodata_cell:
        data[0, 0] = NODATA  # piksel kiri-atas: lng 106-106.5, lat -6.5..-6
    with rasterio.open(
        path, "w", driver="GTiff", height=4, width=4, count=1,
        dtype="float32", crs="EPSG:4326",
        transform=from_origin(106.0, -6.0, 0.5, 0.5), nodata=NODATA,
    ) as ds:
        ds.write(data, 1)
    return path


def test_sample_tif_nilai_dan_nodata_jadi_nan(tmp_path):
    tif = make_tif(tmp_path / "a.tif", 1500.0, nodata_cell=True)

    values = fetch_chirps.sample_tif(tif, lats=[-6.25, -7.0], lngs=[106.25, 107.0])

    assert np.isnan(values[0])  # jatuh di piksel nodata
    assert values[1] == 1500.0


def test_build_baseline_rata_rata_antar_tahun(tmp_path, monkeypatch):
    tifs = {
        2020: make_tif(tmp_path / "2020.tif", 1000.0),
        2021: make_tif(tmp_path / "2021.tif", 2000.0, nodata_cell=True),
    }
    monkeypatch.setattr(
        fetch_chirps, "sample_year",
        lambda year, lats, lngs, tif_path=None: fetch_chirps.sample_tif(
            tifs[year], lats, lngs
        ),
    )
    grid = pd.DataFrame(
        {"h3_index": ["a", "b"], "lat": [-6.25, -7.0], "lng": [106.25, 107.0]}
    )

    baseline = fetch_chirps.build_baseline(grid, years=(2020, 2021))

    # Sel b: mean(1000, 2000) = 1500, 2 tahun valid.
    b = baseline[baseline["h3_index"] == "b"].iloc[0]
    assert b["rainfall_hist_mm"] == 1500.0 and b["n_years_valid"] == 2
    # Sel a: 2021 nodata -> nanmean = 1000, hanya 1 tahun valid.
    a = baseline[baseline["h3_index"] == "a"].iloc[0]
    assert a["rainfall_hist_mm"] == 1000.0 and a["n_years_valid"] == 1


def test_sample_year_pakai_cache_lokal_tanpa_network(tmp_path, monkeypatch):
    tif = make_tif(tmp_path / "chirps-v2.0.2020.tif", 800.0)
    monkeypatch.setattr(fetch_chirps, "CHIRPS_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        fetch_chirps.requests, "get",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("tidak boleh download")),
    )

    values = fetch_chirps.sample_year(2020, lats=[-7.0], lngs=[107.0])

    assert values[0] == 800.0


def test_main_simpan_csv_dan_log_pipeline(tmp_path, monkeypatch):
    logged = []
    monkeypatch.setattr(
        fetch_chirps, "log_pipeline_run",
        lambda name, n, status, detail=None: logged.append((name, n, status, detail)),
    )
    tif = make_tif(tmp_path / "x.tif", 1200.0)
    monkeypatch.setattr(
        fetch_chirps, "sample_year",
        lambda year, lats, lngs, tif_path=None: fetch_chirps.sample_tif(tif, lats, lngs),
    )
    grid = pd.DataFrame({"h3_index": ["a"], "lat": [-7.0], "lng": [107.0]})
    monkeypatch.setattr(fetch_chirps, "load_grid", lambda: grid)
    out = tmp_path / "baseline_test.csv"

    n = fetch_chirps.main(output_path=out, years=(2020, 2021))

    assert n == 1 and out.exists()
    saved = pd.read_csv(out)
    assert saved.loc[0, "rainfall_hist_mm"] == 1200.0
    assert logged == [
        ("chirps_ingestion", 1, "success",
         "cells=1 years=2020-2021 hist_mean_mm=1200 -> baseline_test.csv"),
    ]


def test_main_gagal_log_failed_dan_raise(monkeypatch):
    logged = []
    monkeypatch.setattr(
        fetch_chirps, "log_pipeline_run",
        lambda name, n, status, detail=None: logged.append((name, n, status, detail)),
    )

    def boom():
        raise RuntimeError("grid hilang")

    monkeypatch.setattr(fetch_chirps, "load_grid", boom)

    with pytest.raises(RuntimeError, match="grid hilang"):
        fetch_chirps.main(output_path=None)
    assert logged == [("chirps_ingestion", 0, "failed", "RuntimeError: grid hilang")]
