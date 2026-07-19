"""Unit test fondasi untuk src/db/models.py (SPEC.md Bagian 5.2 urutan 1).

Memakai SQLite in-memory (bukan PostGIS) hanya untuk memverifikasi metadata
schema valid dan bisa di-create — bukan pengganti tes integrasi PostGIS asli.
"""

from sqlalchemy import create_engine, inspect

from src.db.models import Base, PipelineLog


def test_pipeline_logs_has_required_columns():
    columns = {c.name for c in PipelineLog.__table__.columns}
    # Kolom wajib sesuai SPEC.md Bagian 5.3 poin 3.
    assert {"timestamp", "pipeline_name", "jumlah_temuan", "status"} <= columns


def test_all_tables_registered_in_metadata():
    expected = {
        "pipeline_logs",
        "road_errors",
        "poi_anomalies",
        "weather_risk_grid",
        "aggregated_findings",
    }
    assert expected <= set(Base.metadata.tables.keys())


def test_non_geometry_tables_create_on_sqlite():
    # road_errors/poi_anomalies/weather_risk_grid pakai tipe Geometry yang
    # butuh ekstensi PostGIS asli, jadi hanya tabel non-geometri yang diuji
    # di sini. Skema PostGIS penuh divalidasi manual saat Fase 0 langkah 2.
    engine = create_engine("sqlite:///:memory:")
    PipelineLog.__table__.create(bind=engine)
    assert inspect(engine).has_table("pipeline_logs")
