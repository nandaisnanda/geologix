"""Unit test fetch_osm_poi.py — SPEC.md Bagian 5.2c (baca layer POI dari .shp.zip)."""

import zipfile

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from src.data_ingestion import fetch_osm_poi


@pytest.fixture()
def synthetic_zip(tmp_path):
    """Zip berisi 2 layer shapefile persis bernama layer Geofabrik."""
    layer_dir = tmp_path / "layers"
    layer_dir.mkdir()

    points = gpd.GeoDataFrame(
        {
            "osm_id": ["1", "2", "3"],
            "code": [2301, 2301, 2301],
            "fclass": ["restaurant", "restaurant", "restaurant"],
            "name": ["dalam-1", "dalam-2", "luar"],
            "geometry": [Point(0.5, 0.5), Point(0.9, 0.9), Point(5.0, 5.0)],
        },
        crs="EPSG:4326",
    )
    points.to_file(layer_dir / f"{fetch_osm_poi.POI_POINT_LAYER}.shp")

    areas = gpd.GeoDataFrame(
        {
            "osm_id": ["10"],
            "code": [2401],
            "fclass": ["hotel"],
            "name": ["area-dalam"],
            "geometry": [Polygon([(0.1, 0.1), (0.3, 0.1), (0.3, 0.3), (0.1, 0.3)])],
        },
        crs="EPSG:4326",
    )
    areas.to_file(layer_dir / f"{fetch_osm_poi.POI_AREA_LAYER}.shp")

    zip_path = tmp_path / "java-latest-free.shp.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in layer_dir.iterdir():
            zf.write(f, arcname=f.name)
    return zip_path


@pytest.fixture()
def synthetic_boundary(tmp_path, monkeypatch):
    """Boundary 1x1 derajat dengan kolom WADMKC, monkeypatch ke modul."""
    boundary = gpd.GeoDataFrame(
        {
            "WADMKC": ["Menteng"],
            "geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
        },
        crs="EPSG:4326",
    )
    path = tmp_path / "boundary.shp"
    boundary.to_file(path)
    monkeypatch.setattr(fetch_osm_poi, "BOUNDARY_SHP_PATH", path)
    return path


def test_load_pois_clip_dan_konversi_area(synthetic_zip, synthetic_boundary):
    pois = fetch_osm_poi.load_pois(zip_path=synthetic_zip)

    # Titik di luar boundary (5,5) harus terbuang oleh gpd.clip.
    assert set(pois["name"]) == {"dalam-1", "dalam-2", "area-dalam"}
    # Layer area wajib jadi titik (representative_point), bukan poligon.
    assert (pois.geometry.geom_type == "Point").all()
    # Penanda asal layer (SPEC 5.2c: 2 layer, titik + area).
    area_row = pois[pois["name"] == "area-dalam"].iloc[0]
    assert area_row["source_layer"] == fetch_osm_poi.POI_AREA_LAYER
    assert 0.1 <= area_row.geometry.x <= 0.3 and 0.1 <= area_row.geometry.y <= 0.3


def test_load_pois_filter_kecamatan_wadmkc(synthetic_zip, synthetic_boundary):
    pois = fetch_osm_poi.load_pois(zip_path=synthetic_zip, kecamatan="menteng")
    assert len(pois) == 3  # casefold match "Menteng"
    with pytest.raises(ValueError, match="WADMKC"):
        fetch_osm_poi.load_pois(zip_path=synthetic_zip, kecamatan="Atlantis")


def test_ensure_shp_zip_pakai_cache_lokal(tmp_path, monkeypatch):
    """Kalau zip sudah ada di data/raw, TIDAK boleh download ulang (idempotent)."""
    fake_zip = tmp_path / "java-latest-free.shp.zip"
    fake_zip.write_bytes(b"x")
    monkeypatch.setattr(fetch_osm_poi, "SHP_ZIP_PATH", fake_zip)
    monkeypatch.setattr(
        fetch_osm_poi.requests, "get",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("tidak boleh download")),
    )
    assert fetch_osm_poi.ensure_shp_zip() == fake_zip


def test_main_simpan_gpkg_dan_log_pipeline(
    synthetic_zip, synthetic_boundary, tmp_path, monkeypatch
):
    logged = []
    monkeypatch.setattr(
        fetch_osm_poi, "log_pipeline_run",
        lambda name, n, status, detail=None: logged.append((name, n, status, detail)),
    )
    out = tmp_path / "poi_test.gpkg"

    n = fetch_osm_poi.main(zip_path=synthetic_zip, output_path=out)

    assert n == 3
    assert out.exists()
    saved = gpd.read_file(out, layer="poi")
    assert len(saved) == 3
    assert logged == [
        ("poi_ingestion", 3, "success",
         "area=jabodetabek point=2 area_poi=1 -> poi_test.gpkg"),
    ]
