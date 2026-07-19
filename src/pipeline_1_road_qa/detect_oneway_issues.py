"""Deteksi inkonsistensi arah jalan (oneway) — SPEC.md Bagian 3, Pipeline 1.3.

Definisi persis SPEC 3.3: hitung Strongly Connected Component (SCC) graph
berarah memakai **algoritma Tarjan** (``networkx.strongly_connected_components``
adalah implementasi Tarjan non-rekursif), lalu flag edge oneway yang membuat
node tidak bisa dijangkau balik — yaitu edge yang menyeberang antar-SCC
(``scc[u] != scc[v]``): tidak ada strongly connected path kembali dari ``v``
ke ``u``, indikasi kemungkinan arah terbalik di data OSM.

Catatan: edge dua-arah tidak mungkin menyeberang SCC (pasangan edge
kebalikannya menjamin u,v satu SCC), jadi hanya edge ber-atribut oneway yang
dicek. Node di komponen yang memang terputus total sudah ditangani 3.2 —
temuan di sini terbatas pada edge oneway penyebab ketakterjangkauan balik.

Severity: ``high`` — arah salah menyesatkan navigasi secara aktif (rute
memutar/ilegal), lebih berbahaya daripada jalan buntu pasif.
"""

import networkx as nx

ERROR_TYPE = "oneway_inconsistency"
SEVERITY = "high"


def detect_oneway_issues(G: nx.MultiDiGraph) -> list[dict]:
    """Return temuan edge oneway lintas-SCC, satu dict per edge.

    Tiap dict: ``osm_node_id`` (node asal ``u``), ``osm_way_id`` (osmid way),
    ``error_type``, ``severity``, ``lon``, ``lat`` (koordinat node asal).
    """
    scc_id: dict = {}
    for i, comp in enumerate(nx.strongly_connected_components(G)):  # Tarjan, SPEC 3.3
        for node in comp:
            scc_id[node] = i

    findings = []
    for u, v, data in G.edges(data=True):
        if not data.get("oneway"):
            continue
        if scc_id[u] == scc_id[v]:
            continue  # ada path balik v->u, arah konsisten
        osmid = data.get("osmid")
        if isinstance(osmid, (list, tuple)):  # hasil merge simplifikasi OSMnx
            osmid = osmid[0]
        node_data = G.nodes[u]
        findings.append(
            {
                "osm_node_id": u,
                "osm_way_id": osmid,
                "error_type": ERROR_TYPE,
                "severity": SEVERITY,
                "lon": node_data["x"],
                "lat": node_data["y"],
            }
        )
    return findings
