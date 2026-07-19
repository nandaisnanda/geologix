"""Unit test 3 detektor Pipeline 1 — SPEC.md Bagian 3.1-3.3.

Graph sintetis dibangun manual (MultiDiGraph + koordinat x/y) supaya tiap
kasus benar/salah bisa dipastikan secara matematis, sesuai prinsip SPEC 3:
graph theory dipilih justru karena punya ground truth pasti.
"""

import networkx as nx
import pytest
from shapely.geometry import Polygon

from src.pipeline_1_road_qa.detect_dangling_nodes import detect_dangling_nodes
from src.pipeline_1_road_qa.detect_disconnected import detect_disconnected
from src.pipeline_1_road_qa.detect_oneway_issues import detect_oneway_issues


def _add_twoway(G, u, v):
    G.add_edge(u, v, oneway=False)
    G.add_edge(v, u, oneway=False)


def _path_graph_twoway(node_coords):
    """Jalan dua-arah a-b-c-...: MultiDiGraph dengan koordinat node."""
    G = nx.MultiDiGraph()
    for node, (x, y) in node_coords.items():
        G.add_node(node, x=x, y=y)
    nodes = list(node_coords)
    for u, v in zip(nodes, nodes[1:]):
        _add_twoway(G, u, v)
    return G


# --- 3.1 Dangling node: degree(v) = 1 tanpa memandang arah ---

def test_dangling_ujung_jalan_dua_arah_terdeteksi():
    # a-b-c dua-arah: di MultiDiGraph degree a = 2 (in+out), tapi definisi
    # 3.1 (tanpa arah) -> degree 1. Kedua ujung (a, c) harus terdeteksi.
    G = _path_graph_twoway({"a": (0, 0), "b": (1, 0), "c": (2, 0)})
    ids = {f["osm_node_id"] for f in detect_dangling_nodes(G)}
    assert ids == {"a", "c"}


def test_dangling_kecualikan_turning_circle():
    # SPEC 3.1: cul-de-sac asli (tag highway=turning_circle) bukan error.
    G = _path_graph_twoway({"a": (0, 0), "b": (1, 0), "c": (2, 0)})
    G.nodes["c"]["highway"] = "turning_circle"
    ids = {f["osm_node_id"] for f in detect_dangling_nodes(G)}
    assert ids == {"a"}


def test_dangling_kecualikan_artefak_luar_boundary():
    G = _path_graph_twoway({"a": (0, 0), "b": (1, 0), "c": (5, 0)})  # c di luar
    boundary = Polygon([(-1, -1), (2, -1), (2, 1), (-1, 1)])
    ids = {f["osm_node_id"] for f in detect_dangling_nodes(G, boundary=boundary)}
    assert ids == {"a"}


def test_dangling_dianotasi_kelas_highway_edge():
    # Kelas jalan edge yang menempel ikut di temuan (utk kebijakan persistensi
    # runner — bukan bagian deteksi SPEC 3.1). List OSMnx -> elemen pertama.
    G = _path_graph_twoway({"a": (0, 0), "b": (1, 0), "c": (2, 0)})
    for u, v, k in G.edges(keys=True):
        G.edges[u, v, k]["highway"] = "primary" if {u, v} == {"a", "b"} else ["residential", "service"]
    by_id = {f["osm_node_id"]: f for f in detect_dangling_nodes(G)}
    assert by_id["a"]["highway"] == "primary"
    assert by_id["c"]["highway"] == "residential"


def test_split_dangling_kebijakan_persistensi():
    from src.pipeline_1_road_qa.__main__ import MAJOR_HIGHWAY_CLASSES, split_dangling

    findings = [
        {"osm_node_id": 1, "highway": "primary"},
        {"osm_node_id": 2, "highway": "residential"},
        {"osm_node_id": 3, "highway": None},
        {"osm_node_id": 4, "highway": "tertiary_link"},
    ]
    assert "tertiary_link" in MAJOR_HIGHWAY_CLASSES
    kept, skipped = split_dangling(findings, "major")
    assert [f["osm_node_id"] for f in kept] == [1, 4] and skipped == 2
    kept, skipped = split_dangling(findings, "all")
    assert len(kept) == 4 and skipped == 0
    kept, skipped = split_dangling(findings, "none")
    assert kept == [] and skipped == 4
    with pytest.raises(ValueError):
        split_dangling(findings, "aneh")


