"""Bangun grid H3 Jabodetabek untuk Pipeline 3 — Weather-Risk Overlay.

SPEC.md Bagian 2 Pipeline 3 (overlay curah hujan ke grid H3) dan Bagian 5.2
urutan 6 (file pertama pipeline_3_weather_risk). Grid ini adalah unit analisis
untuk seluruh rumus Bagian 3 Pipeline 3: nilai kriteria per sel dinormalisasi
Min-Max (3.1), digabung WLC (3.3), dan diuji hotspot Getis-Ord Gi* (3.4).

Keputusan H3_RESOLUTION = 7 (didelegasikan Fase 0 -> sini, nilai di config.py):
- Jabodetabek ~7.000 km2; res 7 (avg hex 5,16 km2, edge ~1,2 km) ~ 1.400 sel.
- Curah hujan Open-Meteo utk Indonesia beresolusi model ~11-25 km — grid lebih
  halus dari sumber datanya tidak menambah informasi (res 8 = ~9.700 sel,
  7x beban API + baris DB per jam; res 6 = 36 km2/hex, terlalu kasar untuk
  peta risiko level kota).

Alur (deterministik, idempotent):
1. Boundary = dissolve seluruh desa di ``data/boundaries/jabodetabek.shp``
   (sumber sama dengan pipeline lain), reproject ke EPSG:4326 bila perlu.
2. ``h3.geo_to_cells()`` (containment: pusat sel di dalam poligon) -> daftar
   cell, diurutkan supaya output deterministik antar-run.
3. GeoDataFrame: ``h3_index``, ``lat``/``lng`` pusat sel (titik sampling
   Open-Meteo), geometri poligon hexagon (SRID 4326, cocok schema
   ``weather_risk_grid`` di models.py).
4. ``main()``: simpan ``data/raw/h3_grid_jabodetabek.gpkg`` + log run ke
   ``pipeline_logs`` (SPEC.md Bagian 5.3).
"""

import argparse

import geopandas as gpd
import h3
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from src import config
from src.db.writer import log_pipeline_run

PIPELINE_NAME = "h3_grid"

BOUNDARY_SHP_PATH = config.BOUNDARIES_DIR / "jabodetabek.shp"
GRID_OUTPUT_PATH = config.RAW_DATA_DIR / "h3_grid_jabodetabek.gpkg"
GRID_LAYER = "h3_grid"


def load_boundary_polygon(shp_path=None) -> BaseGeometry:
    """Dissolve seluruh poligon boundary jadi satu geometri EPSG:4326."""
    gdf = gpd.read_file(shp_path or BOUNDARY_SHP_PATH)
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf.union_all()


def cell_to_polygon(cell: str) -> Polygon:
    """Poligon hexagon shapely dari satu cell H3 (h3 pakai lat,lng -> shapely lng,lat)."""
    return Polygon((lng, lat) for lat, lng in h3.cell_to_boundary(cell))


def build_h3_grid(
    boundary: BaseGeometry | None = None,
    resolution: int = config.H3_RESOLUTION,
) -> gpd.GeoDataFrame:
    """Grid H3 menutupi boundary: kolom h3_index, lat, lng, geometry hexagon.

    Containment mengikuti default H3 polyfill: sel masuk grid jika PUSAT sel
    ada di dalam boundary. Daftar sel diurutkan -> deterministik antar-run.
    """
    if boundary is None:
        boundary = load_boundary_polygon()
    cells = sorted(h3.geo_to_cells(boundary, resolution))
    if not cells:
        raise ValueError(
            f"Boundary tidak menghasilkan sel H3 pada resolusi {resolution} "
            "(poligon terlalu kecil? cek CRS boundary = EPSG:4326)"
        )
    centroids = [h3.cell_to_latlng(c) for c in cells]
    return gpd.GeoDataFrame(
        {
            "h3_index": cells,
            "lat": [lat for lat, _ in centroids],
            "lng": [lng for _, lng in centroids],
        },
        geometry=[cell_to_polygon(c) for c in cells],
        crs="EPSG:4326",
    )


def main(output_path=None, resolution: int = config.H3_RESOLUTION) -> int:
    """Bangun grid + simpan GPKG + log ke pipeline_logs. Return jumlah sel."""
    output_path = output_path or GRID_OUTPUT_PATH
    try:
        grid = build_h3_grid(resolution=resolution)
        grid.to_file(output_path, layer=GRID_LAYER, driver="GPKG")
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    log_pipeline_run(
        PIPELINE_NAME,
        len(grid),
        "success",
        detail=f"resolution={resolution} cells={len(grid)} -> {output_path.name}",
    )
    return len(grid)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bangun grid H3 Jabodetabek (SPEC P3)")
    parser.add_argument(
        "--resolution", type=int, default=config.H3_RESOLUTION,
        help=f"Resolusi H3 (default {config.H3_RESOLUTION}, lihat config.py)",
    )
    args = parser.parse_args()
    n = main(resolution=args.resolution)
    print(f"Grid H3 tersimpan: {n} sel -> {GRID_OUTPUT_PATH}")
