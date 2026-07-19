"""Backend FastAPI GeoLogix — baca hasil pipeline dari database.

Fase 5 step 17 (SPEC.md Bagian 8) / urutan file 9 (SPEC.md Bagian 5.2).
Menyajikan isi tabel hasil (SPEC.md Bagian 5.3) untuk client dashboard
(SPEC.md PRD "Dashboard": 3 layer peta + panel log + filter waktu):

- GET /health              : cek koneksi database.
- GET /road-errors         : layer 1 — temuan Pipeline 1 (titik lon/lat).
- GET /poi-anomalies       : layer 2 — temuan Pipeline 2 (titik lon/lat).
- GET /weather-risk        : layer 3 — grid H3 Pipeline 3. Geometri hexagon
                             TIDAK dikirim: deck.gl H3HexagonLayer merender
                             langsung dari h3_index (hemat ±90% payload).
- GET /aggregated-findings : prioritas gabungan Pipeline 4 (lon/lat di-join
                             dari tabel sumber road_errors/poi_anomalies).
- GET /pipeline-logs       : panel log riwayat run (bukti sistem otomatis).

Filter waktu (PRD: "lihat kondisi kemarin vs sekarang") — semantik SNAPSHOT:
baris hasil tiap run disimpan menumpuk (append), jadi "kondisi pada waktu T"
= baris dari batch run terakhir sebelum T, bukan seluruh isi tabel.

- Tanpa parameter        -> snapshot TERBARU: anchor = MAX(kolom waktu),
  ambil baris dalam jendela ``window_minutes`` sebelum anchor. Jendela perlu
  karena timestamp per-baris dibuat saat insert (run P1 full-area menulis
  ±183 rb baris, bisa berlangsung puluhan menit -> default road/poi 120 mnt;
  grid P3 1.079 baris selesai < 1 mnt -> default 15 mnt).
- ``at=<ISO datetime>``  -> snapshot pada waktu itu: anchor = MAX(ts) <= at.
- ``since``/``until``    -> rentang eksplisit; menonaktifkan logika snapshot
  (dipakai kalau client mau riwayat penuh, mis. grafik tren).

API ini READ-ONLY dan TIDAK menulis ke ``pipeline_logs``: aturan logging
CLAUDE.md berlaku untuk run pipeline (proses yang menghasilkan temuan);
request baca bukan run pipeline, dan mencatatnya justru mengotori bukti
otomasi yang jadi nilai jual tabel itu.

CATATAN (utang keputusan di PROGRESS.md): ``road_errors`` full-area saat ini
memuat ±183 rb dangling yang sebagian artefak clip boundary. ``limit``
default 5.000 melindungi payload, tapi layer road-error di client JANGAN
dipakai untuk kesimpulan sebelum keputusan boundary/filter dangling selesai.

Menjalankan lokal::

    uvicorn src.api.main:app --reload
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.db.writer import get_engine

# Jendela default snapshot per tabel (menit) — lihat docstring modul.
ROAD_POI_WINDOW_MIN = 120
GRID_WINDOW_MIN = 15

app = FastAPI(
    title="GeoLogix AI API",
    description="REST read-only hasil 4 pipeline GeoLogix (SPEC.md Fase 5 step 17).",
    version="0.1.0",
)

# Dashboard/aplikasi client di-serve dari origin lain (Vercel/localhost:5173).
# Data read-only publik -> default longgar; batasi via env saat deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=(os.environ.get("API_CORS_ORIGINS") or "*").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)

_engine: Engine | None = None


def get_db_engine() -> Engine:
    """Engine singleton (connection pool SQLAlchemy di baliknya).

    Dependency FastAPI — dioverride di unit test dengan engine SQLite.
    """
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def _norm_dt(value: datetime | None) -> datetime | None:
    """Datetime aware -> naive UTC (kolom DB timestamp-without-tz berisi UTC)."""
    if value is not None and value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _as_datetime(value: datetime | str | None) -> datetime | None:
    """Hasil MAX() bisa berupa str (SQLite) atau datetime (PostgreSQL)."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _time_filter(
    engine: Engine,
    table: str,
    ts_col: str,
    since: datetime | None,
    until: datetime | None,
    at: datetime | None,
    window_minutes: int,
) -> tuple[datetime | None, datetime | None, str]:
    """Terjemahkan parameter waktu -> (start, end, mode).

    mode "range"    : since/until eksplisit dari client.
    mode "snapshot" : jendela [anchor - window, anchor]; anchor = MAX(ts_col)
                      (dibatasi <= at kalau diberikan). Tabel kosong ->
                      (None, None, "snapshot") — endpoint balas items [].
    ``table``/``ts_col`` konstanta internal, bukan input user (aman f-string).
    """
    since, until, at = _norm_dt(since), _norm_dt(until), _norm_dt(at)
    if since is not None or until is not None:
        return since, until, "range"
    sql = f"SELECT MAX({ts_col}) FROM {table}"
    params: dict = {}
    if at is not None:
        sql += f" WHERE {ts_col} <= :at"
        params["at"] = at
    with engine.connect() as conn:
        anchor = _as_datetime(conn.execute(text(sql), params).scalar())
    if anchor is None:
        return None, None, "snapshot"
    return anchor - timedelta(minutes=window_minutes), anchor, "snapshot"


