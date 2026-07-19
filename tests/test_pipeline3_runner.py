"""Unit test runner Pipeline 3 — orkestrasi Gi* + Min-Max + AHP + WLC (SPEC P3)."""

import h3
import numpy as np
import pandas as pd
import pytest

from src.pipeline_3_weather_risk import __main__ as runner

CENTER = h3.latlng_to_cell(-6.175, 106.827, 7)
CELLS = sorted(h3.grid_disk(CENTER, 2))  # 19 sel nyata res 7


@pytest.fixture()
def tangkapan(monkeypatch):
    saved, logged = [], []
    monkeypatch.setattr(
        runner, "save_weather_risk_grid",
        lambda rows, engine=None: (saved.extend(rows), len(rows))[1],
    )
    monkeypatch.setattr(
        runner, "log_pipeline_run",
        lambda name, n, status, detail=None, engine=None: logged.append(
            (name, n, status, detail)
        ),
    )
    return saved, logged


def _rainfall(cells):
    return pd.DataFrame(
        {
            "h3_index": cells,
            "rainfall_mm": np.linspace(0.0, 4.0, len(cells)),
            "weather_time": "2026-07-19T07:00",
        }
    )


def _baseline(cells, klaster_tinggi=True):
    inti = set(h3.grid_disk(CENTER, 1))
    hist = [4000.0 if (c in inti and klaster_tinggi) else 1500.0 for c in cells]
    return pd.DataFrame({"h3_index": cells, "rainfall_hist_mm": hist})


def test_run_risk_index_valid_dan_tersimpan(tangkapan):
    saved, logged = tangkapan

    summary = runner.run(_rainfall(CELLS), _baseline(CELLS))

    assert summary["cells"] == len(CELLS) and summary["dropped"] == 0
    # Bobot AHP P3: [2/3, 1/3], CR 2x2 = 0.
    assert summary["weights"] == [0.6667, 0.3333] and summary["cr"] == 0.0
    # RiskIndex hasil WLC atas kriteria ternormalisasi -> wajib [0, 1].
    assert 0.0 <= summary["risk_min"] <= summary["risk_max"] <= 1.0
    # Klaster baseline tinggi di pusat -> ada hotspot signifikan.
    assert summary["hotspots"] >= 1
    assert len(saved) == len(CELLS)
    contoh = saved[0]
    assert contoh["geom_wkt"].startswith("POLYGON ((")
    assert set(contoh) == {
        "h3_index", "geom_wkt", "rainfall_realtime_mm",
        "hotspot_gi_star_z", "risk_index",
    }
    # Log: jumlah_temuan = jumlah hotspot, bukan jumlah sel.
    name, n, status, detail = logged[0]
    assert name == "pipeline_3_weather_risk" and status == "success"
    assert n == summary["hotspots"]
    assert f"cells={len(CELLS)}" in detail and "weather_time=2026-07-19T07:00" in detail


def test_run_sel_nan_baseline_dibuang_sebelum_gi_star(tangkapan):
    saved, _ = tangkapan
    baseline = _baseline(CELLS)
    baseline.loc[baseline["h3_index"] == CELLS[0], "rainfall_hist_mm"] = np.nan

    summary = runner.run(_rainfall(CELLS), baseline)

    # Sel NaN dibuang (bukan diam-diam dianggap 0) — Gi* jalan tanpa NaN.
    assert summary["cells"] == len(CELLS) - 1
    assert summary["dropped"] == 1
    assert all(r["h3_index"] != CELLS[0] for r in saved)


def test_run_tanpa_irisan_data_raise(tangkapan):
    rainfall = _rainfall(CELLS[:3])
    baseline = pd.DataFrame({"h3_index": ["zzz"], "rainfall_hist_mm": [1000.0]})
    with pytest.raises(ValueError, match="tidak ada sel"):
        runner.run(rainfall, baseline)
