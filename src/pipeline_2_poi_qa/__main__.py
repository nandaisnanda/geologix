"""Runner Pipeline 2 — POI Validation (SPEC.md Bagian 8, step 8-10).

Orkestrasi: muat POI (GPKG hasil ``fetch_osm_poi.py`` atau langsung dari
.shp.zip) -> jarak Haversine ke jalan terdekat (SPEC Bagian 3 Pipeline 2.1)
-> deteksi outlier IQR (2.2) -> simpan ke ``poi_anomalies`` -> log run ke
``pipeline_logs`` (SPEC 5.3). File runner (``__main__.py``) di luar daftar
SPEC 5.1 — keputusan minimal yang sama dengan Pipeline 1, dicatat PROGRESS.md.

Pemakaian::

    python -m src.pipeline_2_poi_qa                       # GPKG jabodetabek
    python -m src.pipeline_2_poi_qa --kecamatan Menteng   # sample dari .shp.zip

Jalan dibaca dari layer ``gis_osm_roads_free_1`` .shp.zip dengan bbox POI +
margin ``BBOX_MARGIN_DEG`` supaya jalan tepat di luar tepi bbox tetap jadi
kandidat terdekat (hindari jarak menggelembung artifisial di tepi area).
"""

import argparse

import geopandas as gpd

from src.data_ingestion.fetch_osm_poi import POI_OUTPUT_PATH, load_pois
from src.db.writer import log_pipeline_run, save_poi_anomalies
from src.pipeline_2_poi_qa.detect_outliers import detect_outliers
from src.pipeline_2_poi_qa.spatial_join import load_roads, nearest_road_distances

PIPELINE_NAME = "pipeline_2_poi_qa"

# ~5.5 km di ekuator — jauh melebihi jarak POI->jalan wajar di Jabodetabek.
BBOX_MARGIN_DEG = 0.05


def run(pois: gpd.GeoDataFrame, roads: gpd.GeoDataFrame, engine=None) -> dict:
    """Jalankan join jarak + deteksi IQR + simpan hasil + log. Return ringkasan."""
    joined = nearest_road_distances(pois, roads)
    findings, bounds = detect_outliers(joined)
    n_saved = save_poi_anomalies(findings, engine=engine)
    summary = {
        "n_poi": len(pois),
        "n_roads": len(roads),
        "q1_m": round(bounds["q1"], 2),
        "q3_m": round(bounds["q3"], 2),
        "upper_bound_m": round(bounds["upper_bound"], 2),
        "outliers": len(findings),
        "saved": n_saved,
    }
    log_pipeline_run(
        PIPELINE_NAME,
        len(findings),
        "success",
        detail=(
            f"poi={summary['n_poi']} roads={summary['n_roads']} "
            f"q1={summary['q1_m']}m q3={summary['q3_m']}m "
            f"upper={summary['upper_bound_m']}m outliers={len(findings)}"
        ),
        engine=engine,
    )
    return summary


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Pipeline 2 - POI Validation")
    parser.add_argument(
        "--gpkg",
        default=str(POI_OUTPUT_PATH),
        help="path GPKG hasil fetch_osm_poi (default: data/raw/poi_jabodetabek.gpkg)",
    )
    parser.add_argument(
        "--kecamatan",
        help="baca POI 1 kecamatan langsung dari .shp.zip (abaikan --gpkg)",
    )
    args = parser.parse_args(argv)

    try:
        pois = (
            load_pois(kecamatan=args.kecamatan)
            if args.kecamatan
            else gpd.read_file(args.gpkg, layer="poi")
        )
        minx, miny, maxx, maxy = pois.total_bounds
        roads = load_roads(
            bbox=(
                minx - BBOX_MARGIN_DEG,
                miny - BBOX_MARGIN_DEG,
                maxx + BBOX_MARGIN_DEG,
                maxy + BBOX_MARGIN_DEG,
            )
        )
        summary = run(pois, roads)
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    print(summary)
    return summary


if __name__ == "__main__":
    main()
