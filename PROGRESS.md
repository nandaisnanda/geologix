# PROGRESS.md — GeoLogix AI

## Status: FASE 6 SELESAI (2026-07-20) — README.md + PITCH.md ditulis dari
## hasil nyata. Fase 0-6 KOMPLET. LIVE: https://geologix.vercel.app + API
## https://geologix-api.onrender.com (DB Supabase).
## Observasi otomatis 3 hari (SPEC step 16) berjalan s/d 22 Juli.
## ml/ TETAP TERLARANG: log konsisten (pasca-filter dangling) baru mulai
## 2026-07-20 — butuh BEBERAPA MINGGU-BULAN akumulasi cron (SPEC Bagian 4:
## ideal 3-6 bulan). Keputusan gate ML dicek ulang: 36 log, span 18-19 Jul
## saja (<24 jam data) saat sesi ini — JAUH dari cukup.

## MENGGANTUNG SAAT /clear (cek di awal sesi baru!)
1. **Cron `[schedule]` MASIH BELUM TERBUKTI** — s/d 2026-07-19 18:22Z
   (01:22 WIB 20 Jul) belum ada satu pun run `[schedule]` di `gh run list`
   (weather-risk jadwal 18:07Z telat >15 mnt; delay GitHub biasa, semua
   workflow state=active). Jadwal berikut: weather-risk 00:07Z (07:07 WIB).
   Kalau TIDAK ada run `[schedule]` sama sekali s/d pagi 20 Jul WIB —
   investigasi (catatan: cron di repo private butuh aktivitas repo; cek juga
   tab Actions di web).
2. Opsional (keputusan user): naikkan layer road-error dashboard jadi
   default ON — data road_errors kini bersih (736 baris full-area + 423
   sample Menteng); dan persempit API_CORS_ORIGINS di Render.

## Selesai (sesi Fase 6, 2026-07-20)
- **Utang #1 & #2 sesi lalu BERES:**
  - Run CI 29697090519 (pertama dgn --boundary-jabodetabek
    --dangling-persist major) SUKSES 46m14s. Log id 37: dangling terdeteksi
    179.582 → **dangling_saved=16** (skipped 179.566), disconnected 315,
    oneway 405 → 736 temuan tersimpan. Persis ekspektasi; filter bekerja.
  - **P4 di-rerun atas data full-area PERTAMA**: 2.945 temuan
    terprioritaskan (dedupe road 423→141 Menteng + 736 CI; POI 2.072+32),
    bobot [4/7,2/7,1/7] CR=0, prio 0.1642-0.9999, top poi_anomalies:1927,
    dropped_no_population=0.
- **README.md (step 20) DITULIS** dari PROGRESS + 4 validation notes:
  justifikasi metode per pipeline, bukti otomasi, hasil validasi manual,
  7 known limitations, tabel insiden nyata, roadmap ML (kenapa belum),
  cara reproduce, atribusi data. Angka sudah memakai hasil run terbaru
  (dangling 179.582→16, P4 full-area 2.945).
- **PITCH.md (step 21) DITULIS**: narasi 15 detik + versi 1 kalimat,
  demo flow ±3 mnt (termasuk trik pre-warm cold start Render), Q&A
  antisipasi interview, tabel angka hafalan.
- **Gate ML diverifikasi ulang dgn query nyata** (permintaan user):
  pipeline_logs 36 baris, first 2026-07-18 20:26Z last 2026-07-19 15:05Z
  (sebelum run 37) — ML DITOLAK lagi, akumulasi konsisten baru mulai
  20 Jul. Jawaban terdokumentasi di README bagian Roadmap ML.

## Keputusan penting (sesi Fase 6)
- README menyebut angka temuan = TERSIMPAN pasca-kebijakan `major`
  (16 dangling), dengan angka deteksi mentah (179.582) dipakai sebagai
  narasi "temuan penting run full-area" — jujur dua-duanya.
- PITCH.md = dokumen internal persiapan interview, bukan dokumentasi teknis
  (dinyatakan di header file).
- aggregated_findings kini berisi batch lama (519 sample Menteng) + batch
  full-area (2.945). API /aggregated-findings dedupe per (source_pipeline,
  source_id) keep terbaru — batch lama tidak mengganggu tampilan.

## Selesai (sesi lanjutan Fase 5, 2026-07-20 — 2 utang + deploy + live)
- **Utang #1 BERES** (commit 74dc07a): runner P1 kini punya
  `--boundary-jabodetabek` (reuse dissolve P3, prepared geometry) — buang
  dangling artefak clip tepi; dan `--dangling-persist {all,major,none}` —
  keputusan user: **major** = simpan hanya dangling motorway..tertiary(+link)
  (dead-end arteri = kemungkinan error nyata; ujung gang/cul-de-sac perumahan
  hanya dihitung di detail log). Deteksi tetap persis SPEC 3.1; temuan
  dangling kini dianotasi kelas `highway` edge. jumlah_temuan di log =
  temuan TERSIMPAN. Workflow road-qa memakai kedua flag. 114 test pass
  (2 baru: anotasi highway + split_dangling).
- **Utang #2 BERES**: cron road-qa Sen/Rab/Jum -> **Sen/Kam** (+ Minggu via
  workflow_run) ~ 735 mnt/bln; total semua workflow ~1.500 dari kuota 2.000.
- **Cleanup DB (keputusan user)**: 183.568 baris batch full-area 19 Jul
  (artefak) DIHAPUS dari road_errors — verifikasi jumlah persis sebelum
  DELETE; sisa 423 baris sample Menteng valid. Jejak insiden tetap di
  pipeline_logs id 36 (JANGAN bingung: log id 36 bilang 183568 tapi barisnya
  memang sudah dihapus).
- **DEPLOY SELESAI (step 19)**:
  - Backend: Render Blueprint (`render.yaml` + `requirements-api.txt`
    minimal, terverifikasi cukup di venv bersih) ->
    https://geologix-api.onrender.com — /health + endpoint data OK dari luar.
    Free tier: sleep setelah idle, cold start ±1 mnt (catat di README).
  - Frontend: Vercel, Root Directory `frontend`, env VITE_API_BASE ->
    https://geologix.vercel.app (alias produksi; Deployment Protection
    dimatikan supaya publik). Insiden deploy: error "No FastAPI entrypoint"
    = Vercel scan root repo; fix = Root Directory `frontend` (+ Framework
    Vite), BUKAN pyproject tool.vercel.
  - `API_CORS_ORIGINS` di Render masih `*` — opsional persempit ke domain
    Vercel.
- Log `openmeteo_ingestion failed` (id 31) yang terlihat di dashboard =
  jejak insiden ReadTimeout KEMARIN yang sudah difix (retry) — bukan masalah
  baru; sudah dijelaskan ke user.

## Keputusan penting (sesi lanjutan Fase 5)
- Kebijakan dangling `major` = KEPUTUSAN DATA SEMANTIK per 2026-07-20:
  road_errors sebelum vs sesudah tanggal ini TIDAK sebanding (relevan utk
  Fase ML nanti — mulai hitung akumulasi log konsisten dari sini).
- Fase ML DITOLAK dulu (user tanya 2026-07-20): Fase 6 belum + log historis
  baru ±2 hari; butuh beberapa minggu akumulasi cron (CLAUDE.md #2, SPEC 5.2
  baris 12). Dokumentasikan di README sebagai roadmap.

