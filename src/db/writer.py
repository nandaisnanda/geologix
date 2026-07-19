"""Penulis hasil pipeline ke database — SPEC.md Bagian 5.3 poin 3.

Setiap run pipeline WAJIB dicatat ke tabel `pipeline_logs` (kolom: timestamp,
pipeline_name, jumlah_temuan, status) sebagai bukti sistem otomatis dan bahan
baku Fase 2 ML.
"""

from geoalchemy2 import WKTElement
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src import config
from src.db.models import (
    AggregatedFinding,
    PipelineLog,
    PoiAnomaly,
    RoadError,
    WeatherRiskGrid,
)


def get_engine(database_url: str | None = None) -> Engine:
    url = database_url or config.DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL kosong — set di .env (lihat .env.example)")
    return create_engine(url)


def log_pipeline_run(
    pipeline_name: str,
    jumlah_temuan: int,
    status: str,
    detail: str | None = None,
    engine: Engine | None = None,
) -> int:
    """Catat satu run pipeline ke `pipeline_logs`. Return id baris log."""
    engine = engine or get_engine()
    with Session(engine) as session:
        log = PipelineLog(
            pipeline_name=pipeline_name,
            jumlah_temuan=jumlah_temuan,
            status=status,
            detail=detail,
        )
        session.add(log)
        session.commit()
        return log.id


def finding_to_road_error(finding: dict) -> RoadError:
    """Konversi dict temuan Pipeline 1 (Bagian 3.1-3.3) -> baris ``road_errors``.

    Kunci wajib di dict: ``error_type``, ``severity``, ``lon``, ``lat``;
    opsional: ``osm_node_id``, ``osm_way_id``. Geometri POINT SRID 4326.
    """
    return RoadError(
        osm_node_id=finding.get("osm_node_id"),
        osm_way_id=finding.get("osm_way_id"),
        error_type=finding["error_type"],
        severity=finding["severity"],
        geom=WKTElement(f"POINT({finding['lon']} {finding['lat']})", srid=4326),
    )


def save_road_errors(findings: list[dict], engine: Engine | None = None) -> int:
    """Simpan temuan Pipeline 1 ke tabel ``road_errors``. Return jumlah baris."""
    if not findings:
        return 0
    engine = engine or get_engine()
    with Session(engine) as session:
        session.add_all(finding_to_road_error(f) for f in findings)
        session.commit()
    return len(findings)


def finding_to_poi_anomaly(finding: dict) -> PoiAnomaly:
    """Konversi dict temuan Pipeline 2 (Bagian 2.1-2.2) -> baris ``poi_anomalies``.

    Kunci wajib di dict: ``distance_to_road_m``, ``confidence_score``, ``lon``,
    ``lat``; opsional: ``osm_poi_id``, ``poi_category``. Geometri POINT SRID 4326.
    """
    return PoiAnomaly(
        osm_poi_id=finding.get("osm_poi_id"),
        poi_category=finding.get("poi_category"),
        distance_to_road_m=finding["distance_to_road_m"],
        confidence_score=finding["confidence_score"],
        geom=WKTElement(f"POINT({finding['lon']} {finding['lat']})", srid=4326),
    )


def save_poi_anomalies(findings: list[dict], engine: Engine | None = None) -> int:
    """Simpan temuan Pipeline 2 ke tabel ``poi_anomalies``. Return jumlah baris."""
    if not findings:
        return 0
    engine = engine or get_engine()
    with Session(engine) as session:
        session.add_all(finding_to_poi_anomaly(f) for f in findings)
        session.commit()
    return len(findings)


def row_to_weather_risk(row: dict) -> WeatherRiskGrid:
    """Konversi dict hasil Pipeline 3 (Bagian 3.1-3.4) -> baris ``weather_risk_grid``.

    Kunci wajib di dict: ``h3_index``, ``geom_wkt`` (POLYGON hexagon sel),
    ``risk_index``; opsional: ``rainfall_realtime_mm``, ``hotspot_gi_star_z``.
    Geometri POLYGON SRID 4326.
    """
    return WeatherRiskGrid(
        h3_index=row["h3_index"],
        rainfall_realtime_mm=row.get("rainfall_realtime_mm"),
        hotspot_gi_star_z=row.get("hotspot_gi_star_z"),
        risk_index=row["risk_index"],
        geom=WKTElement(row["geom_wkt"], srid=4326),
    )


def save_weather_risk_grid(rows: list[dict], engine: Engine | None = None) -> int:
    """Simpan hasil Pipeline 3 ke tabel ``weather_risk_grid``. Return jumlah baris."""
    if not rows:
        return 0
    engine = engine or get_engine()
    with Session(engine) as session:
        session.add_all(row_to_weather_risk(r) for r in rows)
        session.commit()
    return len(rows)


def row_to_aggregated_finding(row: dict) -> AggregatedFinding:
    """Konversi dict hasil Pipeline 4 (Bagian 3.2-3.3) -> baris ``aggregated_findings``.

    Kunci wajib di dict: ``source_pipeline``, ``source_id`` (rujukan longgar ke
    baris asal di road_errors/poi_anomalies/weather_risk_grid), ``priority_score``.
    """
    return AggregatedFinding(
        source_pipeline=row["source_pipeline"],
        source_id=row["source_id"],
        priority_score=row["priority_score"],
    )


def save_aggregated_findings(rows: list[dict], engine: Engine | None = None) -> int:
    """Simpan hasil Pipeline 4 ke tabel ``aggregated_findings``. Return jumlah baris."""
    if not rows:
        return 0
    engine = engine or get_engine()
    with Session(engine) as session:
        session.add_all(row_to_aggregated_finding(r) for r in rows)
        session.commit()
    return len(rows)
