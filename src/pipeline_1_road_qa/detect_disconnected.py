"""Deteksi disconnected component — implementasi SPEC.md Bagian 3, Pipeline 1.2.

Definisi persis SPEC 3.2: graph dipecah jadi connected component
``C1..Cn`` memakai BFS/DFS (di sini: ``networkx.connected_components`` pada
graph undirected — implementasi BFS), lalu komponen dicurigai terisolasi jika::

    n > 1  DAN  |Ci| kecil relatif terhadap |Ci| terbesar

"Kecil relatif" dioperasionalkan sebagai ``|Ci| / |Cmax| < min_ratio``.
SPEC 3.2 tidak menetapkan angka pasti — default diambil dari
``config.DISCONNECTED_COMPONENT_MIN_RATIO`` (0.05, PLACEHOLDER yang wajib
divalidasi manual di Fase 1, lihat PROGRESS.md).

Konektivitas dihitung tanpa memandang arah (collapse ``nx.Graph(G)``) —
keterputusan topologi adalah soal ada/tidaknya sambungan fisik, bukan arah;
kesalahan arah ditangani terpisah oleh SCC di 3.3.

Output: SATU temuan per komponen terisolasi (bukan per node), diwakili node
pertama komponen. Severity: ``high`` — subjaringan terisolasi berarti seluruh
area tidak terjangkau routing, dampaknya lebih luas dari satu node dangling.
"""

import networkx as nx

from src import config

ERROR_TYPE = "disconnected_component"
SEVERITY = "high"


def detect_disconnected(
    G: nx.MultiDiGraph,
    min_ratio: float | None = None,
) -> list[dict]:
    """Return temuan komponen terisolasi, satu dict per komponen.

    Tiap dict: ``osm_node_id`` (node representatif), ``error_type``,
    ``severity``, ``lon``, ``lat``, ``component_size``, ``size_ratio``.
    """
    if min_ratio is None:
        min_ratio = config.DISCONNECTED_COMPONENT_MIN_RATIO

    simple = nx.Graph(G)
    components = sorted(nx.connected_components(simple), key=len, reverse=True)
    if len(components) <= 1:  # syarat SPEC 3.2: n > 1
        return []

    max_size = len(components[0])
    findings = []
    for comp in components[1:]:
        ratio = len(comp) / max_size
        if ratio >= min_ratio:
            continue
        rep = min(comp)  # deterministik antar-run
        data = G.nodes[rep]
        findings.append(
            {
                "osm_node_id": rep,
                "error_type": ERROR_TYPE,
                "severity": SEVERITY,
                "lon": data["x"],
                "lat": data["y"],
                "component_size": len(comp),
                "size_ratio": ratio,
            }
        )
    return findings
