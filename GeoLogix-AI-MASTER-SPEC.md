# GEOLOGIX AI — MASTER SPECIFICATION
> Dokumen ini adalah gabungan seluruh spesifikasi proyek: konsep, PRD, dasar matematika, dan roadmap ML.
> **INSTRUKSI UNTUK CLAUDE CODE / AI CODING ASSISTANT:**
> Baca dokumen ini SECARA URUT dari atas ke bawah sebelum menulis kode apa pun.
> Ikuti urutan eksekusi di bagian "STEP PENGERJAAN" pada bagian PRD — JANGAN loncat fase atau bangun beberapa pipeline sekaligus.
> Fase 1 (rule-based/statistik) HARUS selesai dan teruji dulu sebelum menyentuh apa pun di bagian ML Evolution (Fase 2).
> Semua rumus di bagian "DASAR MATEMATIKA" bersifat WAJIB diimplementasikan persis seperti dijabarkan, bukan pendekatan bebas.

---

## DAFTAR ISI
1. Konsep & Latar Belakang (Concept Note)
2. Product Requirements Document (PRD) — Goals, Arsitektur, Step Pengerjaan
3. Dasar Matematika — WAJIB per pipeline
4. Roadmap Evolusi ke Machine Learning (Fase 2 — jangan dikerjakan dulu)

---


# =====================================================
# BAGIAN 1: KONSEP & LATAR BELAKANG
# =====================================================

# GeoLogix AI — Concept Note

## 1. MASALAH (nyata, bukan asumsi)
Maret 2026, Jakarta mengalami "krisis ojol": order GoRide/GrabBike susah dapat driver di zona tertentu, padahal demand GoFood/GrabExpress justru naik. Penyebabnya: hujan ekstrem + banjir lokal + macet membuat driver menghindari zona tertentu, sementara demand di zona itu tetap tinggi.

**Inti masalah:** ketidakseimbangan supply (driver) dan demand (order) antar-zona, yang dipicu kondisi geografis (cuaca, banjir, jaringan jalan) — bukan sekadar "kurang driver secara total".

## 2. SOLUSI
Sistem yang **mendeteksi** zona mana yang sedang/berpotensi kekurangan driver akibat gangguan geografis, **memprediksi** 3 jam ke depan, dan **merekomendasikan** jumlah driver yang perlu dipindah dari zona surplus ke zona defisit — sebelum user mengeluh.

