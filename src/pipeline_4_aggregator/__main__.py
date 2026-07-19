"""Runner Pipeline 4 — Aggregator (SPEC.md PRD Pipeline 4 + Bagian 3 P4).

Merakit input ``prioritize()`` dari temuan nyata di database lalu menjalankan
AHP+WLC -> ``aggregated_findings`` + log ``pipeline_logs``. File runner
(``__main__.py``) di luar daftar SPEC 5.1 — keputusan minimal yang sama
dengan Pipeline 1-3.

Sumber temuan (keputusan proyek): baris ``road_errors`` (P1) dan
``poi_anomalies`` (P2) — SPEC Bagian 3 P4 mendefinisikan kriteria severity
"dari P1/P2"; hasil P3 (grid risiko cuaca kontinu per jam) bukan "error yang
bisa diperbaiki" sehingga tidak punya severity/kemudahan-perbaikan yang
bermakna, dan tetap masuk ringkasan lewat dashboard + pipeline_logs (PRD P4).

Perakitan 3 kriteria per temuan:
- severity           : P1 dari kolom ``severity`` via ``SEVERITY_SCORE``
                       (low=1, medium=2, high=3); P2 = 1 + 2*confidence_score
                       (confidence 0..1 -> skala 1..3 yang sama dengan P1).
- population_density : sampling WorldPop 1km di titik temuan
                       (``fetch_worldpop.sample_density``); NaN (laut/nodata)
                       -> temuan DIBUANG eksplisit sebelum prioritisasi
                       (dicatat di ringkasan), bukan diam-diam 0.
- ease_of_fix        : skor manual 1-5 per jenis error (keputusan proyek,
                       ``EASE_OF_FIX_BY_TYPE``): poi_anomaly=5 (geser titik,
                       edit paling ringan), dangling_node=4 (perbaikan lokal
                       1 way), oneway_inconsistency=3 (verifikasi arah +
                       edit tag), disconnected_component=2 (butuh survei
                       konektivitas lebih luas).

Duplikat antar-run validasi (tiap temuan tersimpan 3x dari checklist 5.4)
di-dedupe: kunci identitas temuan, ambil deteksi TERBARU (``detected_at``).

Pemakaian::

    python -m src.pipeline_4_aggregator
"""

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.data_ingestion.fetch_worldpop import sample_density
from src.db.writer import get_engine, log_pipeline_run
from src.pipeline_4_aggregator.prioritize import PIPELINE_NAME, SEVERITY_SCORE, run

# Skor manual kemudahan perbaikan per jenis error (lihat docstring modul).
EASE_OF_FIX_BY_TYPE = {
    "poi_anomaly": 5.0,
    "dangling_node": 4.0,
    "oneway_inconsistency": 3.0,
    "disconnected_component": 2.0,
}


def load_findings(engine) -> pd.DataFrame:
    """Baca temuan P1+P2 terbaru (dedupe) -> DataFrame input ``prioritize()``."""
    road = pd.read_sql(
        text(
            "SELECT id, osm_node_id, osm_way_id, error_type, severity, "
            "ST_X(geom) AS lon, ST_Y(geom) AS lat, detected_at FROM road_errors"
        ),
        engine,
    )
    poi = pd.read_sql(
        text(
            "SELECT id, osm_poi_id, confidence_score, "
            "ST_X(geom) AS lon, ST_Y(geom) AS lat, detected_at FROM poi_anomalies"
        ),
        engine,
    )

    frames = []
    if not road.empty:
        road = (
            road.sort_values("detected_at")
            .drop_duplicates(["osm_node_id", "osm_way_id", "error_type"], keep="last")
        )
        unknown = set(road["severity"]) - set(SEVERITY_SCORE)
        if unknown:
            raise ValueError(f"severity road_errors tak dikenal: {sorted(unknown)}")
        frames.append(
            pd.DataFrame(
                {
                    "source_pipeline": "road_errors",
                    "source_id": road["id"].to_numpy(),
                    "error_type": road["error_type"].to_numpy(),
                    "severity": road["severity"].map(SEVERITY_SCORE).to_numpy(),
                    "lon": road["lon"].to_numpy(),
                    "lat": road["lat"].to_numpy(),
                }
            )
        )
    if not poi.empty:
        poi = (
            poi.sort_values("detected_at")
            .drop_duplicates(["osm_poi_id", "lon", "lat"], keep="last")
        )
        frames.append(
            pd.DataFrame(
                {
                    "source_pipeline": "poi_anomalies",
                    "source_id": poi["id"].to_numpy(),
                    "error_type": "poi_anomaly",
                    # confidence 0..1 -> skala severity 1..3 yang sama dgn P1.
                    "severity": 1.0 + 2.0 * poi["confidence_score"].to_numpy(),
                    "lon": poi["lon"].to_numpy(),
                    "lat": poi["lat"].to_numpy(),
                }
            )
        )
    if not frames:
        raise ValueError("road_errors dan poi_anomalies kosong — jalankan P1/P2 dulu")
    df = pd.concat(frames, ignore_index=True)
    df["ease_of_fix"] = df["error_type"].map(EASE_OF_FIX_BY_TYPE)
    if df["ease_of_fix"].isna().any():
        unknown = sorted(set(df.loc[df["ease_of_fix"].isna(), "error_type"]))
        raise ValueError(f"error_type tanpa skor ease_of_fix: {unknown}")
    return df


def main() -> dict:
    # Kegagalan perakitan input dicatat di sini; kegagalan di dalam run()
    # sudah dicatat oleh run() sendiri (jangan dobel log).
    try:
        engine = get_engine()
        df = load_findings(engine)
        df["population_density"] = sample_density(df["lon"], df["lat"])
        n_no_pop = int(df["population_density"].isna().sum())
        df = df.dropna(subset=["population_density"]).reset_index(drop=True)
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise

    summary = run(df, engine=engine)  # prioritize -> save -> log (success)
    summary["dropped_no_population"] = n_no_pop
    print(summary)
    return summary


if __name__ == "__main__":
    main()
