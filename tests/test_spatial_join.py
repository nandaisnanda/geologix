"""Unit test spatial_join.py — SPEC.md Bagian 3 Pipeline 2.1 (Haversine)."""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Point

from src.pipeline_2_poi_qa.spatial_join import haversine_km, nearest_road_distances

# Panjang busur 1 derajat meridian pada bola R=6371 km: 2*pi*6371/360.
KM_PER_DEG = 111.19493


def test_haversine_1_derajat_latitude():
    assert haversine_km(0.0, 0.0, 1.0, 0.0) == pytest.approx(KM_PER_DEG, abs=1e-3)


def test_haversine_titik_sama_nol_dan_simetris():
    assert haversine_km(-6.19, 106.83, -6.19, 106.83) == 0.0
    d1 = haversine_km(-6.19, 106.83, -6.90, 107.61)  # ~Jakarta -> Bandung
    d2 = haversine_km(-6.90, 107.61, -6.19, 106.83)
    assert d1 == pytest.approx(d2)
    assert 100 < d1 < 130  # sanity: jarak Jakarta-Bandung ~118 km


def test_haversine_vectorized():
    d = haversine_km(np.array([0.0, 0.0]), 0.0, np.array([1.0, 2.0]), 0.0)
    assert d == pytest.approx([KM_PER_DEG, 2 * KM_PER_DEG], abs=1e-2)


@pytest.fixture()
def roads_dua_garis():
    return gpd.GeoDataFrame(
        {
            "osm_id": ["100", "200"],
            "fclass": ["residential", "primary"],
            "geometry": [
                LineString([(0.0, -1.0), (0.0, 1.0)]),  # garis vertikal x=0
                LineString([(1.0, -1.0), (1.0, 1.0)]),  # garis vertikal x=1
            ],
        },
        crs="EPSG:4326",
    )


def test_nearest_road_distances_pilih_jalan_terdekat(roads_dua_garis):
    pois = gpd.GeoDataFrame(
        {"osm_id": ["1", "2"], "geometry": [Point(0.01, 0.0), Point(0.98, 0.0)]},
        crs="EPSG:4326",
    )
    out = nearest_road_distances(pois, roads_dua_garis)

    assert list(out["nearest_road_osm_id"]) == ["100", "200"]
    assert list(out["nearest_road_fclass"]) == ["residential", "primary"]
    # 0.01 derajat longitude di ekuator ~= 1.11195 km = 1111.95 m.
    assert out["distance_to_road_m"].iloc[0] == pytest.approx(
        0.01 * KM_PER_DEG * 1000, rel=1e-4
    )
    assert out["distance_to_road_m"].iloc[1] == pytest.approx(
        0.02 * KM_PER_DEG * 1000, rel=1e-4
    )
    # Input tidak boleh termutasi.
    assert "distance_to_road_m" not in pois.columns


def test_nearest_road_distances_poi_kosong(roads_dua_garis):
    pois = gpd.GeoDataFrame({"osm_id": []}, geometry=[], crs="EPSG:4326")
    out = nearest_road_distances(pois, roads_dua_garis)
    assert len(out) == 0
    assert "distance_to_road_m" in out.columns


def test_nearest_road_distances_jalan_kosong():
    pois = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs="EPSG:4326")
    roads = gpd.GeoDataFrame({"osm_id": []}, geometry=[], crs="EPSG:4326")
    with pytest.raises(ValueError, match="jalan kosong"):
        nearest_road_distances(pois, roads)