## 3. CARA KERJA (5 langkah)
1. **Lihat keadaan** — kumpulkan data cuaca/banjir, jaringan jalan, pola demand per jam.
2. **Deteksi zona bermasalah** — pakai analisis hotspot statistik spasial (Getis-Ord Gi*, Local Moran's I) untuk menandai zona defisit driver secara signifikan (bukan tebakan visual).
3. **Prediksi 3 jam ke depan** — model machine learning (Gradient Boosting) dibandingkan baseline sederhana, memakai variabel cuaca + histori demand.
4. **Hitung solusi realokasi** — assignment problem (Operations Research/linear programming): dari zona mana ke zona mana, berapa driver.
5. **Tampilkan** — peta interaktif berbasis hexagon (H3), warna risk-level, panah rekomendasi, slider waktu.

**Prinsip metodologi:** GIS klasik untuk deteksi → AI untuk prediksi → OR untuk keputusan. Setiap tahap dipilih karena alasan ilmiah spesifik, bukan karena tren.

## 4. SEBERAPA IMPACTFUL (untuk perusahaan seperti Grab/Gojek)
- **Operasional:** mengurangi keluhan "susah dapat driver" di zona rawan cuaca — langsung menyentuh KPI *service level* dan *driver utilization*, dua metrik inti tim Maps Operations/Network Planning.
- **Proaktif vs reaktif:** kebanyakan sistem existing bereaksi setelah demand menumpuk; sistem ini bertujuan bertindak *sebelum* imbalance terjadi.
- **Keterbatasan jujur:** ini proof-of-concept berbasis data terbuka, bukan sistem produksi — hasil optimasi bersifat indikatif karena tidak memakai data order/driver internal perusahaan. Ini penting disampaikan apa adanya di interview, bukan diklaim sebagai solusi siap pakai.

## 5. DATA YANG DIPAKAI (semua terbuka & legal)
| Data | Sumber | Fungsi |
|---|---|---|
| Curah hujan & riwayat banjir | BMKG, petabencana.id (crowdsourced, dipakai riset akademik Jakarta) | Deteksi zona terdampak cuaca |
| Jaringan jalan | OpenStreetMap (extract Jabodetabek) | Hitung rute, konektivitas, proxy macet |
| Pola mobilitas/demand | Data mobilitas publik historis (proxy, bukan data order asli) | Estimasi pola demand per jam/zona |
| Grid analisis | H3 (Uber, open-source) | Membagi Jabodetabek jadi unit hexagon seragam |




# =====================================================
# BAGIAN 2: PRODUCT REQUIREMENTS DOCUMENT (PRD)
# =====================================================

# Product Requirements Document (PRD)
# GeoLogix AI — Automated Geospatial Data Quality & Risk Intelligence Platform

**Versi:** 1.0
**Status:** Draft untuk portfolio
**Target role:** Maps Operations, Network Planning, Geospatial Data Scientist, Spatial Data Engineer

---

## 1. LATAR BELAKANG & JUSTIFIKASI

Berdasarkan riset job description nyata dari 7 profesional Maps Ops di Grab & Gojek, ditemukan bahwa pekerjaan mereka sehari-hari berpusat pada 3 hal: **(1)** menjaga kualitas data jaringan jalan & POI dalam skala jutaan segmen, **(2)** transformasi deteksi masalah dari reaktif (menunggu komplain) ke proaktif (deteksi otomatis), dan **(3)** integrasi data cuaca/kondisi jalan ke dalam operasional routing.

Masalah nyata yang jadi pemicu: **krisis ojol Maret 2026** di Jakarta — ketidakseimbangan supply-demand driver akibat banjir & macet yang tidak terdeteksi/direspons secara sistematis.

GeoLogix AI dibangun untuk membuktikan kemampuan membangun **pipeline otomatis** yang menjawab kedua sisi ini sekaligus — bukan dashboard statis, tapi sistem yang benar-benar berjalan sendiri dan bisa diverifikasi hasilnya oleh siapa pun (recruiter tinggal buka link/GitHub Actions log).

---

## 2. GOALS

### Goal Utama
Membangun sistem otomatis yang **mendeteksi masalah kualitas data spasial dan risiko operasional geografis** di jaringan jalan Jabodetabek, tanpa intervensi manual setelah sistem berjalan.

### Goal Spesifik (measurable)
1. Mendeteksi minimal 3 kategori error jaringan jalan OSM secara otomatis (topologi terputus, atribut hilang, arah tidak konsisten).
2. Mendeteksi POI dengan lokasi anomali (di luar area valid) secara otomatis.
3. Menghasilkan overlay risiko cuaca-jalan yang ter-update tiap jam tanpa aksi manual.
4. Seluruh pipeline punya log riwayat berjalan yang bisa diaudit publik (GitHub Actions).
5. Dashboard menampilkan data yang selalu fresh (maksimal delay 1 jam dari sumber).

### Non-Goals (supaya scope tidak melebar lagi)
- **Bukan** membangun ulang OSRM/routing engine dari nol.
- **Bukan** memprediksi demand order asli (tidak ada akses data internal perusahaan).
- **Bukan** menggantikan sistem produksi — ini proof-of-concept metodologi yang jujur soal keterbatasannya.

---

## 3. TARGET USER / PERSONA

| Persona | Kebutuhan |
|---|---|
| **Recruiter/Interviewer Maps Ops** | Ingin lihat kandidat paham data quality pipeline & OSM validation nyata |
| **Interviewer Network Planning** | Ingin lihat kandidat paham risk detection & decision support |
| **Anda sendiri (portfolio owner)** | Butuh sistem yang bisa dijelaskan detail per komponen saat interview |

---

## 4. ARSITEKTUR SISTEM END-TO-END

```
[Sumber Data Eksternal]
   ├─ OSM (Overpass API) ──────┐
   ├─ Open-Meteo API ──────────┤
   ├─ CHIRPS (historis) ───────┤
   └─ Data POI (OSM tag) ──────┘
              │
              ▼
   [Scheduler: GitHub Actions — cron]
              │
   ┌──────────┼──────────┬──────────────┐
   ▼          ▼          ▼              ▼
[Pipeline 1] [Pipeline 2] [Pipeline 3]  [Pipeline 4]
Road QA      POI QA       Weather-Risk  Aggregator
              │
              ▼
   [PostgreSQL + PostGIS (Supabase/Neon)]
              │
              ▼
   [FastAPI backend — REST endpoint]
              │
              ▼
   [React + deck.gl Dashboard — auto-refresh]
```

---

## 5. RINCIAN FITUR (4 PIPELINE + DASHBOARD)

### Pipeline 1 — Road Network QA
**Tujuan:** deteksi error topologi jaringan jalan secara otomatis.
**Cara kerja:** tarik OSM extract Jabodetabek → bangun graph (OSMnx) → cek: node menggantung (dangling node), jalan terputus (disconnected components), arah jalan (oneway) tidak konsisten dengan konektivitas.
**Metode:** graph theory murni (rule-based), **bukan AI** — karena ini masalah struktural yang punya definisi pasti benar/salah, deep learning tidak menambah nilai di sini.
**Output:** tabel error dengan lokasi (lat/lon), jenis error, tingkat keparahan.

### Pipeline 2 — POI Validation
**Tujuan:** deteksi POI dengan lokasi tidak masuk akal (contoh: POI "restoran" terletak di tengah sungai/luar jaringan jalan).
**Cara kerja:** spatial join POI ke buffer jaringan jalan terdekat → flag POI yang jaraknya melampaui threshold wajar → cross-check kategori vs area (misal: POI residensial di zona industri terlarang, opsional lanjutan).
**Metode:** spatial statistics (rule-based + outlier detection sederhana, misal IQR pada jarak).
**Output:** daftar POI anomali + skor keyakinan.

### Pipeline 3 — Weather-Risk Overlay
**Tujuan:** menandai ruas jalan yang berisiko terganggu akibat cuaca (hujan/potensi banjir).
**Cara kerja:** tarik data curah hujan Open-Meteo tiap jam → overlay ke grid H3 → gabungkan dengan baseline riwayat rawan banjir dari CHIRPS (historis 5 tahun) → hitung risk index per grid.
**Metode:** GIS klasik (overlay spasial) untuk overlay real-time; **statistik spasial (hotspot analysis)** untuk baseline historis.
**Output:** peta risk index per grid H3, update tiap jam.

### Pipeline 4 — Aggregator & Alert Log
**Tujuan:** gabungkan hasil 3 pipeline jadi satu ringkasan, simpan log riwayat run (bukti sistem berjalan otomatis).
**Output:** log historis "tanggal X, pipeline Y mendeteksi Z error" — inilah yang jadi bukti nyata, setara klaim "80% peningkatan capture rate" di CV orang lain, tapi bisa diverifikasi.

### Dashboard
- Peta interaktif (deck.gl, H3 hexagon layer) menampilkan 3 layer: road error, POI anomali, weather-risk.
- Panel log riwayat pipeline (bukti sistem otomatis).
- Filter waktu (lihat kondisi kemarin vs sekarang).

---

## 6. DATA SOURCES

| Data | Sumber | Update | Fungsi |
|---|---|---|---|
| Jaringan jalan | OpenStreetMap (Overpass API) | On-demand | Pipeline 1 |
| POI | OSM POI tags | On-demand | Pipeline 2 |
| Curah hujan real-time | Open-Meteo API | Per jam | Pipeline 3 |
| Curah hujan historis | CHIRPS | Dekadal | Baseline risiko Pipeline 3 |
| Grid analisis | H3 (Uber open-source) | Statis | Semua pipeline |

---

## 7. TECH STACK

- **Geoprocessing:** Python — GeoPandas, OSMnx, NetworkX, H3-py
- **Automasi:** GitHub Actions (cron scheduler, gratis, log publik)
- **Database:** PostgreSQL + PostGIS (hosting: Supabase/Neon free tier)
- **Backend API:** FastAPI
- **Frontend:** React + deck.gl
- **Deploy:** Vercel (frontend) + Render/Railway (backend)

---

## 8. STEP PENGERJAAN (URUTAN WAJIB — jangan loncat)

**Fase 0 — Fondasi (minggu 1)**
1. Setup repo GitHub, struktur folder, environment Python.
2. Setup database PostgreSQL + PostGIS (Supabase).
3. Ambil sample data OSM Jabodetabek kecil (1 kecamatan dulu) untuk uji coba pipeline sebelum full-scale.

**Fase 1 — Pipeline 1: Road Network QA (minggu 2)**
4. Bangun graph dari OSM pakai OSMnx.
5. Implementasi 3 rule deteksi error (dangling node, disconnected component, oneway inconsistency).
6. Simpan hasil ke database.
7. Uji di 1 kecamatan, validasi manual sample hasil (cek beberapa error benar apa nggak).

**Fase 2 — Pipeline 2: POI Validation (minggu 3)**
8. Ambil data POI dari OSM.
9. Spatial join ke jaringan jalan, hitung jarak, flag anomali.
10. Validasi manual sample.

**Fase 3 — Pipeline 3: Weather-Risk Overlay (minggu 4)**
11. Integrasi Open-Meteo API.
12. Bangun grid H3 untuk Jabodetabek.
13. Ambil CHIRPS historis, hitung baseline risk per grid (hotspot analysis).
14. Gabungkan real-time + historis jadi risk index.

**Fase 4 — Otomasi (minggu 5)**
15. Setup GitHub Actions cron untuk 3 pipeline (jadwal berbeda: harian untuk P1/P2, per jam untuk P3).
16. Uji jalan otomatis minimal 3 hari, pastikan log tersimpan.

**Fase 5 — Backend & Dashboard (minggu 6-7)**
17. Bangun FastAPI endpoint baca dari database.
18. Bangun frontend React + deck.gl, render 3 layer + panel log.
19. Deploy ke Vercel + Render.

**Fase 6 — Dokumentasi & Writeup (minggu 8)**
20. Tulis README metodologi (justifikasi tiap metode, keterbatasan, hasil validasi manual).
21. Siapkan narasi 15 detik + demo flow untuk interview.

**Mulai dari Fase 0 langkah 1-3 dulu — jangan bangun 4 pipeline sekaligus, karena kalau satu pipeline error, susah debug kalau semuanya jalan bersamaan pertama kali.**

---

## 9. KEUNGGULAN DIBANDING PORTFOLIO SEJENIS

1. **Bukti nyata vs klaim** — pipeline benar-benar auto-jalan (GitHub Actions log publik), bukan screenshot sekali jalan.
2. **Selaras persis dengan job desc riil** — dibangun dari analisis 7 profil Maps Ops asli, bukan asumsi.
3. **Metodologi tidak asal AI** — setiap komponen punya justifikasi kapan pakai rule-based/GIS klasik vs kapan pakai statistik spasial, dijelaskan eksplisit di README.
4. **Reproducible 100%** — semua data terbuka, siapa pun bisa jalankan ulang.
5. **Jujur soal keterbatasan** — bukan mengklaim menggantikan sistem produksi Grab/Gojek, tapi proof-of-concept metodologi yang solid.

---

## 10. RISIKO & MITIGASI

| Risiko | Mitigasi |
|---|---|
| Overpass API rate limit / timeout untuk area besar | Mulai dari area kecil, cache hasil, gunakan extract file (Geofabrik) untuk full Jabodetabek |
| GitHub Actions free tier terbatas menit/bulan | Jadwalkan pipeline besar tidak terlalu sering (harian, bukan tiap jam untuk P1/P2) |
| Validasi error/anomali tidak 100% akurat | Selalu cantumkan disclaimer + hasil validasi manual sample di README |
| Waktu pengerjaan meleset dari 8 minggu | Prioritaskan Pipeline 1 selesai dulu sebagai MVP yang bisa didemokan, sisanya iteratif |


# =====================================================
# BAGIAN 3: DASAR MATEMATIKA (WAJIB)
# =====================================================

# Dasar Matematika — GeoLogix AI
Dokumen pendamping PRD. Setiap rumus di sini WAJIB bisa dijelaskan asal dan alasannya saat interview.

---

## PIPELINE 1 — Road Network QA (Graph Theory)

**Representasi data:** jaringan jalan direpresentasikan sebagai graph berarah `G = (V, E)`
- `V` = himpunan node (persimpangan/titik jalan)
- `E` = himpunan edge (ruas jalan), tiap edge punya atribut arah (oneway/two-way)

### 1.1 Deteksi Dangling Node
Node `v` dikategorikan dangling jika:
```
degree(v) = 1
```
`degree(v)` = jumlah edge yang terhubung ke node `v` (dihitung tanpa memandang arah). Node dengan degree 1 berarti jalan "buntu" yang seharusnya tersambung — indikasi data topologi salah (bukan cul-de-sac asli, karena itu perlu dicek silang dengan tag OSM `highway=*` khusus).

### 1.2 Deteksi Disconnected Component
Graph dipecah jadi himpunan connected component `C1, C2, ..., Cn` menggunakan **algoritma BFS/DFS** atau **Union-Find (Disjoint Set)**. Jika:
```
n > 1  DAN  |Ci| kecil relatif terhadap |Ci| terbesar
```
maka komponen kecil itu diduga terisolasi dari jaringan utama — jalan yang "terpisah" di data padahal harusnya nyambung ke jaringan Jabodetabek.

### 1.3 Konsistensi Arah Jalan (Oneway)
Untuk tiap edge berarah, cek apakah termasuk dalam **Strongly Connected Component (SCC)** menggunakan **algoritma Tarjan** atau **Kosaraju**. Edge oneway yang membuat suatu node tidak bisa dijangkau balik (tidak ada strongly connected path) menandakan kemungkinan kesalahan arah di data OSM.

**Kenapa graph theory murni, bukan ML:** ketiga masalah ini punya definisi benar/salah yang pasti secara matematis (ada path atau tidak ada path) — bukan pola statistik yang perlu "dipelajari". Menggunakan ML di sini justru kehilangan garansi correctness yang diberikan algoritma graph klasik (BFS/DFS/Tarjan adalah exact algorithm, bukan probabilistik).

---

## PIPELINE 2 — POI Validation (Spatial Statistics)

### 2.1 Jarak Spasial
Karena koordinat POI dan jalan dalam lat/lon (WGS84), jarak dihitung dengan **Haversine formula** (bukan Euclidean biasa, karena permukaan bumi melengkung):
```
a = sin²(Δφ/2) + cos(φ1) · cos(φ2) · sin²(Δλ/2)
c = 2 · atan2(√a, √(1−a))
d = R · c
```
- `φ1, φ2` = latitude titik 1 & 2 (radian)
- `Δλ` = selisih longitude
- `R` = radius bumi (≈6371 km)

Alternatif: proyeksikan ke UTM (meter-based) dulu baru pakai Euclidean biasa — lebih cepat komputasi untuk skala kota, tapi Haversine lebih aman untuk validasi lintas zona.

### 2.2 Deteksi Anomali Jarak — Interquartile Range (IQR)
Setelah dapat jarak tiap POI ke jalan terdekat, deteksi outlier pakai IQR (bukan asumsi distribusi normal, karena jarak spasial biasanya skewed):
```
Q1 = persentil ke-25 dari seluruh jarak POI→jalan
Q3 = persentil ke-75
IQR = Q3 − Q1
Batas atas = Q3 + 1.5 × IQR
```
POI dengan jarak > batas atas → **diflag sebagai anomali** (lokasi POI "melayang" jauh dari jaringan jalan valid).

**Kenapa IQR, bukan z-score/ML:** distribusi jarak spasial di kota nyata umumnya tidak normal (banyak POI dekat jalan, sedikit yang jauh) — IQR robust terhadap skewness dan tidak butuh asumsi distribusi, cocok untuk data eksplorasi tanpa label training.

---

## PIPELINE 3 — Weather-Risk Overlay (GIS-MCDA)

### 3.1 Normalisasi Kriteria (Min-Max Scaling)
Setiap kriteria (curah hujan, histori banjir) punya satuan beda — wajib dinormalisasi ke skala 0-1 sebelum digabung:
```
xi_norm = (xi − xi_min) / (xi_max − xi_min)
```

### 3.2 Analytic Hierarchy Process (AHP) — untuk menentukan bobot
Metode terstruktur Saaty untuk pembobotan kriteria berdasarkan pairwise comparison (skala 1-9), digunakan di sini agar bobot tidak ditentukan secara asal.

1. **Matriks perbandingan berpasangan** `A` (ukuran n×n, n = jumlah kriteria):
```
A[i][j] = tingkat kepentingan kriteria i relatif terhadap j (skala 1-9 Saaty)
A[j][i] = 1 / A[i][j]
```
2. **Bobot (wi)** = eigenvector utama dari matriks `A`, dinormalisasi sehingga `Σ wi = 1`.
3. **Uji Konsistensi (wajib, tidak boleh dilewat):**
```
CI = (λmax − n) / (n − 1)
CR = CI / RI
```
- `λmax` = eigenvalue terbesar dari matriks A
- `RI` = Random Index (nilai tabel standar Saaty, tergantung n)
- **Syarat valid: CR ≤ 0.1.** Jika CR > 0.1, matriks perbandingan harus direvisi — bobot yang dihasilkan dari matriks tidak konsisten dianggap tidak valid secara metodologis.

### 3.3 Weighted Linear Combination (WLC) — penggabungan akhir
```
RiskIndex(grid) = Σ (wi × xi_norm)     dengan Σ wi = 1
```
Metode ini adalah praktik umum GIS-MCDA yang didokumentasikan luas dalam tinjauan literatur (Malczewski, 2000; 2006, *International Journal of Geographical Information Science*).

### 3.4 Getis-Ord Gi* — untuk baseline historis (opsional, dari CHIRPS 5 tahun)
Dipakai untuk mendeteksi hotspot statistik signifikan dari histori curah hujan/banjir per grid, bukan sekadar nilai tinggi biasa:
```
Gi* = [ Σj (wij · xj) − X̄ · Σj wij ] / [ S · √( (n·Σj wij² − (Σj wij)²) / (n−1) ) ]
```
- `wij` = bobot spasial antara grid i dan j (biasanya berdasarkan kedekatan/contiguity)
- `X̄`, `S` = mean dan standar deviasi global dari semua nilai
- Hasil Gi* berupa z-score → nilai tinggi signifikan (p<0.05) = **hotspot statistik nyata**, bukan sekadar kebetulan angka tinggi.

**Kenapa dipakai:** ini metode standar spatial statistics untuk membedakan pola spasial yang signifikan secara statistik vs random noise — penting supaya baseline risiko historis Anda tidak asal ambil "daerah yang kelihatan sering banjir di peta", tapi benar-benar teruji signifikansinya.

---

## PIPELINE 4 — Aggregator (Prioritas gabungan)

Menggunakan **AHP + WLC yang sama seperti Pipeline 3**, tapi kriterianya beda:
- Kriteria: severity error (dari P1/P2), kepadatan populasi terdampak (proxy WorldPop), kemudahan perbaikan (skor manual 1-5).
- Output: skor prioritas gabungan per temuan, urutan mana yang harus ditangani duluan.

---

## RINGKASAN — Peta Metode ke Pipeline

| Pipeline | Metode | Jenis | Kenapa (ringkas) |
|---|---|---|---|
| P1 Road QA | Graph theory (BFS/DFS, Tarjan) | Exact algorithm | Masalah topologi punya jawaban pasti benar/salah |
| P2 POI Validation | Haversine + IQR | Statistik deskriptif | Deteksi anomali tanpa perlu data training |
| P3 Weather-Risk | AHP + WLC + Getis-Ord Gi* | GIS-MCDA + spatial statistics | Kombinasi kriteria butuh bobot terstruktur, bukan tebakan; hotspot butuh uji signifikansi |
| P4 Aggregator | AHP + WLC | GIS-MCDA | Prioritas multi-kriteria untuk decision support |

**Catatan penting:** tidak ada satupun pipeline di atas yang memakai machine learning. Ini keputusan sadar — bukan karena tidak tahu ML, tapi karena tiap masalah di sini punya struktur matematis yang lebih tepat diselesaikan exact algorithm/statistik klasik. Kalau nanti ingin menambah komponen prediktif (misal prediksi 3 jam ke depan), itu baru domain yang legitimate untuk ML — dan itu harus dibandingkan dengan baseline non-ML untuk membuktikan ML benar-benar diperlukan.


# =====================================================
# BAGIAN 4: ROADMAP EVOLUSI KE MACHINE LEARNING (FASE 2)
# =====================================================

# GeoLogix AI — Roadmap Evolusi: Matematika Dasar → Machine Learning

## PRINSIP UTAMA (baca ini dulu sebelum lanjut)
ML **tidak ditambahkan karena "harus ada AI"**. ML hanya masuk kalau memenuhi 3 syarat sekaligus:
1. Ada **cukup data historis berlabel** (bukan asumsi, harus benar-benar terkumpul dari log Fase 1).
2. Masalahnya **non-linear/multi-variabel** yang sulit dimodelkan aturan sederhana.
3. ML **terbukti mengungguli baseline non-ML** lewat pengujian, bukan diklaim begitu saja.

Kalau salah satu syarat tidak terpenuhi, tetap pakai metode Fase 1 (rule-based/statistik klasik). Ini yang membedakan Anda dari kandidat yang nempel ML di semua tempat tanpa validasi.

---

## FASE 1 (Fondasi — sudah dirancang, JALAN DULU, TANPA ML)
Rekap singkat (detail lengkap ada di dokumen Math Foundations):
- P1 Road QA → graph theory (BFS/DFS, Tarjan)
- P2 POI Validation → Haversine + IQR
- P3 Weather-Risk → AHP + WLC + Getis-Ord Gi*
- P4 Aggregator → AHP + WLC

**Output penting dari Fase 1 yang jadi BAHAN BAKU Fase 2:** setiap kali pipeline jalan, hasil deteksi (error, anomali, risk index) **disimpan sebagai log historis**. Setelah beberapa bulan berjalan, log ini jadi dataset berlabel yang sebelumnya tidak ada — inilah yang membuka jalan ke ML secara sah, bukan asal pasang model dari awal.

---

## FASE 2 (ML masuk — HANYA di 3 titik yang punya justifikasi)

### 2.1 Prediksi Weather-Risk 3 Jam ke Depan
**Kenapa layak ML:** ini murni **prediksi masa depan** berdasarkan multi-variabel (curah hujan real-time + tren + histori) — bukan deteksi masa lalu/sekarang seperti Fase 1. Hubungan antar variabel (bagaimana tren hujan 1 jam terakhir memengaruhi risiko 3 jam ke depan) tidak linear sederhana, sehingga layak dicoba ML.

**Model:** Gradient Boosting (XGBoost/LightGBM) — dipilih karena performanya kuat pada data tabular multi-fitur dan lebih interpretable dibanding deep learning (feature importance bisa dijelaskan ke interviewer).

**Fitur input:**
- Curah hujan 1, 3, 6 jam terakhir (Open-Meteo)
- Risk index historis grid tersebut (dari Pipeline 3 Fase 1)
- Waktu (jam, hari kerja/weekend) — proxy pola demand
- Risk index grid tetangga (spatial lag)

**WAJIB — baseline pembanding:**
```
Baseline 1: Persistence model → prediksi(t+3) = nilai(t)
Baseline 2: Moving average sederhana
```
Model ML **hanya dianggap valid dipakai** jika secara terukur mengungguli kedua baseline ini. Kalau tidak, laporkan jujur bahwa ML tidak memberi nilai tambah di kasus ini — itu tetap temuan yang sah untuk portfolio, bukan kegagalan.

**Metrik evaluasi:** MAE (Mean Absolute Error) dan RMSE, dibandingkan across model vs baseline.

**VALIDASI WAJIB — Spatial Cross-Validation (bukan random split biasa):**
Ini bagian yang sering dilewatkan kandidat lain dan jadi red flag di mata reviewer GIS. Karena data risiko antar-grid yang berdekatan cenderung mirip satu sama lain (spatial autocorrelation), random train-test split akan membuat model terlihat bagus padahal cuma "menghafal" pola lokasi tetangga. Studi metodologi cross-validation untuk data yang punya struktur spasial/temporal/hierarkis menegaskan bahwa random split menghasilkan estimasi performa yang terlalu optimis pada data semacam ini (Roberts et al., 2017, *Ecography*). Solusinya: pakai **spatial block cross-validation** — bagi Jabodetabek jadi blok-blok wilayah, latih di sebagian blok, uji di blok yang benar-benar terpisah secara spasial.

### 2.2 Klasifikasi Prioritas Review Error (semi-otomatis, setelah data cukup)
**Kenapa layak ML:** setelah beberapa bulan, log Fase 1 berisi ribuan temuan error yang **sudah divalidasi manual** (benar error / bukan). Ini jadi label alami. Model classifier bisa belajar pola mana temuan yang kemungkinan besar valid vs false-positive, mengurangi beban validasi manual.
**Model:** klasifikasi biner sederhana (Logistic Regression atau Random Forest) — tidak perlu deep learning untuk jumlah fitur terbatas.
**Metrik:** Precision & Recall (bukan hanya akurasi) karena data kemungkinan besar tidak seimbang (error valid jauh lebih sedikit dari yang tidak valid) — akurasi saja menyesatkan pada data imbalanced.

### 2.3 Refinement Deteksi Anomali POI (opsional, perbandingan langsung dengan IQR)
**Kenapa layak dicoba:** IQR di Fase 1 hanya melihat 1 dimensi (jarak). Clustering density-based (DBSCAN) bisa menangkap pola anomali multi-dimensi (jarak + kepadatan POI sekitar).
**Syarat pakai:** hanya dipertahankan jika terbukti menangkap anomali yang terlewat IQR, divalidasi manual pada sample. Jika tidak ada perbedaan berarti, tetap pakai IQR karena lebih sederhana dan interpretable (prinsip Occam's razor — jangan pakai metode kompleks kalau yang simpel sudah cukup).

---

## ALUR DATA LENGKAP (Fase 1 → Fase 2)

```
[Data mentah: OSM, Open-Meteo, CHIRPS]
        │
        ▼
[FASE 1: Rule-based/Statistik — jalan otomatis harian/jam]
        │
        ▼
[Log historis tersimpan di PostgreSQL — akumulasi dari waktu ke waktu]
        │
        ▼
[Setelah cukup data (idealnya 3-6 bulan log)]
        │
        ▼
[FASE 2: Feature Engineering dari log historis]
        │
        ▼
[Training ML dengan Spatial Cross-Validation]
        │
        ▼
[Uji vs baseline non-ML — HANYA lanjut jika menang]
        │
        ▼
[Jika menang: model deploy sebagai layer tambahan di dashboard]
[Jika kalah: laporkan sebagai temuan negatif yang jujur, tetap pakai Fase 1]
```

---

## KENAPA URUTAN INI PENTING (bukan sekadar formalitas)
Kalau Anda mulai dari ML sejak awal tanpa fondasi Fase 1, Anda tidak akan punya:
- Data historis berlabel yang valid (Fase 2.1 butuh log dari Fase 1 berjalan dulu).
- Baseline pembanding yang kredibel.
- Bukti bahwa Anda paham *kapan* ML diperlukan, bukan cuma *bisa* pakai ML.

Ini justru argumen ilmiah terkuat portfolio Anda: **Anda membangun sistem yang berkembang secara sadar — dari deterministik ke prediktif — dengan pembuktian di tiap langkah**, bukan platform yang dari hari pertama diklaim "AI-powered" tanpa dasar.

## STATUS EKSEKUSI
- **Sekarang:** fokus 100% ke Fase 1 (PRD & Math Foundations yang sudah dibuat). Jangan mulai Fase 2 sebelum Fase 1 jalan otomatis minimal beberapa minggu dan punya log nyata.
- **Fase 2** cukup ditulis sebagai **"roadmap masa depan"** di portfolio/README — ini justru menunjukkan pemikiran jangka panjang ke interviewer, meski belum diimplementasikan penuh saat interview berlangsung.


# =====================================================
# BAGIAN 5: CODE ARCHITECTURE & IMPLEMENTATION FLOW (UNTUK CLAUDE CODE)
# =====================================================

> Bagian ini menerjemahkan PRD (Bagian 2) dan Dasar Matematika (Bagian 3) menjadi struktur kode konkret.
> Claude Code WAJIB mengikuti struktur folder dan urutan file ini — jangan membuat struktur sendiri.

## 5.1 STRUKTUR FOLDER PROYEK

```
geologix-ai/
├── SPEC.md                          # file master spec ini
├── README.md                        # ditulis TERAKHIR, setelah semua fase jalan
├── .github/workflows/
│   ├── pipeline-road-qa.yml         # cron harian
│   ├── pipeline-poi-qa.yml          # cron harian
│   ├── pipeline-weather-risk.yml    # cron per jam
│   └── pipeline-osm-refresh.yml     # cron mingguan (download+clip OSM)
├── data/
│   ├── raw/                         # hasil download OSM/CHIRPS (gitignore, besar)
│   └── boundaries/
│       └── jabodetabek.poly         # polygon boundary untuk clip osmium
├── src/
│   ├── config.py                    # konstanta: path, API keys (dari env), threshold
│   ├── data_ingestion/
│   │   ├── fetch_osm.py             # download+clip .pbf (untuk Pipeline 1, graph topologi)
│   │   ├── fetch_osm_poi.py         # unzip+baca .shp.zip layer POI (untuk Pipeline 2)
│   │   ├── fetch_openmeteo.py       # pull curah hujan real-time
│   │   └── fetch_chirps.py          # pull histori curah hujan
│   ├── pipeline_1_road_qa/
│   │   ├── graph_builder.py         # bangun graph dari OSM (OSMnx)
│   │   ├── detect_dangling_nodes.py
│   │   ├── detect_disconnected.py   # BFS/DFS
│   │   └── detect_oneway_issues.py  # Tarjan SCC
│   ├── pipeline_2_poi_qa/
│   │   ├── spatial_join.py          # Haversine distance ke jalan terdekat
│   │   └── detect_outliers.py       # IQR
│   ├── pipeline_3_weather_risk/
│   │   ├── h3_grid.py               # bangun grid H3 Jabodetabek
│   │   ├── normalize.py             # min-max scaling
│   │   ├── ahp_weights.py           # pairwise matrix, eigenvector, CR check
│   │   ├── wlc_combine.py           # weighted linear combination
│   │   └── hotspot_gi_star.py       # Getis-Ord Gi* untuk baseline historis
│   ├── pipeline_4_aggregator/
│   │   └── prioritize.py            # AHP+WLC untuk prioritas gabungan
│   ├── db/
│   │   ├── models.py                # schema PostgreSQL+PostGIS
│   │   └── writer.py                # simpan hasil tiap pipeline + log run
│   └── api/
│       └── main.py                  # FastAPI endpoint baca dari DB
├── frontend/                        # React + deck.gl (dibuat SETELAH backend jalan)
├── ml/                               # KOSONG di Fase 1 — baru diisi di Fase 2
│   └── (jangan buat file di sini sebelum Fase 1 punya log ≥beberapa minggu)
└── tests/
    └── (unit test tiap fungsi deteksi, terutama rumus matematika Bagian 3)
```

## 5.2 URUTAN FILE DIBUAT (mapping ke "STEP PENGERJAAN" Bagian 2)

| Urutan | File/Folder | Fase PRD |
|---|---|---|
| 1 | `config.py`, `db/models.py`, koneksi Supabase | Fase 0 |
| 2 | `data_ingestion/fetch_osm.py` (Geofabrik+osmium clip) | Fase 0 |
| 3 | `pipeline_1_road_qa/*` lengkap + `tests/` untuk pipeline ini | Fase 1 |
| 4 | `pipeline_2_poi_qa/*` + tests | Fase 2 |
| 5 | `data_ingestion/fetch_openmeteo.py`, `fetch_chirps.py` | Fase 3 |
| 6 | `pipeline_3_weather_risk/*` (urutan internal: h3_grid → normalize → ahp_weights → wlc_combine → hotspot_gi_star) + tests | Fase 3 |
| 7 | `.github/workflows/*.yml` (aktifkan cron, uji jalan otomatis) | Fase 4 |
| 8 | `pipeline_4_aggregator/prioritize.py` | Fase 4 |
| 9 | `api/main.py` (FastAPI) | Fase 5 |
| 10 | `frontend/` (React + deck.gl) | Fase 5 |
| 11 | `README.md` (tulis berdasarkan hasil nyata yang sudah jalan) | Fase 6 |
| 12 | `ml/` — **HANYA jika Fase 1-6 selesai dan log historis cukup** | Fase 2 (ML), lihat Bagian 4 |

**Aturan keras untuk Claude Code:** jangan membuat file di folder `ml/` sebelum baris 1-11 selesai dan diuji jalan. Kalau diminta "tambah fitur AI" sebelum itu, tolak dulu dan arahkan kembali ke fase yang belum selesai — sesuai prinsip di Bagian 4 (ML hanya masuk kalau ada data log + baseline pembanding).

## 5.2c DUA SUMBER DATA OSM — JANGAN DICAMPUR TANPA ALASAN

Proyek ini memakai **2 format ekstrak Geofabrik untuk 2 tujuan berbeda** — ini keputusan sadar, bukan kebetulan:

| Format | Dipakai untuk | Alasan |
|---|---|---|
| `java-latest.osm.pbf` (851MB) | **Pipeline 1 — Road QA** | Menyimpan struktur graph asli (shared node ID antar-way). WAJIB untuk deteksi topologi (dangling node, disconnected component, SCC) — kalau pakai shapefile, proses snapping-nya bisa menciptakan error topologi palsu, merusak validitas hasil deteksi. |
| `java-latest-free.shp.zip` (2.2GB) → layer `gis_osm_pois_free_1.shp` (titik) & `gis_osm_pois_a_free_1.shp` (area) | **Pipeline 2 — POI Validation** | POI validation cuma butuh koordinat + kategori POI, tidak butuh topologi graph. Shapefile lebih praktis di sini karena POI sudah terpisah sebagai layer sendiri, tidak perlu di-parse dari struktur way OSM. |

**Implikasi untuk `data_ingestion/`:**
- `fetch_osm.py` → khusus proses `.pbf` (download/cache/clip untuk Pipeline 1, lihat 5.2b).
- `fetch_osm_poi.py` (file baru) → proses `.shp.zip`: unzip, baca layer `gis_osm_pois_free_1.shp` + `gis_osm_pois_a_free_1.shp` pakai GeoPandas (`gpd.read_file()`), clip ke boundary Jabodetabek pakai `gpd.clip()`.
- Kedua file **tidak saling bergantung** — bisa dikerjakan/diuji secara paralel karena tujuannya beda pipeline.

## 5.2b OSM DATA ACQUISITION — FULL OTOMATIS (KEPUTUSAN FINAL)

**Sumber:** Geofabrik `java-latest.osm.pbf` (851MB, region Java, mencakup Jabodetabek), diperbarui rutin oleh Geofabrik. Lisensi ODbL.

**Masalah teknis yang wajib ditangani:** GitHub Actions runner bersifat ephemeral (storage hilang tiap job selesai). Supaya proses full otomatis (download awal + update mingguan) tetap jalan tanpa intervensi manual, WAJIB pakai `actions/cache` untuk persist file `.pbf` antar-run.

**Logika `fetch_osm.py` (idempotent, aman dijalankan berkali-kali):**
```
1. Cek apakah data/raw/jabodetabek.osm.pbf ada di GitHub Actions Cache (key: "osm-jabodetabek-v1")
   ├── CACHE MISS (run pertama kali, atau cache expired):
   │     → Download java-latest.osm.pbf penuh dari Geofabrik
   │     → osmium extract --polygon data/boundaries/jabodetabek.poly → jabodetabek.osm.pbf
   │     → Simpan ke cache
   │     → Log mode="full_download" ke tabel pipeline_logs
   │
   └── CACHE HIT (run mingguan berikutnya):
         → Restore file dari cache
         → Download file .osc.gz (diff harian/mingguan dari Geofabrik)
         → osmium apply-changes jabodetabek.osm.pbf update.osc.gz -o jabodetabek.osm.pbf (baru)
         → Simpan versi terbaru kembali ke cache (overwrite key yang sama)
         → Log mode="incremental_update" ke tabel pipeline_logs
2. Fallback wajib: jika osmium apply-changes gagal (misal file corrupt), otomatis jatuh ke mode full_download — sistem tidak boleh stuck error tanpa recovery.
```

**Workflow `.github/workflows/pipeline-osm-refresh.yml` — poin implementasi wajib:**
- Gunakan step `actions/cache@v4` dengan `key: osm-jabodetabek-v1` dan `restore-keys` sebagai fallback.
- Jadwal: cron mingguan (`0 0 * * 0`).
- Job ini HARUS selesai sebelum Pipeline 1 (Road QA) dijalankan pada hari yang sama — atur dependency antar-workflow (`workflow_run` trigger) supaya Pipeline 1 tidak jalan dengan data OSM yang belum ter-update.

## 5.3 SETIAP FILE PIPELINE WAJIB PUNYA
1. Docstring yang menyebut rumus/algoritma persis dari Bagian 3 (misal: "Implementasi Getis-Ord Gi*, lihat Bagian 3.4").
2. Unit test minimal 1 kasus (termasuk kasus edge/boundary, misal CR > 0.1 di AHP harus raise error, bukan lolos diam-diam).
3. Logging hasil run ke tabel `pipeline_logs` di database (kolom: timestamp, pipeline_name, jumlah_temuan, status) — ini yang jadi bukti nyata sistem otomatis, dan jadi bahan baku Fase 2 ML nanti.

## 5.4 VALIDASI SEBELUM LANJUT FASE BERIKUTNYA
Sebelum pindah ke fase selanjutnya, checklist:
- [ ] Pipeline fase ini jalan tanpa error minimal 3x run berturut-turut (manual dulu, sebelum di-cron)
- [ ] Ada sample hasil yang divalidasi manual (benar/salah), dicatat di `tests/`
- [ ] Hasil tersimpan ke database dengan schema yang konsisten
