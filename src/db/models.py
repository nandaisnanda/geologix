"""Schema PostgreSQL+PostGIS untuk GeoLogix AI.

Fase 0 (SPEC.md Bagian 5.2 urutan 1). Tabel:
- PipelineLog: log riwayat tiap run pipeline (Bagian 5.3 poin 3, bukti sistem otomatis).
- RoadError: hasil Pipeline 1 - Road Network QA (Bagian 3.1-3.3).
- PoiAnomaly: hasil Pipeline 2 - POI Validation (Bagian 2.1 Haversine, 2.2 IQR).
- WeatherRiskGrid: hasil Pipeline 3 - Weather-Risk Overlay per grid H3 (Bagian 3.1-3.4).
- AggregatedFinding: hasil Pipeline 4 - prioritas gabungan AHP+WLC.

Semua kolom geometri memakai SRID 4326 (WGS84), konsisten dengan data OSM/Open-Meteo.
"""

from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PipelineLog(Base):
    """Log riwayat run pipeline — SPEC.md Bagian 5.3 poin 3.

    Kolom wajib sesuai spec: timestamp, pipeline_name, jumlah_temuan, status.
    """

    __tablename__ = "pipeline_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    pipeline_name: Mapped[str] = mapped_column(String(100), nullable=False)
    jumlah_temuan: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success | failed
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class RoadError(Base):
    """Hasil Pipeline 1 — Road Network QA (SPEC.md Bagian 3.1-3.3).

    error_type: dangling_node | disconnected_component | oneway_inconsistency
    """

    __tablename__ = "road_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    # BigInteger wajib: ID node/way OSM sudah melewati batas int 32-bit (2^31-1).
    osm_node_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    osm_way_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    geom: Mapped[Any] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


class PoiAnomaly(Base):
    """Hasil Pipeline 2 — POI Validation (SPEC.md Bagian 2.1 Haversine, 2.2 IQR)."""

    __tablename__ = "poi_anomalies"

    id: Mapped[int] = mapped_column(primary_key=True)
    osm_poi_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    poi_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    distance_to_road_m: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    geom: Mapped[Any] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


class WeatherRiskGrid(Base):
    """Hasil Pipeline 3 — Weather-Risk Overlay per grid H3 (SPEC.md Bagian 3.1-3.4)."""

    __tablename__ = "weather_risk_grid"

    id: Mapped[int] = mapped_column(primary_key=True)
    h3_index: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    geom: Mapped[Any] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    rainfall_realtime_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hotspot_gi_star_z: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_index: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


class AggregatedFinding(Base):
    """Hasil Pipeline 4 — prioritas gabungan AHP+WLC (SPEC.md Bagian 3.2-3.3; PRD P4).

    source_pipeline + source_id merujuk longgar ke baris di road_errors /
    poi_anomalies / weather_risk_grid (bukan FK tunggal, karena sumbernya
    berasal dari 3 tabel berbeda).
    """

    __tablename__ = "aggregated_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_pipeline: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
