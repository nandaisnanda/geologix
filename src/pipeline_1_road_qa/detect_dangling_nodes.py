"""Deteksi dangling node — implementasi SPEC.md Bagian 3, Pipeline 1.1.

Definisi persis SPEC 3.1: node ``v`` dangling jika ``degree(v) = 1``, dengan
``degree(v)`` = jumlah edge terhubung TANPA memandang arah. Karena input berupa
``MultiDiGraph`` (ujung jalan dua-arah ber-degree 2: satu in + satu out, dan
``to_undirected()`` masih menyisakan 2 edge paralel), graph WAJIB di-collapse
dulu ke simple undirected graph: ``nx.Graph(G)`` — lihat catatan di
``graph_builder.py``.

Sesuai SPEC 3.1, degree=1 belum tentu error — cul-de-sac asli dikecualikan
lewat cek silang tag OSM ``highway=*``: node bertag ``turning_circle`` /
``turning_loop`` adalah ujung buntu yang disengaja, bukan kesalahan topologi.
Tambahan pengecualian (keputusan implementasi, dicatat di PROGRESS.md): node
degree-1 di LUAR polygon boundary adalah artefak pemotongan area
(``truncate_by_edge`` / clip osmium), bukan error data — dilewati jika
``boundary`` diberikan.

Severity: ``medium`` — temuan perlu review manusia (bisa jadi jalan belum
selesai dipetakan), tidak separah subjaringan terisolasi/arah salah.
"""

import networkx as nx
from shapely.geometry import MultiPolygon, Point, Polygon

from src import config

ERROR_TYPE = "dangling_node"
SEVERITY = "medium"

# Tag OSM highway=* penanda ujung buntu yang disengaja (cul-de-sac asli).
CULDESAC_HIGHWAY_TAGS = {"turning_circle", "turning_loop"}


def detect_dangling_nodes(
    G: nx.MultiDiGraph,
    boundary: Polygon | MultiPolygon | None = None,
) -> list[dict]:
    """Return temuan dangling node sebagai list dict siap tulis ke ``road_errors``.

    Tiap dict: ``osm_node_id``, ``error_type``, ``severity``, ``lon``, ``lat``.
    """
    simple = nx.Graph(G)  # collapse arah + edge paralel, sesuai definisi degree 3.1
    findings = []
    for node, degree in simple.degree():
        if degree != config.DANGLING_NODE_DEGREE:
            continue
        data = G.nodes[node]
        if data.get("highway") in CULDESAC_HIGHWAY_TAGS:
            continue  # cul-de-sac asli, bukan error (SPEC 3.1 cek silang tag)
        lon, lat = data["x"], data["y"]
        if boundary is not None and not boundary.contains(Point(lon, lat)):
            continue  # artefak pemotongan boundary, bukan error data
        findings.append(
            {
                "osm_node_id": node,
                "error_type": ERROR_TYPE,
                "severity": SEVERITY,
                "lon": lon,
                "lat": lat,
            }
        )
    return findings
