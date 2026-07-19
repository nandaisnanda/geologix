"""Baca layer POI dari ``java-latest-free.shp.zip`` untuk Pipeline 2 (POI Validation)
— SPEC.md Bagian 5.2c.

Sumber: Geofabrik ``java-latest-free.shp.zip`` (~2.2GB, region Java, lisensi ODbL),
layer ``gis_osm_pois_free_1`` (titik) dan ``gis_osm_pois_a_free_1`` (area).
Khusus ``.shp.zip`` — jaringan jalan dari ``.pbf`` ditangani terpisah oleh
``fetch_osm.py`` (SPEC.md Bagian 5.2c: dua sumber OSM JANGAN dicampur, POI
validation cuma butuh koordinat + kategori, tidak butuh topologi graph).

Alur (idempotent, aman dijalankan berkali-kali):
1. ``ensure_shp_zip()`` — pakai zip yang sudah ada di ``data/raw/``; kalau belum
   ada, download dari Geofabrik (cache lokal, pola sama dengan ``fetch_osm.py``).
2. Baca kedua layer POI via ``gpd.read_file(zip, layer=..., bbox=...)`` —
   prefilter bbox boundary supaya tidak memuat POI seluruh Java ke memori.
3. Layer area dikonversi ke titik ``representative_point()`` (titik dijamin di
   dalam poligon) — downstream ``spatial_join.py`` (Haversine, SPEC.md Bagian 3
   Pipeline 2.1) bekerja pada titik.
4. ``gpd.clip()`` ke boundary Jabodetabek, atau 1 kecamatan (kolom ``WADMKC``)
   untuk sample skala kecil (SPEC.md Bagian 8).
5. Simpan ke ``data/raw/poi_jabodetabek.gpkg`` + log run ke ``pipeline_logs``
   (SPEC.md Bagian 5.3).
"""

import argparse

import geopandas as gpd
import pandas as pd
import requests

from src import config
from src.db.writer import log_pipeline_run

PIPELINE_NAME = "poi_ingestion"

GEOFABRIK_SHP_ZIP_URL = (
    "https://download.geofabrik.de/asia/indonesia/java-latest-free.shp.zip"
)
SHP_ZIP_PATH = config.RAW_DATA_DIR / "java-latest-free.shp.zip"
BOUNDARY_SHP_PATH = config.BOUNDARIES_DIR / "jabodetabek.shp"
POI_OUTPUT_PATH = config.RAW_DATA_DIR / "poi_jabodetabek.gpkg"

POI_POINT_LAYER = "gis_osm_pois_free_1"
POI_AREA_LAYER = "gis_osm_pois_a_free_1"
# Kolom atribut Geofabrik yang dipakai Pipeline 2 (koordinat + kategori saja).
POI_COLUMNS = ["osm_id", "code", "fclass", "name"]


def ensure_shp_zip(force: bool = False):
    """Pakai .shp.zip lokal kalau ada; kalau tidak, download dari Geofabrik."""
    if SHP_ZIP_PATH.exists() and not force:
        return SHP_ZIP_PATH
    with requests.get(GEOFABRIK_SHP_ZIP_URL, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        tmp = SHP_ZIP_PATH.with_suffix(SHP_ZIP_PATH.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(SHP_ZIP_PATH)
    return SHP_ZIP_PATH


def load_boundary(kecamatan: str | None = None) -> gpd.GeoDataFrame:
    """Boundary clip: seluruh Jabodetabek, atau 1 kecamatan (kolom WADMKC)."""
    gdf = gpd.read_file(BOUNDARY_SHP_PATH)
    if kecamatan is not None:
        gdf = gdf[gdf["WADMKC"].str.casefold() == kecamatan.casefold()]
        if gdf.empty:
            raise ValueError(
                f"Kecamatan {kecamatan!r} tidak ditemukan di kolom WADMKC"
            )
    return gdf


def read_poi_layer(zip_path, layer: str, bbox=None) -> gpd.GeoDataFrame:
    """Baca satu layer POI dari .shp.zip, hanya kolom yang dipakai Pipeline 2."""
    gdf = gpd.read_file(zip_path, layer=layer, bbox=bbox)
    keep = [c for c in POI_COLUMNS if c in gdf.columns]
    return gdf[keep + [gdf.geometry.name]]


def load_pois(zip_path=None, kecamatan: str | None = None) -> gpd.GeoDataFrame:
    """Gabungkan layer titik + area (sebagai representative_point), clip boundary."""
    zip_path = zip_path or SHP_ZIP_PATH
    boundary = load_boundary(kecamatan)

    points = read_poi_layer(zip_path, POI_POINT_LAYER, bbox=tuple(boundary.total_bounds))
    if boundary.crs is not None and boundary.crs != points.crs:
        boundary = boundary.to_crs(points.crs)

    areas = read_poi_layer(zip_path, POI_AREA_LAYER, bbox=tuple(boundary.total_bounds))
    areas["geometry"] = areas.geometry.representative_point()

    points["source_layer"] = POI_POINT_LAYER
    areas["source_layer"] = POI_AREA_LAYER
    pois = gpd.GeoDataFrame(
        pd.concat([points, areas], ignore_index=True), crs=points.crs
    )
    return gpd.clip(pois, boundary)


def main(kecamatan: str | None = None, zip_path=None, output_path=None) -> int:
    """Jalankan ingest POI + log ke pipeline_logs. Return jumlah baris POI."""
    output_path = output_path or POI_OUTPUT_PATH
    try:
        zip_path = zip_path or ensure_shp_zip()
        pois = load_pois(zip_path=zip_path, kecamatan=kecamatan)
        pois.to_file(output_path, layer="poi", driver="GPKG")
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    n_point = int((pois["source_layer"] == POI_POINT_LAYER).sum())
    n_area = len(pois) - n_point
    log_pipeline_run(
        PIPELINE_NAME,
        len(pois),
        "success",
        detail=(
            f"area={kecamatan or 'jabodetabek'} point={n_point} "
            f"area_poi={n_area} -> {output_path.name}"
        ),
    )
    return len(pois)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest POI OSM (SPEC 5.2c)")
    parser.add_argument("--kecamatan", help="Sample 1 kecamatan (kolom WADMKC)")
    args = parser.parse_args()
    n = main(kecamatan=args.kecamatan)
    print(f"POI tersimpan: {n} baris -> {POI_OUTPUT_PATH}")
