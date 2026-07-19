# Catatan Validasi Manual — Pipeline 2, Sample Menteng (SPEC 5.4)

Tanggal: 2026-07-19. Data: `java-latest-free.shp.zip` (Geofabrik, 2.24GB),
layer `gis_osm_pois_free_1` (titik) + `gis_osm_pois_a_free_1` (area →
`representative_point()`) + `gis_osm_roads_free_1` (jalan), clip Kecamatan
Menteng → 847 POI, 79.944 ruas jalan (bbox + margin 0.05°). Metode validasi:
bedah 32 outlier per layer/kategori + jarak-tepi-poligon untuk POI area, dan
cek silang POI titik terhadap OSM API live (`api.openstreetmap.org/api/0.6`).

## Hasil run (3x berturut-turut, deterministik — checklist 5.4 poin 1)
| Run | n_poi | Q1 | Q3 | batas atas | outliers | status |
|---|---|---|---|---|---|---|
| 1-3 (identik) | 847 | 8,93 m | 23,51 m | 45,40 m | 32 | success |

Tercatat di `pipeline_logs` (3 baris success, 2026-07-19 22:54-22:56 UTC) dan
`poi_anomalies` (96 baris = 32 × 3). Ingest penuh Jabodetabek juga sukses:
46.980 POI (22.097 titik + 24.883 area) → `data/raw/poi_jabodetabek.gpkg`,
log `poi_ingestion`.

Sanity statistik: Q1-Q3 (9-24 m) sesuai intuisi kota — mayoritas POI menempel
jaringan jalan; distribusi right-skewed, konsisten alasan pemilihan IQR di
SPEC (Bagian 3 P2.2).

## Komposisi 32 outlier
- 28 dari layer AREA, hanya 4 dari layer TITIK.
- Kategori dominan: swimming_pool (9), school (8), pitch (6) — semuanya objek
  berhalaman luas di tengah blok.

### POI area (28) — didominasi artefak `representative_point`
Untuk tiap outlier area dihitung juga jarak TEPI poligon asli → jalan:
| POI | d (rep. point) | d (tepi poligon) | Diagnosis |
|---|---|---|---|
| Plaza Indonesia (mall) | 83,1 m | 0,0 m | Poligon MENEMPEL jalan — murni artefak titik tengah |
| FK UI D-III (university) | 55,7 m | 0,0 m | sda. |
| Kolese Kanisius (school) | 46,9 m | 0,0 m | sda. |
| SMPN 1 Jakarta (school) | 49,9 m | 3,1 m | sda. (praktis menempel) |
| St. Theresia (school) | 63,7 m | 4,8 m | sda. |
| pitch 481759345 | 73,0 m | 62,0 m | Lapangan di tengah blok — jarak riil memang jauh |
| swimming_pool (9 objek) | 46-68 m | 36-59 m | Kolam privat dalam blok hunian — jarak riil jauh, tapi bukan kesalahan data |

**Diagnosis:** ~1/3 outlier area adalah kompleks besar yang tepinya menempel
jalan (jarak sebenarnya ≈ 0) — flag muncul semata karena jarak diukur dari
`representative_point` di tengah poligon. Sisanya (kolam/lapangan dalam blok)
jaraknya riil, tapi merupakan karakteristik objek (akses via persil privat),
bukan POI "melayang" salah posisi.

### POI titik (4 dari 4 dicek ke OSM live) — koordinat semua TERKONFIRMASI
| Node | d | Temuan OSM live |
|---|---|---|
| 7428358740 Apotek Guardian | 62,3 m | Ada, koordinat cocok — di DALAM Plaza Indonesia (POI indoor mall) |
| 5312068021 ATM HSBC | 55,0 m | Ada — juga indoor kompleks mall |
| 318076752 Monumen Selamat Datang | 49,7 m | Ada (wikidata Q2573410) — di TENGAH Bundaran HI, memang ±50 m dari jalur jalan |
| 13946800201 SDN 03 MENTENG | 46,0 m | Ada, `addr:street=Jalan Cilacap` — titik ditaruh di tengah gedung dalam blok |

**Diagnosis:** keempatnya POI sah dengan jarak yang terukur BENAR — outlier
menangkap POI indoor/tengah-blok/tengah-bundaran, bukan kesalahan koordinat.
Tidak ditemukan POI benar-benar "melayang" (salah plot) di sample Menteng —
wajar untuk kawasan pusat kota yang pemetaannya rapat.

## Kesimpulan & tindak lanjut
1. Rumus terverifikasi: Haversine dicek terhadap nilai analitik (1° meridian =
   111,195 km; unit test) dan koordinat OSM live; Q1/Q3/batas-atas IQR persis
   SPEC 2.2 (unit test ground-truth). Deterministik 3x run.
2. **Keputusan tercatat — jarak POI area diukur dari `representative_point`,
   bukan tepi poligon.** Konsekuensi: kompleks besar yang menempel jalan ikut
   ter-flag (≈ 6/32 di sample ini). Opsi perbaikan produksi (putuskan sebelum
   CI Fase 4): ukur jarak dari batas poligon (`shapely.shortest_line` dari
   geometri asli) ATAU pisahkan ambang IQR per layer (titik vs area).
3. Outlier bermakna "jauh dari jalan termapping", bukan otomatis "salah data" —
   sama seperti P1, presisi ditentukan konteks (indoor mall, bundaran, persil
   privat). Disclaimer untuk README (SPEC Bagian 9).
4. `confidence_score` (pagar Tukey 1.5-3×IQR) berperilaku wajar: hanya 4
   temuan ≥ pagar luar (67,3 m) mencapai 1.0, sisanya gradasi — layak
   dipertahankan.
