"""Runner Pipeline 1 — Road Network QA (SPEC.md Bagian 8, step 4-6).

Orkestrasi: bangun/muat graph -> 3 deteksi (SPEC Bagian 3.1-3.3) -> simpan ke
tabel ``road_errors`` -> log run ke ``pipeline_logs`` (SPEC 5.3). File runner
(``__main__.py``) bukan bagian daftar file SPEC 5.1 — keputusan implementasi
minimal supaya pipeline bisa dipanggil satu perintah, dicatat di PROGRESS.md.

Pemakaian::

    python -m src.pipeline_1_road_qa --graphml data/raw/sample_menteng.graphml \
        --kecamatan Menteng
    python -m src.pipeline_1_road_qa --xml data/raw/roads.osm \
        --boundary-jabodetabek --dangling-persist major   # jalur CI full-area

Boundary (``--kecamatan`` utk sample, ``--boundary-jabodetabek`` utk full-area)
mengecualikan dangling node artefak pemotongan area — node hasil clip osmium
jatuh di luar poligon administratif (lihat ``detect_dangling_nodes.py``).

KEBIJAKAN PERSISTENSI DANGLING (keputusan proyek 2026-07-20, utang PROGRESS.md;
deteksi tetap persis SPEC 3.1 — ini hanya soal apa yang DISIMPAN ke DB):
run full-area pertama menghasilkan 182.848 dangling (26% node) yang didominasi
ujung gang/cul-de-sac perumahan tanpa tag turning_circle — bukan error yang
bisa ditindaklanjuti, dan ±730rb baris/minggu tidak berkelanjutan di DB.
``--dangling-persist``:

- ``all``   (default): simpan semua — perilaku lama, utk sample/validasi.
- ``major``: simpan hanya dangling di kelas jalan besar (motorway..tertiary
  + link) — dead-end di jalan arteri = kemungkinan besar error data nyata;
  dangling kelas kecil tetap DIHITUNG dan dicatat di detail pipeline_logs.
- ``none``: tidak simpan dangling sama sekali (statistik di log saja).

``jumlah_temuan`` di pipeline_logs = temuan TERSIMPAN (actionable); hitungan
deteksi penuh selalu ada di kolom detail.
"""

import argparse

import networkx as nx
import osmnx as ox

from src.db.writer import log_pipeline_run, save_road_errors
from src.pipeline_1_road_qa.detect_dangling_nodes import detect_dangling_nodes
from src.pipeline_1_road_qa.detect_disconnected import detect_disconnected
from src.pipeline_1_road_qa.detect_oneway_issues import detect_oneway_issues
from src.pipeline_1_road_qa.graph_builder import (
    build_graph_from_xml,
    graph_summary,
    load_kecamatan_boundary,
)

PIPELINE_NAME = "pipeline_1_road_qa"

# Kelas jalan "besar" utk kebijakan persist=major (subset drivable filter CI).
MAJOR_HIGHWAY_CLASSES = {
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
}


def split_dangling(findings: list[dict], persist: str) -> tuple[list[dict], int]:
    """Pisahkan dangling yang disimpan vs hanya dihitung.

    Return (tersimpan, jumlah_tidak_tersimpan). ``persist``: all|major|none.
    """
    if persist == "all":
        return findings, 0
    if persist == "none":
        return [], len(findings)
    if persist == "major":
        kept = [f for f in findings if f.get("highway") in MAJOR_HIGHWAY_CLASSES]
        return kept, len(findings) - len(kept)
    raise ValueError(f"dangling-persist tak dikenal: {persist!r}")


def run(
    G: nx.MultiDiGraph,
    boundary=None,
    engine=None,
    dangling_persist: str = "all",
) -> dict:
    """Jalankan 3 deteksi + simpan hasil + log. Return ringkasan run."""
    dangling = detect_dangling_nodes(G, boundary=boundary)
    dangling_saved, n_dangling_skipped = split_dangling(dangling, dangling_persist)
    disconnected = detect_disconnected(G)
    oneway = detect_oneway_issues(G)
    findings = dangling_saved + disconnected + oneway

    n_saved = save_road_errors(findings, engine=engine)
    summary = {
        **graph_summary(G),
        "dangling_node": len(dangling),
        "dangling_saved": len(dangling_saved),
        "disconnected_component": len(disconnected),
        "oneway_inconsistency": len(oneway),
        "total": len(findings),
        "saved": n_saved,
    }
    log_pipeline_run(
        PIPELINE_NAME,
        len(findings),
        "success",
        detail=(
            f"nodes={summary['n_nodes']} edges={summary['n_edges']} "
            f"dangling={len(dangling)} dangling_saved={len(dangling_saved)} "
            f"(persist={dangling_persist}, skipped={n_dangling_skipped}) "
            f"disconnected={len(disconnected)} oneway={len(oneway)}"
        ),
        engine=engine,
    )
    return summary


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Pipeline 1 - Road Network QA")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--graphml", help="path graph OSMnx tersimpan (.graphml)")
    source.add_argument("--xml", help="path OSM XML hasil filter .pbf (lihat graph_builder)")
    area = parser.add_mutually_exclusive_group()
    area.add_argument("--kecamatan", help="nama kecamatan (WADMKC) untuk boundary artefak")
    area.add_argument(
        "--boundary-jabodetabek",
        action="store_true",
        help="pakai dissolve seluruh Jabodetabek sebagai boundary artefak (jalur CI)",
    )
    parser.add_argument(
        "--dangling-persist",
        choices=["all", "major", "none"],
        default="all",
        help="kebijakan simpan dangling ke DB (lihat docstring modul)",
    )
    args = parser.parse_args(argv)

    try:
        G = (
            ox.load_graphml(args.graphml)
            if args.graphml
            else build_graph_from_xml(args.xml)
        )
        if args.boundary_jabodetabek:
            # REUSE dissolve boundary P3 (sumber shp sama utk semua pipeline).
            from src.pipeline_3_weather_risk.h3_grid import load_boundary_polygon

            boundary = load_boundary_polygon()
        elif args.kecamatan:
            boundary = load_kecamatan_boundary(args.kecamatan)
        else:
            boundary = None
        summary = run(G, boundary=boundary, dangling_persist=args.dangling_persist)
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    print(summary)
    return summary


if __name__ == "__main__":
    main()
