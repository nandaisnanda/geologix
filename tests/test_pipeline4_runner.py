"""Unit test runner Pipeline 4 — perakitan input dari temuan P1/P2 (SPEC P4)."""

import numpy as np
import pandas as pd
import pytest

from src.pipeline_4_aggregator import __main__ as runner


def _road_df():
    # id 1 & 3 = temuan sama (node 111) dari 2 run validasi -> dedupe ambil id 3.
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "osm_node_id": [111, 222, 111],
            "osm_way_id": [None, None, None],
            "error_type": ["dangling_node", "oneway_inconsistency", "dangling_node"],
            "severity": ["medium", "high", "medium"],
            "lon": [106.80, 106.81, 106.80],
            "lat": [-6.20, -6.21, -6.20],
            "detected_at": pd.to_datetime(
                ["2026-07-19 01:00", "2026-07-19 01:00", "2026-07-19 02:00"]
            ),
        }
    )


def _poi_df():
    return pd.DataFrame(
        {
            "id": [7],
            "osm_poi_id": [901],
            "confidence_score": [0.5],
            "lon": [106.83],
            "lat": [-6.19],
            "detected_at": pd.to_datetime(["2026-07-19 01:30"]),
        }
    )


@pytest.fixture()
def db_sintetis(monkeypatch):
    frames = {"road_errors": _road_df(), "poi_anomalies": _poi_df()}
    monkeypatch.setattr(
        runner.pd, "read_sql",
        lambda query, engine: frames[
            "road_errors" if "road_errors" in str(query) else "poi_anomalies"
        ].copy(),
    )
    return frames


def test_load_findings_dedupe_mapping_severity_dan_ease(db_sintetis):
    df = runner.load_findings(engine=None)

    # Dedupe: node 111 sekali saja, deteksi terbaru (id 3) yang dipakai.
    assert len(df) == 3
    road = df[df["source_pipeline"] == "road_errors"]
    assert sorted(road["source_id"]) == [2, 3]
    # Mapping severity: medium=2, high=3; P2 = 1 + 2*0.5 = 2 (skala sama).
    assert dict(zip(df["source_id"], df["severity"])) == {3: 2.0, 2: 3.0, 7: 2.0}
    # Ease per jenis error (keputusan proyek).
    assert dict(zip(df["source_id"], df["ease_of_fix"])) == {3: 4.0, 2: 3.0, 7: 5.0}


def test_load_findings_severity_tak_dikenal_ditolak(db_sintetis):
    # Baris index 1 (id 2) lolos dedupe — validasi memang setelah dedupe
    # (hanya baris yang dipakai yang dicek).
    db_sintetis["road_errors"].loc[1, "severity"] = "parah_banget"
    with pytest.raises(ValueError, match="tak dikenal"):
        runner.load_findings(engine=None)


def test_main_buang_temuan_tanpa_populasi_lalu_run(db_sintetis, monkeypatch):
    monkeypatch.setattr(runner, "get_engine", lambda: None)
    # Titik pertama (id 3, lon 106.80) tanpa data populasi -> NaN -> dibuang.
    monkeypatch.setattr(
        runner, "sample_density",
        lambda lons, lats: np.where(np.asarray(lons) == 106.80, np.nan, 12000.0),
    )
    diterima = {}
    monkeypatch.setattr(
        runner, "run",
        lambda df, engine=None: diterima.update(df=df) or {"findings": len(df)},
    )

    summary = runner.main()

    assert summary["dropped_no_population"] == 1
    assert summary["findings"] == 2
    assert not diterima["df"]["population_density"].isna().any()
    assert 3 not in set(diterima["df"]["source_id"])