def test_dangling_persimpangan_bukan_temuan():
    # Node tengah persimpangan (degree 3) dan node jalur (degree 2) bukan dangling.
    G = _path_graph_twoway({"a": (0, 0), "b": (1, 0), "c": (2, 0)})
    G.add_node("d", x=1, y=1)
    _add_twoway(G, "b", "d")
    findings = detect_dangling_nodes(G)
    assert {f["osm_node_id"] for f in findings} == {"a", "c", "d"}
    assert all(f["error_type"] == "dangling_node" for f in findings)


# --- 3.2 Disconnected component: n > 1 dan |Ci| kecil relatif |Cmax| ---

def _two_component_graph(n_big=10, n_small=2):
    G = nx.MultiDiGraph()
    big = [f"b{i}" for i in range(n_big)]
    small = [f"s{i}" for i in range(n_small)]
    for i, n in enumerate(big + small):
        G.add_node(n, x=float(i), y=0.0)
    for u, v in zip(big, big[1:]):
        _add_twoway(G, u, v)
    for u, v in zip(small, small[1:]):
        _add_twoway(G, u, v)
    return G


def test_disconnected_komponen_kecil_terdeteksi():
    G = _two_component_graph(n_big=10, n_small=2)  # rasio 0.2
    findings = detect_disconnected(G, min_ratio=0.3)
    assert len(findings) == 1
    f = findings[0]
    assert f["component_size"] == 2
    assert f["size_ratio"] == pytest.approx(0.2)
    assert f["error_type"] == "disconnected_component"
    assert f["osm_node_id"] == "s0"  # representatif deterministik (min)


def test_disconnected_rasio_di_atas_threshold_tidak_diflag():
    G = _two_component_graph(n_big=10, n_small=2)
    assert detect_disconnected(G, min_ratio=0.1) == []  # 0.2 >= 0.1


def test_disconnected_graph_utuh_tanpa_temuan():
    # Syarat SPEC 3.2: n > 1. Satu komponen -> tidak ada temuan.
    G = _path_graph_twoway({"a": (0, 0), "b": (1, 0), "c": (2, 0)})
    assert detect_disconnected(G, min_ratio=0.9) == []


# --- 3.3 Oneway/SCC (Tarjan): edge oneway lintas-SCC = arah dicurigai salah ---

def test_oneway_edge_tanpa_jalan_balik_terdeteksi():
    # Siklus a->b->c->a (satu SCC) + oneway c->d tanpa path balik dari d.
    G = nx.MultiDiGraph()
    for i, n in enumerate("abcd"):
        G.add_node(n, x=float(i), y=0.0)
    for u, v in [("a", "b"), ("b", "c"), ("c", "a")]:
        G.add_edge(u, v, oneway=True, osmid=100)
    G.add_edge("c", "d", oneway=True, osmid=200)
    findings = detect_oneway_issues(G)
    assert len(findings) == 1
    f = findings[0]
    assert (f["osm_node_id"], f["osm_way_id"]) == ("c", 200)
    assert f["error_type"] == "oneway_inconsistency"


def test_oneway_siklus_konsisten_tanpa_temuan():
    G = nx.MultiDiGraph()
    for i, n in enumerate("abc"):
        G.add_node(n, x=float(i), y=0.0)
    for u, v in [("a", "b"), ("b", "c"), ("c", "a")]:
        G.add_edge(u, v, oneway=True, osmid=100)
    assert detect_oneway_issues(G) == []


def test_oneway_jalan_dua_arah_tidak_pernah_diflag():
    # Ujung jalan dua-arah beda SCC? Tidak mungkin — dan kalaupun graph aneh,
    # edge non-oneway tetap dilewati.
    G = _path_graph_twoway({"a": (0, 0), "b": (1, 0)})
    assert detect_oneway_issues(G) == []


def test_oneway_osmid_list_diambil_elemen_pertama():
    # Simplifikasi OSMnx bisa merge beberapa way -> osmid berupa list.
    G = nx.MultiDiGraph()
    G.add_node("a", x=0.0, y=0.0)
    G.add_node("b", x=1.0, y=0.0)
    G.add_edge("a", "b", oneway=True, osmid=[11, 22])
    f = detect_oneway_issues(G)[0]
    assert f["osm_way_id"] == 11
