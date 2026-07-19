"""Runner Pipeline 1 — Road Network QA (SPEC.md Bagian 8, step 4-6).

Orkestrasi: bangun/muat graph -> 3 deteksi (SPEC Bagian 3.1-3.3) -> simpan ke
tabel ``road_errors`` -> log run ke ``pipeline_logs`` (SPEC 5.3). File runner
(``__main__.py``) bukan bagian daftar file SPEC 5.1 — keputusan implementasi
minimal supaya pipeline bisa dipanggil satu perintah, dicatat di PROGRESS.md.

Pemakaian::

    python -m src.pipeline_1_road_qa --graphml data/raw/sample_menteng.graphml \
        --kecamatan Menteng
    python -m src.pipeline_1_road_qa --xml data/raw/roads.osm   # jalur CI (.pbf)

``--kecamatan`` memuat polygon boundary dari shapefile untuk mengecualikan
dangling node artefak pemotongan area (lihat ``detect_dangling_nodes.py``).
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


def run(G: nx.MultiDiGraph, boundary=None, engine=None) -> dict:
    """Jalankan 3 deteksi + simpan hasil + log. Return ringkasan run."""
    dangling = detect_dangling_nodes(G, boundary=boundary)
    disconnected = detect_disconnected(G)
    oneway = detect_oneway_issues(G)
    findings = dangling + disconnected + oneway

    n_saved = save_road_errors(findings, engine=engine)
    summary = {
        **graph_summary(G),
        "dangling_node": len(dangling),
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
            f"dangling={len(dangling)} disconnected={len(disconnected)} "
            f"oneway={len(oneway)}"
        ),
        engine=engine,
    )
    return summary


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Pipeline 1 - Road Network QA")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--graphml", help="path graph OSMnx tersimpan (.graphml)")
    source.add_argument("--xml", help="path OSM XML hasil filter .pbf (lihat graph_builder)")
    parser.add_argument("--kecamatan", help="nama kecamatan (WADMKC) untuk boundary artefak")
    args = parser.parse_args(argv)

    try:
        G = (
            ox.load_graphml(args.graphml)
            if args.graphml
            else build_graph_from_xml(args.xml)
        )
        boundary = (
            load_kecamatan_boundary(args.kecamatan) if args.kecamatan else None
        )
        summary = run(G, boundary=boundary)
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    print(summary)
    return summary


if __name__ == "__main__":
    main()
