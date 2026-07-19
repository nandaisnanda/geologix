"""Deteksi anomali jarak POI→jalan — IQR, SPEC.md Bagian 3, Pipeline 2.2.

Rumus persis SPEC 2.2 (bukan z-score/ML — jarak spasial skewed, IQR robust
tanpa asumsi distribusi):

    Q1 = persentil ke-25 dari seluruh jarak POI→jalan
    Q3 = persentil ke-75
    IQR = Q3 − Q1
    batas atas = Q3 + 1.5 × IQR

Multiplier 1.5 diambil dari ``config.IQR_OUTLIER_MULTIPLIER``. POI dengan
jarak > batas atas diflag anomali (lokasi "melayang" jauh dari jaringan jalan).

``confidence_score`` (keputusan implementasi — SPEC tidak menetapkan; dicatat
di PROGRESS.md): jarak pelampauan batas atas dalam satuan IQR, dipetakan linear
0→1 antara pagar dalam Tukey (Q3 + 1.5·IQR) dan pagar luar (Q3 + 3·IQR);
melewati pagar luar = 1.0. Kasus degenerate IQR = 0 → pelanggar diberi 1.0.
"""

import geopandas as gpd
import numpy as np

from src import config


def iqr_bounds(distances) -> dict:
    """Hitung Q1/Q3/IQR/batas atas persis SPEC 2.2. Input: array-like jarak."""
    arr = np.asarray(distances, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        raise ValueError("Tidak ada jarak valid untuk dihitung IQR")
    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1
    return {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "upper_bound": q3 + config.IQR_OUTLIER_MULTIPLIER * iqr,
    }


def _confidence(distance: float, bounds: dict) -> float:
    """Skor 0-1: linear antara pagar dalam (batas atas) dan pagar luar Tukey."""
    if bounds["iqr"] <= 0:
        return 1.0
    exceed_iqr = (distance - bounds["upper_bound"]) / bounds["iqr"]
    return min(1.0, exceed_iqr / config.IQR_OUTLIER_MULTIPLIER)


def _osm_id_to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def detect_outliers(
    pois: gpd.GeoDataFrame, distance_col: str = "distance_to_road_m"
) -> tuple[list[dict], dict]:
    """Flag POI berjarak > batas atas IQR (SPEC 2.2).

    Input: hasil ``spatial_join.nearest_road_distances`` (wajib punya kolom
    ``distance_to_road_m``). Return ``(findings, bounds)``; tiap finding dict
    siap tulis ke ``poi_anomalies``: ``osm_poi_id``, ``poi_category``,
    ``distance_to_road_m``, ``confidence_score``, ``lon``, ``lat``.
    """
    bounds = iqr_bounds(pois[distance_col])
    outliers = pois[pois[distance_col] > bounds["upper_bound"]]
    findings = [
        {
            "osm_poi_id": _osm_id_to_int(row.get("osm_id")),
            "poi_category": row.get("fclass"),
            "distance_to_road_m": float(row[distance_col]),
            "confidence_score": _confidence(float(row[distance_col]), bounds),
            "lon": row.geometry.x,
            "lat": row.geometry.y,
        }
        for _, row in outliers.iterrows()
    ]
    return findings, bounds
