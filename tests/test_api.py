"""Unit test src/api/main.py — FastAPI read-only Fase 5 (SPEC.md step 17).

DB uji = SQLite in-memory: tabel dibuat manual (geom sebagai TEXT WKT) dan
fungsi PostGIS ST_X/ST_Y diregister sebagai fungsi Python, supaya SQL teks
produksi bisa dieksekusi apa adanya tanpa PostGIS. Timestamp disimpan string
ISO (separator spasi) — konsisten dengan perbandingan leksikografis SQLite.
"""

import sqlite3
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool

from src.api.main import app, get_db_engine


def _st_x(wkt: str | None) -> float | None:
    return None if wkt is None else float(wkt.split("(")[1].split()[0])


def _st_y(wkt: str | None) -> float | None:
    return None if wkt is None else float(wkt.rstrip(")").split()[-1])


SCHEMA = [
    "CREATE TABLE road_errors (id INTEGER PRIMARY KEY, osm_node_id BIGINT,"
    " osm_way_id BIGINT, error_type TEXT, severity TEXT, geom TEXT,"
    " detected_at TEXT)",
    "CREATE TABLE poi_anomalies (id INTEGER PRIMARY KEY, osm_poi_id BIGINT,"
    " poi_category TEXT, distance_to_road_m REAL, confidence_score REAL,"
    " geom TEXT, detected_at TEXT)",
    "CREATE TABLE weather_risk_grid (id INTEGER PRIMARY KEY, h3_index TEXT,"
    " geom TEXT, rainfall_realtime_mm REAL, hotspot_gi_star_z REAL,"
    " risk_index REAL, computed_at TEXT)",
    "CREATE TABLE aggregated_findings (id INTEGER PRIMARY KEY,"
    " source_pipeline TEXT, source_id INTEGER, priority_score REAL,"
    " computed_at TEXT)",
    "CREATE TABLE pipeline_logs (id INTEGER PRIMARY KEY, timestamp TEXT,"
    " pipeline_name TEXT, jumlah_temuan INTEGER, status TEXT, detail TEXT)",
]