## Selesai (sesi Fase 5, 2026-07-20 — api/main.py + frontend deck.gl)
- `src/api/main.py` (SPEC 5.2 urutan 9): FastAPI READ-ONLY, 6 endpoint:
  /health, /road-errors, /poi-anomalies, /weather-risk (tanpa geometri —
  deck.gl render dari h3_index, hemat ±90% payload), /aggregated-findings,
  /pipeline-logs. CORS via env `API_CORS_ORIGINS` (default *).
  Jalankan: `uvicorn src.api.main:app`.
- **Semantik filter waktu = SNAPSHOT** (PRD "kemarin vs sekarang"): default
  anchor = MAX(timestamp) dgn jendela `window_minutes` (road/poi 120 mnt —
  insert P1 full-area bisa puluhan menit; grid/agregat 15 mnt); `at=` mundur
  ke batch <= at; `since/until` = rentang eksplisit (riwayat penuh).
- `/aggregated-findings` DEDUPE (source_pipeline, source_id) keep computed_at
  terbaru via ROW_NUMBER — 3x run validasi P4 berjarak detik, jendela waktu
  tak bisa memisahkan; terverifikasi data nyata: 519 baris -> **173 unik**
  (persis angka validasi P4). lon/lat di-join dari tabel sumber.
- API TIDAK menulis pipeline_logs (keputusan: request baca bukan run
  pipeline; mencatatnya mengotori bukti otomasi).
- Test: **112 pass** (10 baru test_api.py): SQLite in-memory + tabel manual
  (geom TEXT WKT) + ST_X/ST_Y diregister sbg fungsi Python -> SQL produksi
  jalan apa adanya tanpa PostGIS; dependency override get_db_engine.
- **Uji server nyata ke Supabase**: /health ok; weather-risk 1.079 sel;
  road-errors total 183.568 (= log id 36); poi 2.072; logs 36.
- `frontend/` (SPEC 5.2 urutan 10): Vite + React 18 + deck.gl 9 + MapLibre
  (basemap Carto Positron, tanpa API key). 3 layer (H3HexagonLayer risk,
  ScatterplotLayer road & POI) + panel log + filter waktu datetime-local
  (WIB -> UTC ISO) + auto-refresh 5 mnt + legenda. `VITE_API_BASE` utk
  deploy (default localhost:8000). Warna dari skill dataviz tervalidasi
  (kategorikal slot 1-4 all-pairs PASS; risk = ramp biru sequential).
- **Layer road error DEFAULT OFF** + peringatan di UI (utang dangling
  artefak clip); weather + POI default on, limit road 5.000/req.
- Verifikasi visual: `npm run build` bersih; screenshot headless Chrome —
  hexagon risk + 2.072 POI + panel log render benar, konversi WIB benar,
  0 error console. **DIKONFIRMASI USER di browser (2026-07-20): backend +
  frontend jalan, dashboard menampilkan 3 layer** (basemap yang tak
  tertangkap screenshot headless terbukti hanya artefak capture).

## Keputusan penting (sesi Fase 5)
- Bentuk client masih netral: REST JSON generik, dashboard web = pembuktian
  step 18; kalau user jadi bikin aplikasi, endpoint sama bisa dipakai.
- deck.gl H3HexagonLayer dipilih persis sesuai PRD ("H3 hexagon layer");
  geometri hexagon sengaja tidak dikirim API (h3_index cukup).
- Deploy (step 19) DITUNDA: layer road-error belum layak dipublikasikan
  sebelum utang keputusan #1 (filter dangling) selesai.

## Langkah selanjutnya (sesi baru — FASE 6 dokumentasi)
0. **Cek 3 hal "MENGGANTUNG SAAT /clear" di atas dulu** (run CI #1 filter
   baru, rerun P4, bukti cron pertama).
1. **Fase 6 (step 20-21): README metodologi** — tulis dari hasil NYATA yang
   tercatat di file ini + validation notes di tests/ (justifikasi metode,
   keterbatasan, hasil validasi manual, insiden + penanganannya, URL live).
   Known limitation yang jujur = nilai plus. Narasi 15 detik + demo flow.
2. Pantau cron s/d 22 Juli (SPEC step 16) — run merah = prioritas interupsi.
3. Opsional: persempit API_CORS_ORIGINS di Render ke domain Vercel; setelah
   frontend stabil pertimbangkan naikkan layer road error jadi default ON
   (datanya kini bersih pasca-filter).

## ~~2 UTANG KEPUTUSAN~~ — SELESAI 2026-07-20 (lihat "Selesai" sesi lanjutan
## Fase 5 di atas: filter dangling major + boundary; jadwal Sen/Kam)

---

## Arsip: Fase 4 — CI terbukti jalan (status lama)

## Status lama: Fase 4 — 4/4 WORKFLOW CI TERBUKTI JALAN (run manual pertama
## sukses semua, 2026-07-19; log CI nyata di pipeline_logs id 23-36).

## Bukti run CI pertama (2026-07-19, semua via workflow_dispatch)
- `pipeline-osm-refresh` SUKSES 2m45s: mode `full_download` (log id 26),
  cache `osm-jabodetabek-v1-*` terisi (130MB clipped .pbf).
- `pipeline-poi-qa` SUKSES 3m25s — **run full-area P2 PERTAMA**: 46.979 POI,
  745.268 ruas jalan, **2.072 outlier** (Q1=8,71m Q3=22,83m upper=44,0m —
  konsisten statistik sample Menteng; rasio 4,4% vs 3,8%) (log id 27-28).
- `pipeline-weather-risk` SUKSES 8m58s (run ke-3): 1.079 sel, 348 hotspot,
  risk_max=0,3333 — tepat bobot hist 1/3 karena rain=0,00 semua sel (jam
  kering kemarau; kriteria realtime ternormalisasi 0) (log id 32-35).
- `pipeline-road-qa` SUKSES 57 menit (run ke-3) — **run full-area P1
  PERTAMA**: 703.926 node, 1.708.734 edge; temuan 183.568 =
  **182.848 dangling (26% node!)** + 315 disconnected + 405 oneway (log 36).
  Dependency `workflow_run` refresh->road-qa TERBUKTI bekerja (terpicu
  otomatis 13:38 setelah refresh sukses).

## Insiden CI run pertama (semua sudah ditangani, jejak dibiarkan)
1. **startup_failure semua run (0-1 dtk)** = billing akun: GitHub Pro $0
   (diskon education) tapi otorisasi kartu GAGAL -> GitHub blokir seluruh
   Actions. Fix: user update kartu (hold ~Rp18rb = otorisasi, bukan charge).
   Pelajaran: startup_failure seragam + instan = cek billing, bukan YAML.
2. **ReadTimeout Open-Meteo** dari runner (IP Azure shared; log id 25, 31).
   Fix: `fetch_openmeteo._get_batch` retry timeout/koneksi (commit d3...,
   102 test pass). Catatan: `gh run rerun` memakai SHA lama — fix baru
   terbukti lewat run BARU.
3. **road-qa OOM**: runner shutdown 12,5 mnt tanpa output (RAM 16GB habis
   saat graph_from_xml Jabodetabek). Fix percobaan 1: swap fixed 16GB ->
   GAGAL "No space left" (disk /mnt tak selega dokumentasi). Fix final:
   **swap dinamis** (mount terlega, margin 6GB, cap 16GB) -> sukses 57 mnt
   (lambat karena swap-thrash; budget timeout 90 mnt cukup).
