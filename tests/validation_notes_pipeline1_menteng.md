# Catatan Validasi Manual — Pipeline 1, Sample Menteng (SPEC 5.4)

Tanggal: 2026-07-19. Graph: `data/raw/sample_menteng.graphml`
(OSMnx `graph_from_polygon`, `network_type="drive"`, Kecamatan Menteng,
693 node / 1.326 edge). Metode validasi: cek silang temuan terhadap OSM API
live (`api.openstreetmap.org/api/0.6`) — tag node, tag way, dan daftar way
yang memuat node tersebut.

## Hasil run (3x berturut-turut, deterministik — checklist 5.4 poin 1)
| Run | dangling | disconnected | oneway | total | status |
|---|---|---|---|---|---|
| 1-3 (identik) | 69 | 2 | 70 | 141 | success |

Tercatat di `pipeline_logs` (3 baris success 2026-07-18 20:27-20:28 UTC) dan
`road_errors` (423 baris = 141 x 3). Tiga baris `failed` sebelumnya di
`pipeline_logs` adalah insiden kolom Integer 32-bit (lihat PROGRESS.md) —
dibiarkan sebagai jejak historis.

## Sample yang divalidasi

### Dangling node (4 dari 69 dicek) — 4/4 FALSE POSITIVE terhadap definisi "error topologi"
| Node | Temuan OSM live |
|---|---|
| 353139789 | Tersambung ke 2 way; way lanjutan `living_street` ber-`motorcar=no` (width 1 m) |
| 353146588 | Tersambung ke 3 way; lanjutan `living_street` `motorcar=no` |
| 1675286064 | Tersambung ke 2 way `living_street`, lanjutan `motorcar=no` |
| 1675286070 | Tersambung ke 2 way `living_street`, lanjutan `motorcar=no` |

**Diagnosis:** node-node ini BUKAN dangling di data OSM — jalan lanjutannya ada,
tapi berupa gang `motorcar=no` yang dikecualikan filter `network_type="drive"`.
Jadi temuan "benar" untuk jaringan mobil, "salah" untuk klaim kesalahan data.
Degree=1 (SPEC 3.1) bekerja tepat secara matematis; presisinya ditentukan
pra-pemrosesan (filter), bukan rumusnya.

### Disconnected component (2 dari 2 dicek) — sebab sama
Dua komponen ukuran 2 (rasio 0.0029 < 0.05): rep 4791006451 dan 13550914939.
Keduanya pulau `living_street` yang di dunia nyata tersambung via way
`motorcar=no` / `access=destination` (mis. jembatan Gang Ampiun). Terisolasi
hanya dalam jaringan mobil.

### Oneway inconsistency (3 dari 70 dicek) — tag oneway valid; flag = artefak clip
Way 526737276 & 1378151561 (Jalan Teluk Betung, tertiary) dan 1263586498
(Jalan Jenderal Sudirman, primary) memang `oneway=yes` di OSM. Ter-flag karena
path balik (lawan arah) berada DI LUAR polygon Menteng — SCC dihitung pada
subgraph terpotong. Diproyeksikan turun drastis saat dijalankan pada graph
Jabodetabek penuh di CI.

## Kesimpulan & tindak lanjut
1. Ketiga rumus (degree=1, BFS component, Tarjan SCC) terverifikasi benar via
   unit test sintetis ber-ground-truth pasti; false positive sample berasal
   dari pra-pemrosesan (filter drive + pemotongan area), bukan dari algoritma.
2. `DISCONNECTED_COMPONENT_MIN_RATIO=0.05`: pada sample ini kedua komponen
   berrasio 0.003 — jauh di bawah threshold; belum ada dasar mengubah
   placeholder. Validasi ulang pada graph Jabodetabek penuh (Fase 4).
3. **Keputusan filter untuk produksi (harus diputuskan sebelum CI Fase 4):**
   untuk use case armada motor (Grab/Gojek), pertimbangkan sertakan jalan
   `motorcar=no` yang `motorcycle=yes` (gang) — mengurangi false positive
   dangling/disconnected sekaligus lebih sesuai konteks Jakarta.
4. Temuan oneway pada area terpotong wajib dibaca sebagai "perlu review",
   bukan vonis salah arah — disclaimer dicantumkan di README (SPEC Bagian 9).
