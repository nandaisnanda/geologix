"""Unit test db/writer.py — SPEC.md Bagian 5.3 poin 3 (log run ke pipeline_logs)."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.db.models import Base, PipelineLog
from src.db.writer import (
    finding_to_poi_anomaly,
    finding_to_road_error,
    get_engine,
    log_pipeline_run,
    row_to_weather_risk,
    save_poi_anomalies,
    save_road_errors,
    save_weather_risk_grid,
)


@pytest.fixture
def sqlite_engine():
    # PipelineLog tidak punya kolom geometri, jadi bisa diuji di SQLite in-memory.
    engine = create_engine("sqlite://")
    PipelineLog.__table__.create(engine)
    return engine


def test_log_pipeline_run_tersimpan(sqlite_engine):
    log_id = log_pipeline_run(
        "pipeline_1_road_qa", 42, "success", detail="uji", engine=sqlite_engine
    )
    with Session(sqlite_engine) as session:
        row = session.execute(select(PipelineLog)).scalar_one()
        assert row.id == log_id
        assert row.pipeline_name == "pipeline_1_road_qa"
        assert row.jumlah_temuan == 42
        assert row.status == "success"
        assert row.timestamp is not None


def test_finding_to_road_error_geometri_wkt_srid4326():
    row = finding_to_road_error(
        {
            "osm_node_id": 123,
            "error_type": "dangling_node",
            "severity": "medium",
            "lon": 106.83,
            "lat": -6.19,
        }
    )
    assert row.osm_node_id == 123
    assert row.osm_way_id is None
    assert row.error_type == "dangling_node"
    assert row.geom.srid == 4326
    assert row.geom.data == "POINT(106.83 -6.19)"


def test_save_road_errors_list_kosong_tanpa_koneksi_db():
    # Tidak boleh menyentuh engine/DB kalau tidak ada temuan.
    assert save_road_errors([], engine=None) == 0


def test_finding_to_poi_anomaly_geometri_wkt_srid4326():
    row = finding_to_poi_anomaly(
        {
            "osm_poi_id": 4567890123,  # > 2^31: kolom wajib BigInteger
            "poi_category": "restaurant",
            "distance_to_road_m": 250.5,
            "confidence_score": 0.8,
            "lon": 106.83,
            "lat": -6.19,
        }
    )
    assert row.osm_poi_id == 4567890123
    assert row.poi_category == "restaurant"
    assert row.distance_to_road_m == 250.5
    assert row.confidence_score == 0.8
    assert row.geom.srid == 4326
    assert row.geom.data == "POINT(106.83 -6.19)"


def test_save_poi_anomalies_list_kosong_tanpa_koneksi_db():
    assert save_poi_anomalies([], engine=None) == 0


def test_row_to_weather_risk_geometri_polygon_srid4326():
    wkt = "POLYGON((106.8 -6.2, 106.81 -6.2, 106.81 -6.19, 106.8 -6.2))"
    row = row_to_weather_risk(
        {
            "h3_index": "878c10000ffffff",
            "geom_wkt": wkt,
            "rainfall_realtime_mm": 0.4,
            "hotspot_gi_star_z": 2.1,
            "risk_index": 0.63,
        }
    )
    assert row.h3_index == "878c10000ffffff"
    assert row.rainfall_realtime_mm == 0.4
    assert row.hotspot_gi_star_z == 2.1
    assert row.risk_index == 0.63
    assert row.geom.srid == 4326
    assert row.geom.data == wkt


def test_save_weather_risk_grid_list_kosong_tanpa_koneksi_db():
    assert save_weather_risk_grid([], engine=None) == 0


def test_get_engine_tanpa_database_url(monkeypatch):
    from src import config

    monkeypatch.setattr(config, "DATABASE_URL", "")
    with pytest.raises(RuntimeError, match="DATABASE_URL kosong"):
        get_engine()