- PERINGATAN INTEGRITAS (tetap relevan): klaim "CI sudah jalan" tanpa cek
  `gh run list` + `pipeline_logs` pernah terbantah data. Selalu verifikasi.

## 2 UTANG KEPUTUSAN sebelum data full-area dipercaya (prioritas sesi dekat)
1. **182.848 dangling P1 full-area BUKAN semua error nyata** — campuran
   (a) artefak clip tepi Jabodetabek: runner CI tidak memberi boundary
   polygon ke `detect_dangling_nodes` (flag `--kecamatan` tak terpakai di
   full-area), dan (b) cul-de-sac perumahan asli. Konsekuensi DB: ~183k
   baris/run x 4 run/minggu = ~730k baris/minggu ke `road_errors` — TIDAK
   berkelanjutan. Keputusan: tambah opsi boundary Jabodetabek di runner P1
   + pertimbangkan filter cul-de-sac/severity sebelum simpan. SEBELUM itu
   beres, **JANGAN jalankan ulang P4** (akan mengagregasi 183k temuan
   termasuk artefak).
2. Kuota Actions private KETAT: estimasi terpakai ~1.700-1.800 mnt/bulan
   (road-qa 57 mnt x 4/minggu ~ 980; weather ~720; sisanya ~100) dari
   2.000. Kalau road-qa tetap selambat ini, turunkan ke 2x/minggu atau
   percepat (keputusan bareng poin 1 — filter dangling juga memangkas
   waktu tulis DB).

## Selesai (sesi Fase 4 lanjutan, 2026-07-19 — P4 jalan nyata + repo GitHub)
- **Repo GitHub: `nandaisnanda/geologix` (PRIVATE)** — dibuat via gh CLI,
  push `main`, secret `DATABASE_URL` di-set. Riwayat: sempat dibuat di akun
  `ananneeeeetunai` (public), lalu dipindah; 4 workflow di repo lama
  DI-DISABLE (cron dobel = duplikat DB + 2x budget Open-Meteo). Repo lama
  belum dihapus (butuh manual). PERHATIAN: repo private = 2.000 menit
  Actions/bulan — jadwal cron ini butuh ±2.700-5.000 menit/bulan, kuota bisa
  habis pertengahan bulan; pertimbangkan `--visibility public`.
- `data_ingestion/fetch_worldpop.py`: WorldPop IDN 2020 1km UN-adjusted
  (jiwa/km2, ~10.5MB, CC BY 4.0), download+cache idempotent, log
  `worldpop_ingestion`; `sample_density()` rasterio, nodata/negatif -> NaN
  (tidak diam-diam 0). Konstanta `WORLDPOP_TIF_URL` di config.py (pakai
  `or`, pelajaran insiden CHIRPS env kosong).
- Runner `pipeline_4_aggregator/__main__.py`:
  `python -m src.pipeline_4_aggregator` → baca `road_errors`+`poi_anomalies`
  (ST_X/ST_Y), dedupe temuan antar-run validasi (kunci identitas, ambil
  `detected_at` terbaru), rakit 3 kriteria → `prioritize.run()`.
  Temuan NaN populasi dibuang eksplisit (tercatat di ringkasan).
- Test: **100 pass** (6 baru: 3 fetch_worldpop raster sintetis + nodata->NaN,
  3 runner: dedupe+mapping, severity asing ditolak, buang NaN populasi).
- **Checklist SPEC 5.4 Pipeline 4: TERPENUHI.**
  - 3x run identik: 173 temuan (141 P1 + 32 P2 pasca-dedupe), bobot
    [0.5714, 0.2857, 0.1429] CR=0, prio 0.4197-0.9988, top poi_anomalies:79
    (log id 20-22; 519 baris `aggregated_findings`; WorldPop log id 19).
  - Validasi manual: `tests/validation_notes_pipeline4.md` — urutan bisa
    dijelaskan penuh (POI conf 1.0 pusat kota + ease 5 teratas; oneway high
    ~0.90; dangling medium terbawah road). Cek tangan peringkat 1 cocok.
  - Hasil tersimpan di DB schema konsisten.

## Keputusan penting (sesi Fase 4 lanjutan)
- **Repo TETAP PRIVATE (keputusan user, final — alasan: anti-copas).**
  Konsekuensi kuota 2.000 menit Actions/bulan ditangani dengan JADWAL HEMAT
  (total ±1.500 menit/bulan): weather-risk per 6 jam (`7 */6 * * *`, ~4,3k
  unit Open-Meteo/hari), road-qa Sen/Rab/Jum (+ Minggu via workflow_run),
  poi-qa Sen/Kam, osm-refresh tetap mingguan. Justifikasi = mitigasi SPEC
  Bagian 10 ("jadwalkan pipeline besar tidak terlalu sering"). Kalau repo
  nanti di-public-kan (mis. saat melamar), jadwal boleh dinaikkan lagi
  (weather per 3 jam = batas budget Open-Meteo).
