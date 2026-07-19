"""Unit test h3_grid.py — SPEC.md Bagian 2 Pipeline 3 (grid H3 Jabodetabek)."""

import geopandas as gpd
import h3
import pytest
from shapely.geometry import Polygon, box

from src.pipeline_3_weather_risk import h3_grid

# Kotak ~11x11 km di sekitar Monas (cukup untuk beberapa sel res 7).
MONAS_BOX = box(106.77, -6.225, 106.87, -6.125)


def test_build_h3_grid_valid_dan_deterministik():
    grid = h3_grid.build_h3_grid(boundary=MONAS_BOX, resolution=7)

    assert len(grid) > 0
    assert grid["h3_index"].map(h3.is_valid_cell).all()
    assert (grid["h3_index"].map(h3.get_resolution) == 7).all()
    # Deterministik antar-run (sel diurutkan).
    grid2 = h3_grid.build_h3_grid(boundary=MONAS_BOX, resolution=7)
    assert list(grid["h3_index"]) == list(grid2["h3_index"])
    # Tidak ada sel duplikat.
    assert grid["h3_index"].is_unique


def test_build_h3_grid_geometri_dan_centroid_konsisten():
    grid = h3_grid.build_h3_grid(boundary=MONAS_BOX, resolution=7)

    # Geometri = poligon hexagon valid yang memuat pusat selnya sendiri.
    assert (grid.geometry.geom_type == "Polygon").all()
    assert grid.geometry.is_valid.all()
    assert grid.crs.to_epsg() == 4326
    for row in grid.itertuples():
        lat, lng = h3.cell_to_latlng(row.h3_index)
        assert row.lat == lat and row.lng == lng
        # Urutan koordinat shapely wajib (lng, lat) — pusat sel di dalam hexagon.
        assert row.geometry.contains(gpd.points_from_xy([lng], [lat])[0])
    # Containment default polyfill: pusat semua sel di dalam boundary.
    assert MONAS_BOX.contains(gpd.points_from_xy(grid["lng"], grid["lat"])).all()


def test_build_h3_grid_boundary_terlalu_kecil_raise():
    titik_kecil = Polygon(
        [(106.8, -6.2), (106.8001, -6.2), (106.8001, -6.1999), (106.8, -6.1999)]
    )
    with pytest.raises(ValueError, match="resolusi"):
        h3_grid.build_h3_grid(boundary=titik_kecil, resolution=7)


def test_load_boundary_polygon_dissolve_dan_reproject(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1)]}, crs="EPSG:4326"
    ).to_crs(epsg=3857)
    path = tmp_path / "boundary.shp"
    gdf.to_file(path)

    poly = h3_grid.load_boundary_polygon(shp_path=path)

    # Dua kotak menempel -> satu geometri, kembali ke derajat (bukan meter).
    assert poly.geom_type in ("Polygon", "MultiPolygon")
    assert abs(poly.area - 2.0) < 1e-6


def test_main_simpan_gpkg_dan_log_pipeline(tmp_path, monkeypatch):
    logged = []
    monkeypatch.setattr(
        h3_grid, "log_pipeline_run",
        lambda name, n, status, detail=None: logged.append((name, n, status, detail)),
    )
    monkeypatch.setattr(h3_grid, "load_boundary_polygon", lambda: MONAS_BOX)
    out = tmp_path / "grid_test.gpkg"

    n = h3_grid.main(output_path=out, resolution=7)

    assert n > 0 and out.exists()
    saved = gpd.read_file(out, layer=h3_grid.GRID_LAYER)
    assert len(saved) == n
    assert logged == [
        ("h3_grid", n, "success", f"resolution=7 cells={n} -> grid_test.gpkg"),
    ]