def _fetch(
    engine: Engine,
    select_sql: str,
    count_from_sql: str,
    where: list[str],
    params: dict,
    order_by: str,
    limit: int,
    offset: int,
) -> dict:
    """Eksekusi SELECT + COUNT dengan WHERE/limit/offset yang sama."""
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    with engine.connect() as conn:
        total = conn.execute(
            text(f"SELECT COUNT(*) {count_from_sql}{where_sql}"), params
        ).scalar()
        rows = conn.execute(
            text(
                f"{select_sql}{where_sql} ORDER BY {order_by}"
                f" LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": limit, "offset": offset},
        )
        items = [dict(r) for r in rows.mappings()]
    return {"total": total, "items": items}


def _snapshot_response(
    engine: Engine,
    *,
    table: str,
    ts_col: str,
    select_sql: str,
    count_from_sql: str | None = None,
    extra_where: list[str],
    params: dict,
    since: datetime | None,
    until: datetime | None,
    at: datetime | None,
    window_minutes: int,
    order_by: str,
    limit: int,
    offset: int,
) -> dict:
    """Pola bersama endpoint layer: filter waktu snapshot/range + paginasi."""
    start, end, mode = _time_filter(engine, table, ts_col, since, until, at, window_minutes)
    if mode == "snapshot" and start is None:  # tabel kosong (atau at sebelum data pertama)
        return {"meta": {"mode": mode, "start": None, "end": None, "total": 0}, "items": []}
    where = list(extra_where)
    if start is not None:
        where.append(f"{ts_col} >= :ts_start")
        params["ts_start"] = start
    if end is not None:
        where.append(f"{ts_col} <= :ts_end")
        params["ts_end"] = end
    result = _fetch(
        engine, select_sql, count_from_sql or f"FROM {table}", where, params,
        order_by, limit, offset,
    )
    return {
        "meta": {"mode": mode, "start": start, "end": end, "total": result["total"]},
        "items": result["items"],
    }


@app.get("/")
def root() -> dict:
    return {
        "name": "GeoLogix AI API",
        "endpoints": [
            "/health", "/road-errors", "/poi-anomalies", "/weather-risk",
            "/aggregated-findings", "/pipeline-logs", "/docs",
        ],
    }


@app.get("/health")
def health(engine: Engine = Depends(get_db_engine)) -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # koneksi DB gagal -> 503, bukan 500 generik
        raise HTTPException(status_code=503, detail=f"database: {type(exc).__name__}")
    return {"status": "ok", "database": "ok"}