# Dua batch run: 18 Juli (lama) dan 19 Juli (terbaru) — menguji semantik
# snapshot (default = batch terbaru saja; at= mundur ke batch lama).
SEED = [
    # road_errors: batch lama 2 baris, batch baru 2 baris (1 oneway).
    "INSERT INTO road_errors VALUES"
    " (1, 111, NULL, 'dangling_node', 'medium', 'POINT(106.80 -6.20)',"
    "  '2026-07-18 10:00:00'),"
    " (2, 112, NULL, 'dangling_node', 'medium', 'POINT(106.81 -6.21)',"
    "  '2026-07-18 10:00:05'),"
    " (3, 111, NULL, 'dangling_node', 'medium', 'POINT(106.80 -6.20)',"
    "  '2026-07-19 12:00:00'),"
    " (4, NULL, 900, 'oneway_inconsistency', 'high', 'POINT(106.85 -6.25)',"
    "  '2026-07-19 12:01:00')",
    "INSERT INTO poi_anomalies VALUES"
    " (1, 4567890123, 'restaurant', 250.5, 0.8, 'POINT(106.83 -6.19)',"
    "  '2026-07-19 11:00:00'),"
    " (2, 4567890124, 'atm', 60.0, 0.3, 'POINT(106.84 -6.18)',"
    "  '2026-07-19 11:00:10')",
    "INSERT INTO weather_risk_grid VALUES"
    " (1, '87xold', 'POLYGON((0 0,1 0,1 1,0 0))', 0.0, 1.0, 0.10,"
    "  '2026-07-19 06:00:00'),"
    " (2, '87xaaa', 'POLYGON((0 0,1 0,1 1,0 0))', 0.4, 2.1, 0.63,"
    "  '2026-07-19 12:00:00'),"
    " (3, '87xbbb', 'POLYGON((0 0,1 0,1 1,0 0))', 0.0, -0.5, 0.05,"
    "  '2026-07-19 12:00:02')",
    # Baris 1 dan 4 = temuan sama (poi_anomalies/1) dari 2 run P4 berjarak
    # detik (pola checklist 5.4 3x run) — endpoint wajib dedupe, keep terbaru.
    "INSERT INTO aggregated_findings VALUES"
    " (1, 'poi_anomalies', 1, 0.9988, '2026-07-19 13:00:00'),"
    " (2, 'road_errors', 4, 0.9000, '2026-07-19 13:00:01'),"
    " (3, 'road_errors', 3, 0.4197, '2026-07-19 13:00:02'),"
    " (4, 'poi_anomalies', 1, 0.9988, '2026-07-19 13:00:03')",
    "INSERT INTO pipeline_logs VALUES"
    " (1, '2026-07-18 10:05:00', 'pipeline_1_road_qa', 2, 'success', NULL),"
    " (2, '2026-07-19 12:05:00', 'pipeline_1_road_qa', 2, 'success', NULL),"
    " (3, '2026-07-19 12:06:00', 'pipeline_3_weather_risk', 1, 'failed',"
    "  'ReadTimeout')",
]


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _register(dbapi_conn, _record):
        dbapi_conn.create_function("ST_X", 1, _st_x)
        dbapi_conn.create_function("ST_Y", 1, _st_y)

    # Parameter datetime -> string ISO spasi (perbandingan leksikografis valid).
    sqlite3.register_adapter(datetime, lambda d: d.isoformat(sep=" "))

    with engine.begin() as conn:
        for stmt in SCHEMA + SEED:
            conn.execute(text(stmt))

    app.dependency_overrides[get_db_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok"}


def test_road_errors_snapshot_default_hanya_batch_terbaru(client):
    body = client.get("/road-errors").json()
    assert body["meta"]["mode"] == "snapshot"
    assert body["meta"]["total"] == 2
    ids = [item["id"] for item in body["items"]]
    assert ids == [3, 4]  # batch 19 Juli saja, batch 18 Juli tidak ikut
    first = body["items"][0]
    assert first["lon"] == 106.80 and first["lat"] == -6.20
    assert first["error_type"] == "dangling_node"


def test_road_errors_at_mundur_ke_batch_lama(client):
    body = client.get("/road-errors", params={"at": "2026-07-18T23:00:00"}).json()
    assert [item["id"] for item in body["items"]] == [1, 2]


def test_road_errors_filter_error_type_dan_range_eksplisit(client):
    body = client.get(
        "/road-errors",
        params={
            "error_type": "dangling_node",
            "since": "2026-07-01T00:00:00",
            "until": "2026-07-31T00:00:00",
        },
    ).json()
    # Mode range = riwayat penuh: ketiga dangling dari dua batch.
    assert body["meta"]["mode"] == "range"
    assert [item["id"] for item in body["items"]] == [1, 2, 3]


def test_poi_anomalies_min_confidence_urut_confidence(client):
    body = client.get("/poi-anomalies").json()
    # Urut confidence turun: id 1 (0.8) sebelum id 2 (0.3).
    assert [item["id"] for item in body["items"]] == [1, 2]
    body = client.get("/poi-anomalies", params={"min_confidence": 0.5}).json()
    assert [item["id"] for item in body["items"]] == [1]
    assert body["items"][0]["distance_to_road_m"] == 250.5


def test_weather_risk_snapshot_tanpa_geometri_dan_min_risk(client):
    body = client.get("/weather-risk").json()
    # Snapshot 12:00 saja (jendela 15 mnt) — sel 06:00 tidak ikut.
    assert {item["h3_index"] for item in body["items"]} == {"87xaaa", "87xbbb"}
    assert "geom" not in body["items"][0]
    body = client.get("/weather-risk", params={"min_risk": 0.5}).json()
    assert [item["h3_index"] for item in body["items"]] == ["87xaaa"]


def test_aggregated_findings_join_lonlat_urut_prioritas(client):
    body = client.get("/aggregated-findings").json()
    items = body["items"]
    # Dedupe: baris 1 kalah dari baris 4 (temuan sama, computed_at terbaru);
    # total = temuan unik (3), urut priority turun.
    assert body["meta"]["total"] == 3
    assert [item["id"] for item in items] == [4, 2, 3]
    # id 1 dari poi_anomalies -> koordinat POI + error_type 'poi_anomaly'.
    assert items[0]["error_type"] == "poi_anomaly"
    assert items[0]["lon"] == 106.83 and items[0]["lat"] == -6.19
    # id 2 dari road_errors id 4 (oneway).
    assert items[1]["error_type"] == "oneway_inconsistency"
    assert items[1]["lon"] == 106.85


def test_pipeline_logs_terbaru_dulu_dan_filter_status(client):
    body = client.get("/pipeline-logs").json()
    assert body["meta"]["total"] == 3
    assert [item["id"] for item in body["items"]] == [3, 2, 1]
    body = client.get("/pipeline-logs", params={"status": "failed"}).json()
    assert [item["detail"] for item in body["items"]] == ["ReadTimeout"]


def test_tabel_kosong_balas_snapshot_kosong(client):
    # at sebelum data pertama -> anchor None -> items kosong, bukan error.
    body = client.get("/road-errors", params={"at": "2020-01-01T00:00:00"}).json()
    assert body == {
        "meta": {"mode": "snapshot", "start": None, "end": None, "total": 0},
        "items": [],
    }


def test_limit_offset_paginasi(client):
    body = client.get("/road-errors", params={"limit": 1}).json()
    assert body["meta"]["total"] == 2 and len(body["items"]) == 1
    body2 = client.get("/road-errors", params={"limit": 1, "offset": 1}).json()
    assert body2["items"][0]["id"] != body["items"][0]["id"]
