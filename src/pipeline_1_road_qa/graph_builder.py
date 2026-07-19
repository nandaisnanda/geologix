"""Bangun graph jalan berarah dari data OSM — SPEC.md Bagian 3, Pipeline 1.

Representasi data sesuai SPEC.md Bagian 3 (Pipeline 1 — Road Network QA):
jaringan jalan sebagai graph berarah ``G = (V, E)`` dengan ``V`` = node
(persimpangan/titik jalan) dan ``E`` = edge (ruas jalan) beratribut arah
(oneway/two-way). Dibangun memakai OSMnx (SPEC.md Bagian 8, step 4) sebagai
``networkx.MultiDiGraph`` — input untuk deteksi dangling node (3.1),
disconnected component (3.2), dan oneway/SCC (3.3).

Dua jalur input, dua tujuan:
- ``build_graph_from_xml``     -> produksi/CI: dari ``jabodetabek.osm.pbf`` hasil
  ``fetch_osm.py``. WAJIB dari ``.pbf`` (bukan shapefile) demi validitas
  topologi — SPEC.md 5.2c. Konversi WAJIB dua tahap::

      osmium tags-filter jabodetabek.osm.pbf w/highway -o roads.osm.pbf
      osmium cat roads.osm.pbf -o roads.osm

  ``tags-filter w/highway`` TIDAK boleh dilewati: ``graph_from_xml`` menelan
  SEMUA way di file (bangunan, sungai, pagar) dan simplifikasi bisa melebur
  ruas jalan dengan segmen non-jalan jadi satu edge (terverifikasi empiris)
  -> dangling node & disconnected component palsu massal di deteksi 3.1-3.2.
- ``build_graph_from_polygon`` -> dev/sample: fetch langsung via Overpass untuk
  area kecil (1 kecamatan, SPEC.md Bagian 8 Fase 0 langkah 3).

PERHATIAN inkonsistensi filter sample vs produksi: jalur polygon memakai
``network_type="drive"`` (hanya jalan kendaraan), sedangkan filter
``w/highway`` di jalur produksi masih memuat footway/cycleway/steps.
Saat runner CI dibuat (Fase 4), selaraskan filter osmium ke subset highway
drivable supaya hasil validasi manual sample merepresentasikan produksi.

Parameter penting (bukan default OSMnx):
- ``retain_all=True`` — default OSMnx hanya menyimpan komponen terhubung
  terbesar; itu justru MEMBUANG disconnected component yang mau dideteksi
  di Bagian 3 Pipeline 1.2. Wajib True.
- ``simplify=True`` — node interstisial degree-2 (titik bentuk geometri) di-
  merge; endpoint jalan buntu tetap tersimpan sehingga deteksi dangling (3.1)
  tidak terpengaruh, dan graph jauh lebih kecil.

CATATAN degree untuk implementasi 3.1 (``detect_dangling_nodes.py``):
SPEC 3.1 mendefinisikan ``degree(v)`` TANPA memandang arah. Di MultiDiGraph,
ujung jalan buntu dua-arah ber-degree 2 (1 in + 1 out), dan
``G.to_undirected()`` masih MultiGraph dengan 2 edge paralel (degree tetap 2).
Deteksi WAJIB collapse ke simple undirected graph dulu::

    nx.Graph(G.to_undirected())   # baru degree(v) == 1 bermakna dangling

Memakai ``G.degree(v) == 1`` langsung pada MultiDiGraph = nol temuan (salah).
"""

from pathlib import Path

import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import MultiPolygon, Polygon

from src import config

BOUNDARY_SHP_PATH = config.BOUNDARIES_DIR / "jabodetabek.shp"


def build_graph_from_xml(filepath: str | Path) -> nx.MultiDiGraph:
    """Bangun MultiDiGraph dari file OSM XML (jalur produksi, dari .pbf)."""
    return ox.graph_from_xml(filepath, simplify=True, retain_all=True)


def build_graph_from_polygon(
    polygon: Polygon | MultiPolygon, network_type: str = "drive"
) -> nx.MultiDiGraph:
    """Bangun MultiDiGraph via Overpass untuk area kecil (sample kecamatan)."""
    ox.settings.cache_folder = config.RAW_DATA_DIR / "osmnx_cache"
    return ox.graph_from_polygon(
        polygon,
        network_type=network_type,
        simplify=True,
        retain_all=True,
        truncate_by_edge=True,
    )


def load_kecamatan_boundary(kecamatan: str) -> Polygon | MultiPolygon:
    """Ambil poligon 1 kecamatan (kolom WADMKC) dari shapefile boundary.

    Untuk sample uji coba skala kecil sebelum full-scale — SPEC.md Bagian 8,
    Fase 0 langkah 3.
    """
    gdf = gpd.read_file(BOUNDARY_SHP_PATH)
    subset = gdf[gdf["WADMKC"].str.casefold() == kecamatan.casefold()]
    if subset.empty:
        raise ValueError(f"Kecamatan {kecamatan!r} tidak ditemukan di kolom WADMKC")
    return subset.geometry.union_all()


def graph_summary(G: nx.MultiDiGraph) -> dict:
    """Ringkasan graph untuk logging pipeline_logs (SPEC.md Bagian 5.3)."""
    return {
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "is_directed": G.is_directed(),
    }