@app.get("/road-errors")
def road_errors(
    error_type: str | None = None,
    severity: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    at: datetime | None = None,
    window_minutes: int = Query(default=ROAD_POI_WINDOW_MIN, ge=1, le=1440),
    limit: int = Query(default=5000, ge=1, le=200_000),
    offset: int = Query(default=0, ge=0),
    engine: Engine = Depends(get_db_engine),
) -> dict:
    """Layer 1 — temuan Pipeline 1 (Bagian 3.1-3.3) sebagai titik lon/lat."""
    where, params = [], {}
    if error_type is not None:
        where.append("error_type = :error_type")
        params["error_type"] = error_type
    if severity is not None:
        where.append("severity = :severity")
        params["severity"] = severity
    return _snapshot_response(
        engine,
        table="road_errors",
        ts_col="detected_at",
        select_sql=(
            "SELECT id, osm_node_id, osm_way_id, error_type, severity, "
            "ST_X(geom) AS lon, ST_Y(geom) AS lat, detected_at FROM road_errors"
        ),
        extra_where=where,
        params=params,
        since=since, until=until, at=at, window_minutes=window_minutes,
        order_by="id",
        limit=limit, offset=offset,
    )


@app.get("/poi-anomalies")
def poi_anomalies(
    poi_category: str | None = None,
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    since: datetime | None = None,
    until: datetime | None = None,
    at: datetime | None = None,
    window_minutes: int = Query(default=ROAD_POI_WINDOW_MIN, ge=1, le=1440),
    limit: int = Query(default=5000, ge=1, le=200_000),
    offset: int = Query(default=0, ge=0),
    engine: Engine = Depends(get_db_engine),
) -> dict:
    """Layer 2 — temuan Pipeline 2 (Bagian 2.1 Haversine, 2.2 IQR)."""
    where, params = [], {}
    if poi_category is not None:
        where.append("poi_category = :poi_category")
        params["poi_category"] = poi_category
    if min_confidence is not None:
        where.append("confidence_score >= :min_confidence")
        params["min_confidence"] = min_confidence
    return _snapshot_response(
        engine,
        table="poi_anomalies",
        ts_col="detected_at",
        select_sql=(
            "SELECT id, osm_poi_id, poi_category, distance_to_road_m, "
            "confidence_score, ST_X(geom) AS lon, ST_Y(geom) AS lat, "
            "detected_at FROM poi_anomalies"
        ),
        extra_where=where,
        params=params,
        since=since, until=until, at=at, window_minutes=window_minutes,
        order_by="confidence_score DESC, id",
        limit=limit, offset=offset,
    )


@app.get("/weather-risk")
def weather_risk(
    min_risk: float | None = Query(default=None, ge=0.0, le=1.0),
    since: datetime | None = None,
    until: datetime | None = None,
    at: datetime | None = None,
    window_minutes: int = Query(default=GRID_WINDOW_MIN, ge=1, le=1440),
    limit: int = Query(default=2000, ge=1, le=20_000),
    offset: int = Query(default=0, ge=0),
    engine: Engine = Depends(get_db_engine),
) -> dict:
    """Layer 3 — grid H3 Pipeline 3 (Bagian 3.1-3.4). Tanpa geometri (lihat
    docstring modul); 1 snapshot = ±1.079 sel, limit default menampung penuh
    setelah filter min_risk umum dashboard."""
    where, params = [], {}
    if min_risk is not None:
        where.append("risk_index >= :min_risk")
        params["min_risk"] = min_risk
    return _snapshot_response(
        engine,
        table="weather_risk_grid",
        ts_col="computed_at",
        select_sql=(
            "SELECT id, h3_index, rainfall_realtime_mm, hotspot_gi_star_z, "
            "risk_index, computed_at FROM weather_risk_grid"
        ),
        extra_where=where,
        params=params,
        since=since, until=until, at=at, window_minutes=window_minutes,
        order_by="risk_index DESC, id",
        limit=limit, offset=offset,
    )


