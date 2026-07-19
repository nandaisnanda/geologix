# Validasi manual Pipeline 4 — Aggregator (checklist SPEC 5.4)

Tanggal: 2026-07-19. Input: temuan nyata P1/P2 di Supabase (sample Menteng,
run validasi Fase 1-2). WorldPop idn_pd_2020_1km_UNadj.tif (log id 19).

## 1. Tiga run berturut-turut — identik & deterministik
`python -m src.pipeline_4_aggregator` 3x (log id 20-22, 519 baris
`aggregated_findings` = 173x3):
- 173 temuan: 141 road_errors (dedupe dari 423 = 141x3 run validasi P1) +
  32 poi_anomalies (dedupe dari 96 = 32x3 run validasi P2). Dedupe bekerja.
- Bobot AHP [0.5714, 0.2857, 0.1429] = eksak [4/7, 2/7, 1/7], CR = 0.0
  (matriks konsisten sempurna, lolos syarat CR <= 0.1 SPEC 3.2).
- priority_score 0.4197-0.9988, top selalu poi_anomalies:79.
- dropped_no_population = 0 (semua titik Menteng tercakup raster WorldPop).

## 2. Sample hasil dicek manual — urutan masuk akal
| Peringkat | Sumber | Prio | Penjelasan |
|---|---|---|---|
| 1-4 | poi_anomalies conf=1.0 (jarak 68-83m) | 0.94-0.999 | severity 1+2*1.0=3.0 (setara `high` P1) + densitas pusat Jakarta tinggi + ease 5 (edit POI paling ringan) — quick win valid didahulukan |
| 5-6 | road_errors oneway `high` | ~0.90 | severity sama (3.0) tapi ease 3 -> selisih ~0.1 = 2/5 x bobot ease 1/7, sesuai hitungan |
| terbawah road | dangling `medium` | 0.599 | severity 2.0 + ease 4 — tidak pernah di bawah POI conf rendah murni karena bobot severity dominan 4/7 |

Cek tangan peringkat 1 (poi 79): ketiga kriteria di/dekat maksimum batch
(conf 1.0 -> sev 3.0 = max; densitas Menteng dekat max; ease 5 = max) ->
prio ~= 1 (0.9988 karena densitas bukan persis max). Benar.

## 3. Keterbatasan yang disadari
1. **Skor relatif per batch** (Min-Max per run, keputusan sama dengan P3) —
   membandingkan angka antar-run berbeda batch tidak bermakna; urutan
   DALAM satu run yang bermakna.
2. Input saat ini masih temuan sample Menteng (P1/P2 belum run full
   Jabodetabek di CI) — variasi densitas populasi sempit (satu kecamatan).
   Jalankan ulang P4 setelah CI menghasilkan temuan full-area.
3. WorldPop = proyeksi 2020 resolusi 1 km (sesuai label "proxy" di SPEC),
   bukan populasi aktual 2026.
4. Severity P2 dipetakan 1+2*confidence (skala 1-3 sama dengan P1) —
   keputusan proyek; kalau dianggap terlalu agresif (4 POI conf 1.0 menyalip
   semua road error), turunkan pemetaan atau bobot ease.
