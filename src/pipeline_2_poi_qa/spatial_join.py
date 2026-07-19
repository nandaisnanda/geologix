"""Jarak Haversine tiap POI ke jalan terdekat — SPEC.md Bagian 3, Pipeline 2.1.

Rumus persis SPEC 2.1 (koordinat WGS84 lat/lon, bukan Euclidean biasa):

    a = sin²(Δφ/2) + cos(φ1)·cos(φ2)·sin²(Δλ/2)
    c = 2·atan2(√a, √(1−a))
    d = R·c

dengan ``R = EARTH_RADIUS_KM = 6371`` dari ``config`` (φ = latitude radian,
Δλ = selisih longitude radian).

Sumber jalan: layer ``gis_osm_roads_free_1`` dari ``java-latest-free.shp.zip``
yang SAMA dengan sumber POI — Pipeline 2 hanya butuh geometri jalan (bukan
topologi graph), jadi tetap sepenuhnya di jalur shapefile sesuai pemisahan dua
sumber OSM di SPEC.md Bagian 5.2c; jalur ``.pbf`` khusus Pipeline 1.

Mekanisme: kandidat jalan terdekat dicari via spatial index STRtree
(``roads.sindex.nearest``) dalam ruang derajat lat/lon, titik terdekat pada
geometri jalan diambil dengan ``shapely.shortest_line``, lalu jaraknya dihitung
Haversine. Anisotropi derajat lat/lon di lintang Jabodetabek (~-6°,
cos φ ≈ 0.995) terlalu kecil untuk mengubah kandidat jalan yang terpilih.
"""

import geopandas as gpd
import numpy as np
import shapely

from src import config
from src.data_ingestion.fetch_osm_poi import SHP_ZIP_PATH

ROADS_LAYER = "gis_osm_roads_free_1"
ROAD_COLUMNS = ["osm_id", "fclass", "name"]

_DISTANCE_COLUMNS = ["nearest_road_osm_id", "nearest_road_fclass", "distance_to_road_m"]


def haversine_km(lat1, lon1, lat2, lon2):
    """Jarak Haversine dalam km — rumus persis SPEC 2.1, vectorized numpy."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = phi2 - phi1
    dlam = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return config.EARTH_RADIUS_KM * c


def load_roads(zip_path=None, bbox=None) -> gpd.GeoDataFrame:
    """Baca layer jalan dari .shp.zip Geofabrik (sumber sama dengan POI, 5.2c)."""
    zip_path = zip_path or SHP_ZIP_PATH
    gdf = gpd.read_file(zip_path, layer=ROADS_LAYER, bbox=bbox)
    keep = [c for c in ROAD_COLUMNS if c in gdf.columns]
    return gdf[keep + [gdf.geometry.name]]


def nearest_road_distances(
    pois: gpd.GeoDataFrame, roads: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Return salinan ``pois`` + kolom jalan terdekat dan jarak Haversine (meter).

    Kolom baru: ``nearest_road_osm_id``, ``nearest_road_fclass``,
    ``distance_to_road_m`` (satuan meter, konsisten kolom
    ``poi_anomalies.distance_to_road_m`` di ``db/models.py``).
    """
    if roads.empty:
        raise ValueError("GeoDataFrame jalan kosong — tidak ada acuan jarak")
    out = pois.copy()
    if pois.empty:
        for col in _DISTANCE_COLUMNS:
            out[col] = []
        return out

    poi_pos, road_pos = roads.sindex.nearest(pois.geometry, return_all=False)
    poi_geoms = pois.geometry.values[poi_pos]
    road_geoms = roads.geometry.values[road_pos]

    # Titik terdekat pada geometri jalan (ujung kedua shortest_line), lalu
    # jarak POI -> titik itu dihitung Haversine (SPEC 2.1).
    nearest_pts = shapely.get_point(shapely.shortest_line(poi_geoms, road_geoms), 1)
    d_km = haversine_km(
        shapely.get_y(poi_geoms),
        shapely.get_x(poi_geoms),
        shapely.get_y(nearest_pts),
        shapely.get_x(nearest_pts),
    )

    n = len(pois)
    dist_m = np.full(n, np.nan)
    dist_m[poi_pos] = d_km * 1000.0
    road_ids = np.full(n, None, dtype=object)
    road_ids[poi_pos] = roads["osm_id"].values[road_pos]
    road_fclass = np.full(n, None, dtype=object)
    if "fclass" in roads.columns:
        road_fclass[poi_pos] = roads["fclass"].values[road_pos]

    out["nearest_road_osm_id"] = road_ids
    out["nearest_road_fclass"] = road_fclass
    out["distance_to_road_m"] = dist_m
    return out