- **Sumber temuan P4 = P1 + P2 saja** (SPEC Bagian 3 P4: severity "dari
  P1/P2"): grid risiko P3 kontinu per jam, bukan "error yang bisa
  diperbaiki" — tak punya severity/ease bermakna; P3 masuk ringkasan lewat
  dashboard + pipeline_logs (PRD P4). 
- **Severity P2 = 1 + 2*confidence_score** (0..1 -> skala 1..3 yang sama
  dengan mapping P1 low=1/medium=2/high=3).
- **ease_of_fix per jenis error** (skor manual 1-5 SPEC): poi_anomaly=5,
  dangling_node=4, oneway_inconsistency=3, disconnected_component=2.
- **Populasi = WorldPop 2020 1km UN-adjusted** sampling titik temuan;
  nodata -> temuan dibuang eksplisit, bukan 0.
- Validasi severity/ease dilakukan SETELAH dedupe (hanya baris terpakai).

## Langkah selanjutnya (sesi baru)
0. **Fase 5 (backend FastAPI `api/main.py` dulu, baru frontend)** — boleh
   mulai sekarang, paralel dengan observasi 3 hari. Catatan arah client:
   user mempertimbangkan APLIKASI (bukan web dashboard) — backend FastAPI
   netral terhadap itu; keputusan bentuk client belum final.
1. Pantau cron s/d 22 Juli (SPEC step 16): run merah di GitHub = prioritas
   interupsi. Cek `gh run list` + `pipeline_logs`.
2. Kerjakan 2 UTANG KEPUTUSAN di atas (dangling full-area + kuota) —
   idealnya sesi terpisah sebelum Fase 6; WAJIB sebelum P4 dijalankan
   ulang dan sebelum layer road-error dipakai dashboard.
2. Setelah P1/P2 jalan full-area di CI: jalankan ulang P4 (temuan sekarang
   masih sample Menteng — lihat validation notes P4 poin 3.2).
3. 3 keputusan terbuka lama: boundary full-area P1, gang motorcycle-only
   di filter osmium, jarak-dari-tepi poligon POI area.
4. Fase 5: `api/main.py` (FastAPI) + frontend deck.gl.

---

## Arsip: Fase 4 sesi awal — workflows + prioritize.py

## Selesai (sesi Fase 4, 2026-07-19)
- `.github/workflows/` — 4 workflow (SPEC 5.2 urutan 7, nama persis SPEC 5.1):
  - `pipeline-osm-refresh.yml`: cron mingguan `0 0 * * 0` persis SPEC 5.2b;
    `actions/cache` restore/save path `jabodetabek.osm.pbf` +
    `osm_replication_state.txt`; jalankan `python -m src.data_ingestion.fetch_osm`
    (incremental/full + fallback sudah di dalam modul).
  - `pipeline-road-qa.yml`: cron harian `30 2 * * 1-6` (Sen-Sab) +
    `workflow_run` setelah osm-refresh sukses (dependency SPEC 5.2b) — Minggu
    TIDAK pakai cron supaya tidak dobel. Restore cache OSM (+fallback
    fetch_osm kalau cache miss/evicted), konversi 2 tahap
    `osmium tags-filter w/highway=<subset> | osmium cat`, lalu
    `python -m src.pipeline_1_road_qa --xml`.
  - `pipeline-poi-qa.yml`: cron harian `45 1 * * *`; cache
    `java-latest-free.shp.zip` (2.2GB) key per-minggu ISO TANPA restore-keys
    (fallback zip lama membatalkan refresh mingguan); `fetch_osm_poi` →
    `python -m src.pipeline_2_poi_qa`.
  - `pipeline-weather-risk.yml`: cron `7 */3 * * *` (PER 3 JAM — lihat
    keputusan); cache statis `weather-static-v1` (grid H3 + baseline CHIRPS,
    dibangun ulang hanya saat miss); `fetch_openmeteo` →
    `python -m src.pipeline_3_weather_risk`.
  - Semua: `workflow_dispatch` (uji manual), `concurrency` anti-tumpang-tindih,
    `timeout-minutes`, secret `DATABASE_URL` (Supabase Session Pooler, IPv4).
- `pipeline_4_aggregator/prioritize.py` (SPEC 5.2 urutan 8, Bagian 3 P4):
  REUSE `compute_ahp_weights`/`min_max_normalize`/`wlc_combine` dari P3 —
  bukan implementasi ulang. Kriteria P4: severity, population_density,
  ease_of_fix (1-5). `prioritize()` → priority_score [0,1] urut menurun;
  `run()` → simpan `aggregated_findings` + log `pipeline_logs`
  (jumlah_temuan = jumlah temuan diprioritaskan; gagal → log `failed`).
- `db/writer.py`: + `row_to_aggregated_finding()` / `save_aggregated_findings()`.
- Test: **94 pass** total (8 baru di `test_prioritize.py`: bobot eksak
  [4/7,2/7,1/7] CR=0, skor vs hitungan tangan, NaN ditolak, ease di luar 1-5
  ditolak, kolom hilang/kosong, matriks tak konsisten raise
  AhpConsistencyError, run simpan+log, run gagal tercatat failed).
- YAML keempat workflow tervalidasi parse (PyYAML).

## Keputusan penting (sesi Fase 4)
- **Cron weather-risk PER 3 JAM (`7 */3 * * *`), bukan per jam seperti teks
  SPEC step 15:** budget Open-Meteo free tier 10k unit/hari, 1 lokasi = 1 unit
  (terverifikasi empiris, insiden 429 log id 12). Per jam = ~26k/hari (3x
  budget); per 3 jam = ~8,6k/hari, muat TANPA subset grid (peta risiko parsial
  ditolak — kehilangan makna operasional). Terdokumentasi di komentar workflow.
- **Cache GitHub Actions IMMUTABLE — "overwrite key yang sama" (SPEC 5.2b)
  diimplementasikan** dengan key unik per-run `osm-jabodetabek-v1-<run_id>` +
  `restore-keys: osm-jabodetabek-v1-` (restore ambil entri terbaru se-prefix).
- **Filter osmium produksi = subset drivable setara `network_type="drive"`
  OSMnx** (motorway..service,road + link) — menutup inkonsistensi sample vs
  produksi yang dicatat di docstring graph_builder.py; hasil CI kini
  merepresentasikan hasil validasi manual Menteng. Perluasan ke gang
  motorcycle-only (motorcar=no, motorcycle=yes) MASIH TERBUKA (lihat di bawah).
- **Matriks pairwise P4 (keputusan proyek):** severity:populasi=2,
  severity:ease=4, populasi:ease=2 → konsisten sempurna, bobot eksak
  [4/7, 2/7, 1/7], CR=0. Severity = sinyal risiko langsung; populasi
  memodulasi dampak; kemudahan perbaikan = tie-breaker quick-win. Semua
  kriteria arah benefit. `SEVERITY_SCORE`: low=1, medium=2, high=3.
- **NaN kriteria P4 DITOLAK (raise)**, bukan dianggap 0 — `priority_score`
  non-nullable; temuan tanpa data populasi harus dilengkapi dulu.
- **Keputusan tertunda yang TETAP TERBUKA** (CI tetap jalan; hasil P1/P2 masih
  memuat false positive yang sudah dipetakan di validation notes):
  1. Runner P1 full-area TANPA boundary polygon → dangling artefak clip di
     tepi Jabodetabek ikut ter-flag (runner baru dukung `--kecamatan`).
     Opsi: tambah flag boundary Jabodetabek penuh di runner P1.
  2. Gang motorcycle-only belum masuk filter osmium (lihat di atas).
  3. Jarak POI area dari `representative_point`, bukan tepi poligon
     (validation notes P2 poin 2).

## Langkah selanjutnya (Fase 4 lanjutan, sesi baru)
1. `git init` + push repo ke GitHub (folder BELUM repo git), set secret
   `DATABASE_URL` di repo Settings → jalankan tiap workflow via
   `workflow_dispatch` manual dulu (checklist 5.4: 3x run).
2. Setelah jalan: pantau 3 hari (SPEC step 16), cek `pipeline_logs` terisi.
3. Putuskan 3 keputusan terbuka di atas (boundary P1, filter motor, POI area).
4. Runner agregasi P4 (perakit input `prioritize()` dari road_errors/
   poi_anomalies/weather_risk_grid + sumber populasi WorldPop) — `prioritize.py`
   sengaja hanya berisi matematika+persistence; ingest WorldPop belum ada.

---

## Arsip: Fase 3 lanjutan — sisa P3 SELESAI (checklist SPEC 5.4 terpenuhi)

## Selesai (sesi Fase 3 lanjutan, 2026-07-19 — semua sisa P3)
- `pipeline_3_weather_risk/normalize.py` (SPEC 3.1): Min-Max persis rumus;
  degenerate max==min -> 0.0 semua (keputusan: kriteria tanpa variasi netral
  di WLC); NaN dipertahankan.
- `pipeline_3_weather_risk/ahp_weights.py` (SPEC 3.2): eigenvector utama
  (np.linalg.eig), tabel RI Saaty, CI/CR; **CR > 0.1 raise AhpConsistencyError**
  (SPEC 5.3 poin 2). Matriks P3 (keputusan proyek): 2 kriteria
  [rainfall_realtime, hist_hotspot], preferensi 2:1 -> w=[2/3, 1/3], CR=0
  (n<=2 didefinisikan CR=0, RI=0).
- `pipeline_3_weather_risk/wlc_combine.py` (SPEC 3.3): RiskIndex=Σwi·xi_norm;
  validasi sum(w)=1 dan xi di [0,1]; NaN -> RiskIndex NaN (tidak diam-diam 0).
- `data_ingestion/fetch_chirps.py` (SPEC Bagian 6): CHIRPS v2.0 **annual**
  GeoTIFF CHC UCSB, baca REMOTE via GDAL `/vsicurl/` (server dukung HTTP
  range; hanya ratusan KB per tahun, bukan 57MB/file) + fallback download
  cache `data/raw/chirps/`. Jendela 2020-2024 (annual 2025 belum rilis per
  2026-07). Metrik baseline: mean total hujan TAHUNAN 5 th per sel ->
  `data/raw/chirps_baseline.csv`. **Run nyata: 1.079 sel, 0 NaN, 5/5 th
  valid, 1.620-5.028 mm/th (gradien pesisir->Bogor benar)** — log id 15.
- `pipeline_3_weather_risk/hotspot_gi_star.py` (SPEC 3.4): rumus Gi* persis
  SPEC; wij biner contiguity k-ring 1 H3 TERMASUK diri sendiri (definisi
  "star"); S populasi; p satu sisi ke atas via math.erfc (tanpa scipy);
  degenerate S=0 -> z=0. Input NaN ditolak (harus difilter dulu).
- `db/writer.py`: + `row_to_weather_risk()` / `save_weather_risk_grid()`
  (POLYGON hexagon WKT SRID 4326).
- Runner `pipeline_3_weather_risk/__main__.py`:
  `python -m src.pipeline_3_weather_risk [--openmeteo-csv X --chirps-csv Y]`
  → merge snapshot+baseline per h3_index (NaN dibuang SEBELUM Gi*) → Gi* →
  Min-Max kedua kriteria → AHP → WLC → `weather_risk_grid` + log.
  `jumlah_temuan` = jumlah hotspot signifikan (bukan jumlah sel; sel di detail).
- Test: **86 pass** total (27 baru: 4 normalize, 5 ahp, 5 wlc, 5 chirps,
  4 gi_star, 2 writer, 3 runner — salah satunya cek angka z Gi* vs hitungan
  tangan).
- **Checklist SPEC 5.4 Fase 3: TERPENUHI.**
  - 3x run berturut-turut identik: 1.079 sel, 348 hotspot, bobot AHP
    [0.6667, 0.3333] dengan **CR = 0.0** (lolos syarat CR <= 0.1 SPEC 3.2),
    risk 0,0202-0,9723 (log id 16-18; 3.237 baris di `weather_risk_grid`).
  - Validasi manual: `tests/validation_notes_pipeline3.md`. Inti: hotspot
    SEMUA di selatan (Bogor, 4.328 vs 2.662 mm/th) — konsisten "kota hujan";
    sel risk tertinggi (0,972) di Bogor selatan = hujan realtime max jam itu
    + z=4,23. Bukan artefak.
  - Hasil tersimpan di DB schema konsisten.

## Keputusan penting (sesi Fase 3 lanjutan)
- **BUG DIPERBAIKI — `.env` berisi `CHIRPS_BASE_URL=` kosong** meng-override
  default config (os.environ.get dengan default tidak menolong kalau var ada
  tapi kosong). Fix: `os.environ.get(...) or <default>` di config.py. Log
  `chirps_ingestion` id 14 `failed` (MissingSchema) = jejak insiden ini.
- **Baseline pakai CHIRPS ANNUAL, bukan monthly/dekad:** untuk metrik mean
  multi-tahun, pola SPASIAL-lah yang diuji Gi* — mean bulanan = annual/12
  (info spasial identik), sementara monthly = 60 file gz x 14MB yang tak bisa
  dibaca remote. Kalau nanti butuh metrik ekstrem (max bulanan dsb), turunkan
  ke monthly.
- **Kriteria 2 WLC = z-score Gi* dinormalisasi** (bukan mm historis mentah):
  baseline masuk sebagai "kerawanan teruji statistik" sesuai peran Gi* di
  SPEC (P3: hotspot baseline), bukan besaran hujan mentah kedua.
- 348/1079 (32%) sel hotspot — wilayah signifikan bersambung karena gradien
  orografis kuat; opsi seleksi lebih ketat (FDR/ambang z) ditunda, putuskan
  sebelum dashboard Fase 5 (lihat validation notes poin 4).

## Langkah selanjutnya (Fase 4, sesi baru)
1. `.github/workflows/*.yml` (SPEC 5.2 urutan 7): osm-refresh mingguan,
   road-qa & poi-qa harian, weather-risk per jam — TAPI budget Open-Meteo
   free tier (10k unit/hari) tidak cukup untuk per jam x 1.079 sel (~26k):
   putuskan frekuensi (per 3 jam ≈ 8,6k) atau subset grid.
2. Keputusan tertunda Fase 1/2 yang deadline-nya "sebelum CI": filter
   drivable-motor P1, jarak-dari-tepi poligon POI area P2.
3. `pipeline_4_aggregator/prioritize.py` (AHP+WLC reuse dari
   `ahp_weights.py`/`wlc_combine.py` — sudah generik, tinggal matriks
   kriteria P4: severity, populasi WorldPop, kemudahan perbaikan).

---

## Arsip: Fase 3 sesi awal — h3_grid + fetch_openmeteo

## Selesai (sesi Fase 3, 2026-07-19)
- **`H3_RESOLUTION = 7` ditetapkan di `config.py`** (keputusan yang didelegasikan
  sejak Fase 0): avg hex 5,16 km² (edge ~1,2 km) → 1.079 sel utk Jabodetabek.
  Alasan: model cuaca Open-Meteo utk Indonesia ~11-25 km — grid lebih halus
  dari sumber tidak menambah info; res 8 = 7x beban API/DB, res 6 terlalu kasar.
- `pipeline_3_weather_risk/h3_grid.py` (SPEC 5.2 urutan 6, file pertama P3):
  boundary = dissolve `jabodetabek.shp` (union_all, reproject 4326),
  `h3.geo_to_cells()` (containment pusat sel, default polyfill), sel diurutkan
  (deterministik), GeoDataFrame h3_index + lat/lng pusat sel (titik sampling
  Open-Meteo) + geometri hexagon → `data/raw/h3_grid_jabodetabek.gpkg`
  + log `pipeline_logs`. **Run nyata: 1.079 sel res 7** (log id 11).
- `data_ingestion/fetch_openmeteo.py` (SPEC 5.2 urutan 5): sampling per pusat
  sel H3, request multi-lokasi batch 100 koordinat, `current=precipitation`
  (mm 1 jam terakhir, UTC) → `data/raw/openmeteo_latest.csv` (snapshot,
  overwrite tiap run) + log `pipeline_logs`.
  **Run nyata: 1.079 sel, weather_time 2026-07-19T07:00, rain 0-0,4 mm
  (masuk akal utk Juli/kemarau)** — log id 13.
- Test: 59 pass total (13 baru: 5 test_h3_grid, 8 test_fetch_openmeteo —
  batching, response dict 1-lokasi, retry 429, mismatch lokasi, main+log).

## Keputusan penting (sesi Fase 3)
- **Rate limit Open-Meteo TERVERIFIKASI EMPIRIS:** free tier menghitung tiap
  LOKASI sebagai 1 unit call. Burst 11 batch x 100 lokasi tanpa jeda → HTTP
  429 (log id 12, `failed`, sengaja dibiarkan sebagai jejak insiden).
  Solusi di `fetch_openmeteo.py`: `BATCH_PAUSE_S=10` antar-batch (limit
  ~600 unit/menit) + retry khusus 429 (`RETRY_MAX=4`, backoff 30 dtk).
  Run penuh sekarang ~2 menit.
- **PERHATIAN CI Fase 4 (budget API):** cron per jam x 1.079 sel = ~26k
  unit/hari > budget free tier 10.000/hari. Wajib pilih: turunkan frekuensi
  cron (misal per 3 jam ≈ 8,6k/hari) atau subset grid. Dicatat juga di
  komentar `BATCH_SIZE` fetch_openmeteo.py.
- `weather_time` seragam utk semua sel per run (1 jam data) — kolom disimpan
  di CSV supaya downstream (normalize/WLC) bisa cek konsistensi jam data.
- Riwayat antar-jam TIDAK disimpan di CSV (overwrite) — riwayat hidup di
  tabel `weather_risk_grid` saat runner P3 lengkap.

## Langkah selanjutnya (Fase 3 lanjutan, sesi baru)
1. `pipeline_3_weather_risk/normalize.py` — Min-Max scaling (SPEC 3.1).
2. `pipeline_3_weather_risk/ahp_weights.py` — pairwise matrix, eigenvector,
   CI/CR, WAJIB raise kalau CR > 0.1 (SPEC 3.2 + 5.3 poin 2).
3. `pipeline_3_weather_risk/wlc_combine.py` — RiskIndex = Σ wi·xi_norm (SPEC 3.3).
4. `data_ingestion/fetch_chirps.py` — histori 5 tahun (baseline Gi*).
   `CHIRPS_BASE_URL` di config masih string kosong — tentukan endpoint dulu.
5. `pipeline_3_weather_risk/hotspot_gi_star.py` — Getis-Ord Gi* (SPEC 3.4),
   bobot spasial = contiguity antar-hex (k-ring 1 natural di H3).
6. Runner `pipeline_3_weather_risk/__main__.py` → tabel `weather_risk_grid`
   (schema sudah ada di models.py) + checklist SPEC 5.4 (3x run + validasi
   manual).

---

## Arsip: Fase 2 — Pipeline 2 POI Validation SELESAI (checklist SPEC 5.4
## terpenuhi)

## Validasi data nyata Fase 2 (2026-07-19, setelah download selesai)
- `java-latest-free.shp.zip` selesai didownload (2.243MB), 22 layer valid.
- Ingest penuh: **46.980 POI** Jabodetabek (22.097 titik + 24.883 area) →
  `data/raw/poi_jabodetabek.gpkg` + log `poi_ingestion`.
- **Checklist SPEC 5.4 Fase 2: TERPENUHI.**
  - 3x run `--kecamatan Menteng` berturut-turut sukses & deterministik:
    847 POI, Q1=8,93m Q3=23,51m batas atas=45,40m, 32 outlier/run —
    3 log di `pipeline_logs`, 96 baris di `poi_anomalies` (32x3).
  - Validasi manual: `tests/validation_notes_pipeline2_menteng.md`. Inti:
    rumus benar (Haversine dicek vs nilai analitik + OSM API live; IQR persis
    SPEC 2.2); 28/32 outlier dari layer AREA — sebagian artefak
    `representative_point` kompleks besar yang tepinya menempel jalan
    (Plaza Indonesia d_tepi=0m), sisanya objek dalam blok (kolam/lapangan)
    yang jaraknya riil; 4 POI titik terkonfirmasi live di OSM (indoor mall /
    tengah Bundaran HI) — bukan salah koordinat.
  - Hasil tersimpan di DB dengan schema konsisten.
- **Keputusan TERTUNDA (sebelum CI Fase 4):** jarak POI area diukur dari
  `representative_point`, bukan tepi poligon → kompleks besar menempel jalan
  ikut ter-flag (~6/32 sample). Opsi: ukur dari batas poligon asli, atau
  ambang IQR terpisah per layer titik/area. Lihat validation notes poin 2.

## Selesai (sesi Fase 2, 2026-07-19)
- `data_ingestion/fetch_osm_poi.py` (SPEC 5.2c): `ensure_shp_zip()` idempotent
  (pakai zip lokal / download Geofabrik), baca layer `gis_osm_pois_free_1`
  (titik) + `gis_osm_pois_a_free_1` (area, dikonversi `representative_point()`),
  prefilter bbox boundary, `gpd.clip()` ke Jabodetabek atau 1 kecamatan
  (WADMKC), simpan `data/raw/poi_jabodetabek.gpkg`, log `poi_ingestion`.
- `pipeline_2_poi_qa/spatial_join.py` (SPEC Bagian 3 P2.1): `haversine_km()`
  vectorized persis rumus SPEC (R=6371 dari config); jalan dari layer
  `gis_osm_roads_free_1` di .shp.zip yang SAMA (P2 butuh geometri saja, bukan
  topologi — tetap di jalur shapefile sesuai 5.2c); kandidat terdekat via
  STRtree derajat + `shapely.shortest_line`, jarak final Haversine (meter).
- `pipeline_2_poi_qa/detect_outliers.py` (SPEC Bagian 3 P2.2): Q1/Q3
  `np.percentile`, batas atas = Q3 + 1.5×IQR (`IQR_OUTLIER_MULTIPLIER`).
- `db/writer.py`: + `finding_to_poi_anomaly()` / `save_poi_anomalies()`
  → tabel `poi_anomalies`.
- Runner `pipeline_2_poi_qa/__main__.py`:
  `python -m src.pipeline_2_poi_qa [--kecamatan X | --gpkg path]` →
  join jarak → IQR → `poi_anomalies` + log `pipeline_logs`. Bbox jalan =
  bbox POI + margin 0.05° (hindari jarak menggelembung di tepi area).
- Test: 46 pass total (14 baru: 4 fetch_osm_poi, 6 spatial_join+outliers
  sintetis, ... lihat tests/test_fetch_osm_poi.py, test_spatial_join.py,
  test_detect_outliers.py, test_writer.py).

## Keputusan penting (sesi Fase 2)
- **`java-latest-free.shp.zip` TIDAK ada di data/raw/** (cek juga seluruh
  folder Downloads) — download 2.2GB dari Geofabrik dijalankan background via
  `ensure_shp_zip()`. Validasi data nyata (checklist 5.4: 3x run + validasi
  manual sample) BELUM jalan — tunggu download selesai.
- **Sumber jalan Pipeline 2 = layer `gis_osm_roads_free_1` dari .shp.zip**,
  bukan graph .pbf Pipeline 1: P2 hanya butuh geometri jalan untuk jarak,
  bukan topologi; memakai satu sumber shapefile konsisten dengan pemisahan
  dua sumber OSM di SPEC 5.2c.
- **`confidence_score` (SPEC tidak menetapkan):** pelampauan batas atas dalam
  satuan IQR, linear 0→1 antara pagar dalam Tukey (Q3+1.5·IQR) dan pagar
  luar (Q3+3·IQR); ≥ pagar luar = 1.0; IQR=0 (degenerate) → 1.0.
- Jarak disimpan METER (`distance_to_road_m`, konsisten schema models.py)
  meski Haversine dihitung km (R=6371).
- Pemilihan jalan terdekat dilakukan di ruang derajat (STRtree); di lintang
  Jabodetabek (cos φ ≈ 0.995) tidak mengubah kandidat terpilih — jarak final
  tetap Haversine sesuai SPEC.

## Langkah selanjutnya (Fase 3 — Pipeline 3 Weather-Risk, sesi baru)
1. Baca SPEC Bagian 3 Pipeline 3 (Min-Max, AHP CR<=0.1, WLC, Getis-Ord Gi*)
   dan bagian data cuaca (Open-Meteo/CHIRPS, Bagian 6) sebelum mulai.
2. `H3_RESOLUTION` belum ditetapkan — keputusan didelegasikan ke `h3_grid.py`
   (lihat catatan Fase 0).
3. Dua keputusan tertunda untuk CI Fase 4 (bukan blocker Fase 3):
   filter drivable-motor P1 (validation notes P1 poin 3) dan jarak-dari-tepi
   poligon POI area P2 (validation notes P2 poin 2).
4. Catatan: `java-260717.osm.pbf` (853MB) ada di `C:\Users\ACER\Downloads`
   — kemungkinan pbf baru untuk Pipeline 1, bukan urusan Fase 2/3.

---

## Arsip: Fase 1 — Pipeline 1 Road QA SELESAI (checklist SPEC 5.4 terpenuhi)

## Selesai (sesi lanjutan Fase 1, 2026-07-19 — step 5-7 SPEC Bagian 8)
- `detect_dangling_nodes.py` (SPEC 3.1): degree(v)=1 pada `nx.Graph(G)`
  (collapse arah+edge paralel), kecualikan tag `turning_circle`/`turning_loop`
  (cul-de-sac asli) dan node di luar polygon boundary (artefak clip).
  Severity: medium.
- `detect_disconnected.py` (SPEC 3.2): BFS components (`nx.connected_components`),
  syarat n>1 dan |Ci|/|Cmax| < `DISCONNECTED_COMPONENT_MIN_RATIO`; 1 temuan
  per komponen, node representatif = min(comp) (deterministik). Severity: high.
- `detect_oneway_issues.py` (SPEC 3.3): Tarjan SCC
  (`nx.strongly_connected_components`), flag edge oneway lintas-SCC
  (tak ada path balik). Severity: high.
- `db/writer.py` + `finding_to_road_error()` / `save_road_errors()` →
  tabel `road_errors` (WKT POINT SRID 4326).
- Runner `pipeline_1_road_qa/__main__.py`:
  `python -m src.pipeline_1_road_qa --graphml <file> [--kecamatan X]` atau
  `--xml <file>` → 3 deteksi → `road_errors` + log `pipeline_logs`.
  (File runner di luar daftar SPEC 5.1 — keputusan minimal untuk entrypoint CI.)
- Test: 28 pass total (13 baru: 11 detektor sintetis + 2 writer).
- **Checklist SPEC 5.4 Fase 1: TERPENUHI.**
  - 3x run berturut-turut sukses & deterministik di sample Menteng:
    141 temuan/run (69 dangling, 2 disconnected, 70 oneway) — tercatat di
    `pipeline_logs`, 423 baris di `road_errors` (141x3).
  - Validasi manual sample vs OSM API live: lihat
    `tests/validation_notes_pipeline1_menteng.md`. Inti: rumus benar;
    false positive sample berasal dari filter `drive` (gang `motorcar=no`
    tak ikut graph) dan pemotongan area (path balik oneway di luar polygon).
  - Hasil tersimpan di DB dengan schema konsisten.

## Keputusan penting (sesi step 5-7)
- **BUG DIPERBAIKI — kolom ID OSM wajib BigInteger:** insert pertama gagal
  `NumericValueOutOfRange` karena ID node OSM > 2^31. `models.py` diubah
  (`osm_node_id`, `osm_way_id`, `osm_poi_id` → BigInteger) + `ALTER TABLE`
  langsung di Supabase (road_errors, poi_anomalies). 3 baris `failed` di
  `pipeline_logs` adalah jejak insiden ini — sengaja tidak dihapus.
- **Keputusan filter produksi TERTUNDA (deadline: sebelum CI Fase 4):**
  jaringan `drive` mengecualikan gang `motorcar=no` `motorcycle=yes` yang
  relevan untuk armada motor — sumber utama false positive dangling &
  disconnected di Menteng. Opsi: filter drivable-motor kustom. Lihat
  `tests/validation_notes_pipeline1_menteng.md` poin 3.
- `DISCONNECTED_COMPONENT_MIN_RATIO=0.05` dipertahankan (komponen sample
  berrasio 0.003, jauh di bawah) — validasi ulang di graph penuh Fase 4.

## Review graph_builder.py vs SPEC 3.1-3.2 (2026-07-19) — 3 temuan, SUDAH diterapkan
1. **Jalur produksi dari .pbf wajib `osmium tags-filter w/highway` sebelum
   `osmium cat`** — terverifikasi empiris: `graph_from_xml` menelan semua way
   (bangunan/sungai/pagar) dan simplify bisa melebur ruas jalan dengan segmen
   sungai jadi satu edge → dangling/disconnected palsu massal. Perintah dua
   tahap sudah didokumentasikan di docstring `graph_builder.py`.
2. **Semantik degree untuk deteksi 3.1**: di MultiDiGraph ujung jalan buntu
   dua-arah ber-degree 2 (in+out); `to_undirected()` masih MultiGraph (degree
   tetap 2). `detect_dangling_nodes.py` WAJIB pakai
   `nx.Graph(G.to_undirected())` sebelum cek degree==1 — kalau tidak, nol
   temuan. Sudah dicatat di docstring.
3. **Filter sample vs produksi belum sejajar**: polygon path = `drive` saja,
   produksi (w/highway) masih ikut footway/cycleway/steps. Diselaraskan saat
   runner CI Fase 4; sudah dicatat di docstring.

## Selesai (sesi Fase 1 awal, 2026-07-19)
- Dependensi Fase 1 terpasang + dicatat di `requirements.txt`:
  geopandas, osmnx, networkx, shapely.
- `data/boundaries/jabodetabek.poly` — dibuat dari dissolve 1.446 desa di
  `jabodetabek.shp` (buffer 0.002° tutup sliver, simplify 0.001°, exterior
  ring saja). 1 poligon, ±580 vertex. Generator: `ensure_boundary_poly()`
  di `fetch_osm.py` (idempotent, `force=True` untuk regenerate).
- `src/data_ingestion/fetch_osm.py` (SPEC 5.2b) — full download + osmium
  extract, incremental via diff Geofabrik (state file
  `data/raw/osm_replication_state.txt`, apply-changes berurutan, re-extract
  polygon), fallback wajib ke full download, log mode ke `pipeline_logs`.
- `src/db/writer.py` — `log_pipeline_run()` ke tabel `pipeline_logs`
  (SPEC 5.3 poin 3).
- `src/pipeline_1_road_qa/graph_builder.py` (SPEC Bagian 3 Pipeline 1) —
  `build_graph_from_xml()` (jalur produksi/CI dari .pbf→XML),
  `build_graph_from_polygon()` (jalur sample via Overpass),
  `load_kecamatan_boundary()` (kolom WADMKC), `graph_summary()`.
  Kunci: `retain_all=True` (jangan buang komponen kecil — itu target deteksi
  3.2) dan `simplify=True` (endpoint dangling tetap degree-1).
- Test: 15 pass (6 lama + 9 baru di `test_fetch_osm.py`,
  `test_graph_builder.py`, `test_writer.py` — termasuk test fallback
  incremental→full dan test retain_all menjaga 2 komponen terpisah).
- **Uji data nyata (Fase 0 langkah 3 + Fase 1 step 4):** Kecamatan Menteng
  (6.46 km², Jakarta Pusat) via Overpass → 693 node, 1.326 edge berarah,
  3 weakly connected component, 91 kandidat degree-1. Tersimpan di
  `data/raw/sample_menteng.graphml` (gitignored).

## Keputusan penting (sesi ini)
- **osmium-tool TIDAK tersedia di Windows dev ini** (tidak ada di choco,
  WSL belum ada distro). Keputusan: `fetch_osm.py` ditulis untuk jalan di
  GitHub Actions Ubuntu runner (`apt-get install osmium-tool`, Fase 4);
  uji lokal pakai jalur sample Overpass (`build_graph_from_polygon`).
  Clip penuh `java-latest.osm.pbf` → `jabodetabek.osm.pbf` baru terjadi di CI.
- **Shapefile boundary memuat ring desa non-Jabodetabek** (85 desa: Lebak,
  Cianjur, Karawang, Purwakarta, Sukabumi — pola ring perbatasan).
  Keputusan: di-dissolve semua apa adanya untuk `.poly` — buffer tepi justru
  mengurangi artefak potongan jaringan jalan di boundary. Kalau mau difilter,
  regenerate via `ensure_boundary_poly(force=True)` setelah ubah logika.
- Diff incremental Geofabrik mencakup seluruh Java → setelah `apply-changes`
  WAJIB re-extract polygon (sudah diimplementasikan di `incremental_update`).
- Sample kecamatan = **Menteng** (bukan yang terkecil dari sort area, karena
  entri terkecil ternyata serpihan potongan kabupaten perbatasan, bukan
  kecamatan utuh).
- 91 node degree-1 di Menteng ≠ semua error: campuran artefak clip boundary
  (`truncate_by_edge`) + cul-de-cac asli + error data. Pemilahan (cek silang
  tag `highway=*`, SPEC 3.1) adalah tugas `detect_dangling_nodes.py`.

## Langkah selanjutnya (Fase 2 — Pipeline 2 POI Validation, sesi baru)
1. `data_ingestion/fetch_osm_poi.py` — unzip+baca `java-latest-free.shp.zip`
   layer `gis_osm_pois_free_1.shp` & `gis_osm_pois_a_free_1.shp` (GeoPandas),
   clip ke boundary Jabodetabek. JANGAN campur dengan jalur `.pbf` (SPEC 5.2c).
2. `pipeline_2_poi_qa/spatial_join.py` — Haversine ke jalan terdekat (SPEC
   Bagian 3 Pipeline 2.1; `EARTH_RADIUS_KM=6371` sudah di config).
3. `pipeline_2_poi_qa/detect_outliers.py` — IQR (SPEC 2.2, multiplier 1.5).
4. Masing-masing + unit test + log `pipeline_logs`; validasi manual sample
   (SPEC Bagian 8 step 8-10, checklist 5.4).
Catatan: file `.shp.zip` (2.2GB) belum ada di `data/raw/` — perlu didownload
dari Geofabrik dulu (atau di-handle `fetch_osm_poi.py` dengan cache).

---

## Arsip: Fase 0 — Fondasi SELESAI

## Selesai
- Struktur folder dasar dibuat persis mengikuti SPEC.md Bagian 5.1:
  `data/raw/`, `data/boundaries/`, `src/data_ingestion/`, `src/pipeline_1_road_qa/`,
  `src/pipeline_2_poi_qa/`, `src/pipeline_3_weather_risk/`, `src/pipeline_4_aggregator/`,
  `src/db/`, `src/api/`, `tests/`, `.github/workflows/`.
  Folder pipeline masih kosong (hanya `.gitkeep`) — logika pipeline belum disentuh,
  sesuai urutan fase.
- `src/config.py`: path proyek, `DATABASE_URL` dari env, dan threshold rumus
  Bagian 3 (IQR 1.5, AHP CR<=0.1, Gi* p<0.05, dangling node degree=1).
- `src/db/models.py`: schema SQLAlchemy + GeoAlchemy2 (SRID 4326) untuk
  `pipeline_logs` (Bagian 5.3), `road_errors` (P1), `poi_anomalies` (P2),
  `weather_risk_grid` (P3), `aggregated_findings` (P4).
- `requirements.txt`, `.env.example`, `.gitignore` untuk fondasi Python + env.
- `tests/test_config.py`, `tests/test_models.py` — 6 test, semua pass.
- **Database Supabase (PostgreSQL 17.6, region ap-south-1) tersambung dan siap:**
  - Koneksi via **Session Pooler** (bukan direct connection — lihat keputusan di bawah).
  - Extension `postgis` diaktifkan (`CREATE EXTENSION IF NOT EXISTS postgis;`), versi 3.3.
  - Schema di-apply via `Base.metadata.create_all()`. Tabel yang sudah ada di
    Supabase (`public` schema): `pipeline_logs`, `road_errors`, `poi_anomalies`,
    `weather_risk_grid`, `aggregated_findings` (+ tabel sistem PostGIS:
    `spatial_ref_sys`, `geometry_columns`, `geography_columns`).
  - Kredensial tersimpan di `.env` (gitignored), bukan hardcode di `config.py`.

## Keputusan penting
- **Pakai Supabase Session Pooler, bukan Direct Connection.** Direct connection
  host (`db.<ref>.supabase.co`) cuma punya AAAA record (IPv6-only) untuk
  project baru kecuali beli add-on IPv4 — gagal resolve dari jaringan
  IPv4-only. Pooler host (`aws-1-ap-south-1.pooler.supabase.com:5432`) IPv4-
  compatible. Konsekuensi: username koneksi jadi `postgres.<project-ref>`,
  bukan cuma `postgres`.
- Password Supabase yang mengandung karakter reserved URL (`@`, `$`, `#`, dst.)
  WAJIB di-percent-encode di `DATABASE_URL` (mis. `@` -> `%40`, `$` -> `%24`,
  `#` -> `%23`) supaya parser URL tidak salah pisah host/userinfo.
- `ml/` folder **belum dibuat** — sesuai CLAUDE.md aturan #2, baru dibuat
  setelah Fase 1-6 selesai + ada log historis nyata.
- `DISCONNECTED_COMPONENT_MIN_RATIO` (0.05) di `config.py` adalah **placeholder**,
  bukan nilai dari SPEC.md — SPEC.md Bagian 3.2 tidak menetapkan angka pasti.
  Wajib divalidasi manual saat implementasi Pipeline 1 (Fase 1).
- `H3_RESOLUTION` sengaja belum ditetapkan di `config.py` — didelegasikan ke
  `h3_grid.py` saat Fase 3.
- `writer.py` dan file-file `data_ingestion/*.py` (misal `fetch_osm.py`)
  **belum dibuat** — scope sesi fondasi dibatasi ke folder/config/models/DB
  connection saja.

## Observasi file data (sudah ditindaklanjuti)
- `java-latest.osm.pbf` (~894MB) — dipindah ke `data/raw/java-latest.osm.pbf`.
  Masih extract mentah region Java, belum di-clip ke boundary Jabodetabek.
- `jabodetabek.shp` + sidecar (.dbf/.shx/.prj/.cpg/.qmd) — sengaja dobel:
  copy di root dipakai `GeoLogix.qgz` (proyek QGIS), copy di
  `data/boundaries/` dipakai pipeline. Jangan hapus salah satu.
- `GeoLogix.qgz` — tetap di root, tidak diubah.

## Langkah selanjutnya lama (SUDAH DIKERJAKAN — lihat bagian Fase 1 di atas)
1. ~~Sample 1 kecamatan~~ → selesai (Menteng, `sample_menteng.graphml`).
2. ~~`jabodetabek.poly`~~ → selesai (via `ensure_boundary_poly()`).
3. ~~`fetch_osm.py` + `graph_builder.py`~~ → selesai; sisa Fase 1:
   detect_dangling_nodes, detect_disconnected, detect_oneway_issues.
