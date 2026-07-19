"""Unit test graph_builder.py — SPEC.md Bagian 3 Pipeline 1 (representasi G=(V,E) berarah)."""

import textwrap

import pytest

from src.pipeline_1_road_qa import graph_builder

OSM_XML_DUA_KOMPONEN = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <osm version="0.6" generator="test">
      <node id="1" lat="-6.2000" lon="106.8000"/>
      <node id="2" lat="-6.2000" lon="106.8100"/>
      <node id="3" lat="-6.2100" lon="106.8100"/>
      <node id="4" lat="-6.3000" lon="106.9000"/>
      <node id="5" lat="-6.3000" lon="106.9100"/>
      <way id="10">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/>
        <tag k="highway" v="residential"/>
      </way>
      <way id="11">
        <nd ref="4"/><nd ref="5"/>
        <tag k="highway" v="residential"/>
      </way>
    </osm>
    """)


@pytest.fixture
def xml_path(tmp_path):
    p = tmp_path / "sample.osm"
    p.write_text(OSM_XML_DUA_KOMPONEN, encoding="utf-8")
    return p


def test_build_graph_from_xml_berarah_dan_tersimplifikasi(xml_path):
    G = graph_builder.build_graph_from_xml(xml_path)

    assert G.is_directed()
    assert G.is_multigraph()
    # Node 2 interstisial (degree-2) di-merge oleh simplify; endpoint tetap ada.
    assert set(G.nodes) == {1, 3, 4, 5}
    # Jalan residential dua arah -> tiap way jadi sepasang edge bolak-balik.
    assert G.number_of_edges() == 4


def test_retain_all_menjaga_disconnected_component(xml_path):
    """Kritis untuk Bagian 3.2: komponen kecil TIDAK boleh dibuang saat build."""
    import networkx as nx

    G = graph_builder.build_graph_from_xml(xml_path)
    n_komponen = nx.number_weakly_connected_components(G)
    assert n_komponen == 2  # way 10 dan way 11 terpisah, dua-duanya harus ada


def test_load_kecamatan_boundary_tidak_ditemukan():
    with pytest.raises(ValueError, match="tidak ditemukan"):
        graph_builder.load_kecamatan_boundary("KecamatanFiktifXYZ")


def test_graph_summary(xml_path):
    G = graph_builder.build_graph_from_xml(xml_path)
    s = graph_builder.graph_summary(G)
    assert s == {"n_nodes": 4, "n_edges": 4, "is_directed": True}