@app.get("/aggregated-findings")
def aggregated_findings(
    since: datetime | None = None,
    until: datetime | None = None,
    at: datetime | None = None,
    window_minutes: int = Query(default=GRID_WINDOW_MIN, ge=1, le=1440),
    limit: int = Query(default=100, ge=1, le=10_000),
    offset: int = Query(default=0, ge=0),
    engine: Engine = Depends(get_db_engine),
) -> dict:
    """Prioritas gabungan Pipeline 4 (Bagian 3 P4), urut priority_score turun.

    lon/lat + error_type di-join dari tabel sumber (source_pipeline+source_id
    adalah rujukan longgar — lihat models.AggregatedFinding).

    DEDUPE per (source_pipeline, source_id), ambil computed_at terbaru:
    checklist SPEC 5.4 menjalankan P4 3x berturut-turut berjarak detik —
    jendela waktu tidak bisa memisahkan batch serapat itu, dan tanpa dedupe
    temuan yang sama tampil 3x di client. Konsisten dengan dedupe runner P4.
    """
    start, end, mode = _time_filter(
        engine, "aggregated_findings a", "a.computed_at", since, until, at,
        window_minutes,
    )
    if mode == "snapshot" and start is None:
        return {"meta": {"mode": mode, "start": None, "end": None, "total": 0}, "items": []}
    where, params = [], {}
    if start is not None:
        where.append("a.computed_at >= :ts_start")
        params["ts_start"] = start
    if end is not None:
        where.append("a.computed_at <= :ts_end")
        params["ts_end"] = end
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    inner = (
        "SELECT a.id, a.source_pipeline, a.source_id, a.priority_score, "
        "a.computed_at, "
        "COALESCE(ST_X(r.geom), ST_X(p.geom)) AS lon, "
        "COALESCE(ST_Y(r.geom), ST_Y(p.geom)) AS lat, "
        "COALESCE(r.error_type, 'poi_anomaly') AS error_type, "
        "ROW_NUMBER() OVER (PARTITION BY a.source_pipeline, a.source_id "
        "ORDER BY a.computed_at DESC, a.id DESC) AS rn "
        "FROM aggregated_findings a "
        "LEFT JOIN road_errors r "
        "ON a.source_pipeline = 'road_errors' AND r.id = a.source_id "
        "LEFT JOIN poi_anomalies p "
        "ON a.source_pipeline = 'poi_anomalies' AND p.id = a.source_id"
        f"{where_sql}"
    )
    with engine.connect() as conn:
        total = conn.execute(
            text(
                "SELECT COUNT(DISTINCT source_pipeline || ':' || source_id) "
                f"FROM aggregated_findings a{where_sql}"
            ),
            params,
        ).scalar()
        rows = conn.execute(
            text(
                f"SELECT id, source_pipeline, source_id, priority_score, "
                f"computed_at, lon, lat, error_type FROM ({inner}) t "
                f"WHERE rn = 1 ORDER BY priority_score DESC, id "
                f"LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": limit, "offset": offset},
        )
        items = [dict(r) for r in rows.mappings()]
    return {"meta": {"mode": mode, "start": start, "end": end, "total": total}, "items": items}


@app.get("/pipeline-logs")
def pipeline_logs(
    pipeline_name: str | None = None,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    engine: Engine = Depends(get_db_engine),
) -> dict:
    """Panel log riwayat run (Bagian 5.3 poin 3) — terbaru dulu, TANPA logika
    snapshot: log memang riwayat penuh, bukan keadaan sesaat."""
    where, params = [], {}
    if pipeline_name is not None:
        where.append("pipeline_name = :pipeline_name")
        params["pipeline_name"] = pipeline_name
    if status is not None:
        where.append("status = :status")
        params["status"] = status
    if since is not None:
        where.append("timestamp >= :since")
        params["since"] = _norm_dt(since)
    if until is not None:
        where.append("timestamp <= :until")
        params["until"] = _norm_dt(until)
    result = _fetch(
        engine,
        "SELECT id, timestamp, pipeline_name, jumlah_temuan, status, detail "
        "FROM pipeline_logs",
        "FROM pipeline_logs",
        where,
        params,
        "timestamp DESC, id DESC",
        limit,
        offset,
    )
    return {"meta": {"total": result["total"]}, "items": result["items"]}
