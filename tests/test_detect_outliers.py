"""Unit test detect_outliers.py — SPEC.md Bagian 3 Pipeline 2.2 (IQR)."""

import geopandas as gpd
import pytest
from shapely.geometry import Point

from src.pipeline_2_poi_qa.detect_outliers import detect_outliers, iqr_bounds


def _pois(distances):
    return gpd.GeoDataFrame(
        {
            "osm_id": [str(i) for i in range(len(distances))],
            "fclass": ["restaurant"] * len(distances),
            "distance_to_road_m": distances,
            "geometry": [Point(106.8 + i * 0.001, -6.2) for i in range(len(distances))],
        },
        crs="EPSG:4326",
    )


def test_iqr_bounds_rumus_spec():
    # 9 nilai: 1..8 dan 100. np.percentile linear: Q1=3, Q3=7, IQR=4.
    bounds = iqr_bounds([1, 2, 3, 4, 5, 6, 7, 8, 100])
    assert bounds["q1"] == pytest.approx(3.0)
    assert bounds["q3"] == pytest.approx(7.0)
    assert bounds["iqr"] == pytest.approx(4.0)
    assert bounds["upper_bound"] == pytest.approx(7.0 + 1.5 * 4.0)  # = 13.0


def test_iqr_bounds_kosong_raise():
    with pytest.raises(ValueError, match="jarak valid"):
        iqr_bounds([float("nan")])


def test_detect_outliers_flag_di_atas_batas():
    findings, bounds = detect_outliers(_pois([1, 2, 3, 4, 5, 6, 7, 8, 100]))
    assert bounds["upper_bound"] == pytest.approx(13.0)
    assert len(findings) == 1
    f = findings[0]
    assert f["osm_poi_id"] == 8  # osm_id "8" -> int
    assert f["poi_category"] == "restaurant"
    assert f["distance_to_road_m"] == pytest.approx(100.0)
    # (100-13)/4 = 21.75 IQR di atas batas -> jauh melewati pagar luar -> 1.0
    assert f["confidence_score"] == 1.0
    assert f["lat"] == pytest.approx(-6.2)


def test_detect_outliers_tanpa_outlier():
    findings, _ = detect_outliers(_pois([10.0, 11.0, 12.0, 13.0]))
    assert findings == []


def test_detect_outliers_confidence_linear_antara_pagar():
    # 10 nilai: Q1=2.25, Q3=6.75, IQR=4.5, upper=13.5 (np.percentile linear)
    # -> 15 melewati batas sebesar 1.5/4.5 = 0.333 IQR, di bawah pagar luar.
    distances = [0, 1, 2, 3, 4, 5, 6, 7, 8, 15.0]
    findings, bounds = detect_outliers(_pois(distances))
    assert bounds["upper_bound"] == pytest.approx(13.5)
    assert len(findings) == 1
    assert findings[0]["confidence_score"] == pytest.approx((1.5 / 4.5) / 1.5)


def test_detect_outliers_iqr_nol_confidence_penuh():
    findings, bounds = detect_outliers(_pois([5.0, 5.0, 5.0, 5.0, 9.0]))
    assert bounds["iqr"] == pytest.approx(0.0)
    assert len(findings) == 1
    assert findings[0]["confidence_score"] == 1.0
